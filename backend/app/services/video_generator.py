"""Explainer-video generation for the landing page's Learn More section.

The renderer itself lives in `videogen/` at the repo root and is a CLI, not a
library: it shells out to Manim, writes files next to itself, and takes minutes
per video. So this service drives it as a child process rather than importing
it. Nothing in `videogen/` is imported here, which is deliberate — the API
server does not have manim, manim-voiceover or ffmpeg installed and must keep
starting cleanly without them.

    POST /videos/generate  -> queue a topic, return a slug immediately
    GET  /videos/{slug}     -> poll status until "ready"
    GET  /videos/{slug}/file -> the mp4

A render is minutes of CPU and two Claude calls, so three things bound the cost:
already-rendered topics are served straight off disk, only one render runs at a
time, and each caller gets a small quota per hour.

Renders run on their own daemon threads rather than as asyncio tasks. A task
created inside a request handler belongs to that request's event loop, and a
ten-minute render outliving the loop that spawned it gets cancelled. A thread
around a blocking `Popen` has no such lifetime coupling, and the work is a child
process rather than anything CPU-bound in Python, so nothing is lost by it.
"""

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import get_settings

settings = get_settings()

# backend/app/services/video_generator.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

# Stages, in the order the CLI reports them. The frontend renders these as
# labels, so keep them short.
QUEUED = "queued"
DESIGNING = "designing"
WRITING = "writing"
RENDERING = "rendering"
READY = "ready"
FAILED = "failed"

_STAGE_LABEL = {
    QUEUED: "Waiting for a free render slot",
    DESIGNING: "Designing the lesson",
    WRITING: "Writing the animation",
    RENDERING: "Rendering the video",
    READY: "Ready",
    FAILED: "Failed",
}

# Each stage's rough share of a cold run, used only to move a progress bar.
# Manim's own progress goes to a tty we do not have, so this is an estimate by
# design and is never presented as exact.
_STAGE_PROGRESS = {QUEUED: 2, DESIGNING: 12, WRITING: 35, RENDERING: 65, READY: 100}

# A cold run is two Claude calls plus a full Manim render. Past this something
# has wedged and the child is killed so the queue is not blocked forever.
_RENDER_TIMEOUT_SECONDS = 45 * 60

# Enough lines to explain a failure without letting a chatty child grow without
# bound in memory.
_LOG_TAIL_LINES = 40

_MAX_TOPIC_CHARS = 80


class VideogenUnavailable(RuntimeError):
    """The renderer cannot run here. The message says what is missing."""


def slugify(topic: str) -> str:
    """Match `videogen/generator.py:slugify` exactly.

    The CLI keys plans, scene modules and video filenames on its own slug, so
    if these two disagree the finished mp4 is never found.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")
    return slug or "lesson"


def videogen_dir() -> Path:
    return Path(settings.VIDEOGEN_DIR).expanduser() if settings.VIDEOGEN_DIR \
        else REPO_ROOT / "videogen"


def _python_executable() -> str:
    """The interpreter that runs the CLI.

    Defaults to this one, which is usually wrong: the API server's environment
    has no manim. VIDEOGEN_PYTHON points at the interpreter that does, e.g.
    `videogen/.venv/Scripts/python.exe`.
    """
    return settings.VIDEOGEN_PYTHON or sys.executable


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def check_available() -> None:
    """Raise VideogenUnavailable unless a cold render could actually start.

    Checked per request rather than at import so that fixing the environment
    does not require a server restart, and so a missing renderer degrades one
    endpoint instead of the whole API.
    """
    root = videogen_dir()
    if not (root / "generator.py").is_file():
        raise VideogenUnavailable(
            f"The video generator is not installed at {root}. It ships in the "
            f"repo's videogen/ directory; set VIDEOGEN_DIR if it lives elsewhere."
        )
    if not _api_key():
        raise VideogenUnavailable(
            "ANTHROPIC_API_KEY is not set on the server, so no new lesson can "
            "be designed. Already-generated topics still play."
        )
    # sys.executable is always a real file, so only an override can be wrong.
    if settings.VIDEOGEN_PYTHON and not Path(settings.VIDEOGEN_PYTHON).is_file():
        raise VideogenUnavailable(
            f"VIDEOGEN_PYTHON points at {settings.VIDEOGEN_PYTHON}, which does "
            f"not exist."
        )


# Manim renders each animation to its own mp4 under partial_movie_files/ and
# stitches them at the end — a 97-animation lesson leaves ~100 of them, named by
# hash. They are indistinguishable from finished videos by extension alone, so
# every lookup here has to exclude them explicitly.
_PARTIAL_DIR = "partial_movie_files"


def _is_finished_video(path: Path) -> bool:
    return path.is_file() and _PARTIAL_DIR not in path.parts


def find_video(slug: str) -> Optional[Path]:
    """The rendered mp4 for a slug, or None.

    Manim nests output under media/videos/<module>/<resolution>/, and the same
    topic re-rendered at another quality leaves several. Newest wins.
    """
    media = videogen_dir() / "media" / "videos"
    if not media.is_dir():
        return None
    matches = [p for p in media.glob(f"**/{slug}.mp4") if _is_finished_video(p)]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


class _Job:
    """One topic's render. Lives in memory only; a restart forgets in-flight
    work but not finished videos, which are found back on disk."""

    def __init__(self, topic: str, slug: str):
        self.topic = topic
        self.slug = slug
        self.status = QUEUED
        self.error: Optional[str] = None
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self.log: List[str] = []
        self.thread: Optional[threading.Thread] = None

    def as_dict(self) -> dict:
        elapsed = (self.finished_at or time.time()) - self.started_at
        return {
            "slug": self.slug,
            "topic": self.topic,
            "status": self.status,
            "stage_label": _STAGE_LABEL.get(self.status, self.status),
            "progress": _STAGE_PROGRESS.get(self.status, 0),
            "elapsed_seconds": int(elapsed),
            "error": self.error,
            "video_url": f"/api/v1/videos/{self.slug}/file"
            if self.status == READY else None,
        }


class VideoGenerator:
    def __init__(self):
        self._jobs: Dict[str, _Job] = {}
        # One render at a time. Manim is CPU-bound and manim-voiceover keeps a
        # single gTTS cache.json that concurrent writers can corrupt.
        self._slot = threading.Semaphore(1)
        self._starts: Dict[str, List[float]] = {}
        # Guards _jobs and _starts: renders run on their own threads, so
        # bookkeeping is touched from more than one.
        self._lock = threading.Lock()

    # ── quota ────────────────────────────────────────────────────────────────
    def _check_quota(self, caller: str) -> None:
        """Cap cold renders per caller per hour.

        The section is public, so the quota is what stops an anonymous visitor
        from spending the API budget. Serving an existing video never counts.
        Call with `_lock` held.
        """
        limit = settings.VIDEOGEN_RATE_LIMIT_PER_HOUR
        if limit <= 0:
            return
        cutoff = time.time() - 3600
        recent = [t for t in self._starts.get(caller, []) if t > cutoff]
        self._starts[caller] = recent
        if len(recent) >= limit:
            wait = int((recent[0] + 3600 - time.time()) / 60) + 1
            raise PermissionError(
                f"You have generated {limit} videos in the last hour, which is "
                f"the limit. Try again in about {wait} minute(s), or pick a "
                f"topic that has already been generated."
            )

    def _record_start(self, caller: str) -> None:
        self._starts.setdefault(caller, []).append(time.time())

    # ── public API ───────────────────────────────────────────────────────────
    def get(self, slug: str) -> Optional[dict]:
        """Status for a slug: the live job, or a video already on disk."""
        with self._lock:
            job = self._jobs.get(slug)

        # A failed attempt must not mask a video that exists anyway. The CLI
        # writes into the same media tree, so a topic can finish rendering by
        # other means after this server gave up on it — and the stale failure
        # would otherwise be reported forever, since nothing clears _jobs.
        if job and job.status == FAILED and find_video(slug):
            with self._lock:
                if self._jobs.get(slug) is job:
                    del self._jobs[slug]
            job = None

        if job:
            return job.as_dict()
        if find_video(slug):
            # Rendered by an earlier server run, or by the CLI directly.
            done = _Job(slug.replace("-", " "), slug)
            done.status = READY
            done.finished_at = done.started_at
            return done.as_dict()
        return None

    def list_ready(self) -> List[dict]:
        """Every topic with a playable video, newest first — the gallery."""
        media = videogen_dir() / "media" / "videos"
        if not media.is_dir():
            return []
        newest: Dict[str, float] = {}
        for path in media.glob("**/*.mp4"):
            if not _is_finished_video(path):
                continue
            mtime = path.stat().st_mtime
            if mtime > newest.get(path.stem, 0):
                newest[path.stem] = mtime
        return [
            {
                "slug": slug,
                # The original wording is not stored, so rebuild a readable
                # title from the slug.
                "topic": slug.replace("-", " ").title(),
                "video_url": f"/api/v1/videos/{slug}/file",
            }
            for slug, _ in sorted(newest.items(), key=lambda kv: -kv[1])
        ]

    def start(self, topic: str, caller: str) -> dict:
        """Queue a render, or return the finished/in-flight one for this topic."""
        topic = " ".join(str(topic).split())
        if not topic:
            raise ValueError("Give a topic, for example \"hash tables\".")
        if len(topic) > _MAX_TOPIC_CHARS:
            raise ValueError(
                f"Keep the topic under {_MAX_TOPIC_CHARS} characters — it is one "
                f"concept to teach, not a syllabus."
            )
        if not re.search(r"[a-z0-9]", topic.lower()):
            raise ValueError("That topic has no letters or digits in it.")

        slug = slugify(topic)

        if find_video(slug):
            # Already rendered, by an earlier run or the CLI. Free and instant.
            return self.get(slug)

        check_available()

        # Claim the slug and the quota together, so two visitors asking for the
        # same topic at the same moment get one render between them.
        with self._lock:
            existing = self._jobs.get(slug)
            if existing and existing.status != FAILED:
                return existing.as_dict()

            self._check_quota(caller)
            job = _Job(topic, slug)
            self._jobs[slug] = job
            self._record_start(caller)

        job.thread = threading.Thread(
            target=self._run, args=(job,), name=f"videogen:{slug}", daemon=True
        )
        job.thread.start()
        return job.as_dict()

    # ── the child process ────────────────────────────────────────────────────
    def _run(self, job: _Job) -> None:
        """Thread body: wait for the render slot, then drive the CLI."""
        try:
            with self._slot:
                self._render(job)
        except Exception as exc:  # a crash here must not lose the job's status
            job.status = FAILED
            job.error = f"{type(exc).__name__}: {exc}"
            job.finished_at = time.time()

    def _command(self, job: _Job) -> List[str]:
        return [
            _python_executable(),
            "generator.py",
            job.topic,
            "--no-preview",  # there is no display on a server
            "--quality", settings.VIDEOGEN_QUALITY,
            "--fps", str(settings.VIDEOGEN_FPS),
            "--minutes", str(settings.VIDEOGEN_MINUTES),
            "--effort", settings.VIDEOGEN_EFFORT,
        ]

    def _child_env(self) -> dict:
        env = dict(os.environ)
        env["ANTHROPIC_API_KEY"] = _api_key()
        # The CLI prints model-written titles containing curly quotes; on Windows
        # the default console codepage cannot encode them and the write raises.
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def _render(self, job: _Job) -> None:
        job.status = DESIGNING

        proc = subprocess.Popen(
            self._command(job),
            cwd=str(videogen_dir()),
            env=self._child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # Manim's progress bars are full of partial lines and box-drawing
            # characters; decode leniently rather than risk a UnicodeDecodeError
            # taking down a render that is otherwise fine.
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # A wedged child would otherwise hold the single render slot forever.
        # Killing it closes the pipe, which ends the read loop below.
        expired = threading.Event()

        def give_up():
            expired.set()
            proc.kill()

        watchdog = threading.Timer(_RENDER_TIMEOUT_SECONDS, give_up)
        watchdog.daemon = True
        watchdog.start()
        try:
            self._consume(proc, job)
            code = proc.wait()
        finally:
            watchdog.cancel()

        job.finished_at = time.time()
        timed_out = expired.is_set()

        if code == 0 and find_video(job.slug):
            job.status = READY
            return

        job.status = FAILED
        if timed_out:
            job.error = (
                f"Gave up after {_RENDER_TIMEOUT_SECONDS // 60} minutes without "
                f"a finished video."
            )
        elif code == 0:
            job.error = ("The generator finished but no video file was produced.")
        else:
            job.error = self._explain_failure(job, code)

    def _consume(self, proc, job: _Job) -> None:
        """Read the child's output, tracking the stage it reports."""
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            job.log.append(line)
            if len(job.log) > _LOG_TAIL_LINES:
                del job.log[:-_LOG_TAIL_LINES]
            self._advance(job, line)
        proc.stdout.close()

    @staticmethod
    def _advance(job: _Job, line: str) -> None:
        """Map a CLI progress line onto a stage.

        Stages only move forward: the child prints "Reusing plans/..." after it
        has already started writing a scene, and going backwards would make the
        progress bar jump about.
        """
        order = [QUEUED, DESIGNING, WRITING, RENDERING]
        lowered = line.lower()
        if lowered.startswith("designing a lesson"):
            nxt = DESIGNING
        elif lowered.startswith("writing the manim scene"):
            nxt = WRITING
        elif lowered.startswith("rendering"):
            nxt = RENDERING
        else:
            return
        if job.status in order and order.index(nxt) > order.index(job.status):
            job.status = nxt

    @staticmethod
    def _explain_failure(job: _Job, code: int) -> str:
        """Turn the child's exit into something a visitor can act on.

        The CLI already writes actionable messages for the cases it knows
        about (bad key, no credits, refusal), so surface those verbatim rather
        than replacing them with an exit code.
        """
        tail = [ln for ln in job.log if ln.lower().startswith("error:")]
        if tail:
            return tail[-1][len("error:"):].strip()

        joined = "\n".join(job.log).lower()
        if "no module named 'manim'" in joined or "no module named manim" in joined:
            return (
                "The interpreter running the generator does not have manim "
                "installed. Install videogen/requirements.txt into it, and point "
                "VIDEOGEN_PYTHON at that interpreter."
            )
        if "ffmpeg" in joined:
            return ("Manim could not find ffmpeg. Install it and make sure it is "
                    "on the server's PATH.")
        # A killed process reports its signal as the exit code, which Windows
        # then renders unsigned: -1 arrives as 4294967295. Neither number means
        # anything to somebody reading it on the landing page.
        if code < 0 or code > 255:
            return "The render was stopped before it finished."
        return f"The generator exited with code {code}."


video_generator = VideoGenerator()
