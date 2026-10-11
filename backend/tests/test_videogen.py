"""Plumbing tests for the Learn More explainer-video endpoints.

Manim, ffmpeg and an Anthropic key are not available in CI, and a real render
takes minutes, so VIDEOGEN_DIR is pointed at a stub `generator.py` that prints
the same progress lines the real CLI does and drops a file where Manim would.
That exercises everything this service actually owns: the child process, stage
parsing, video discovery, validation, quota and file serving.

    python -m pytest backend/tests/test_videogen.py       (or run this file)
"""

import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Must be set before app.core.config is imported and its settings are cached.
STUB = BACKEND / "tests" / "_videogen_stub"
os.environ["VIDEOGEN_DIR"] = str(STUB)
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-used-by-the-stub"
os.environ["VIDEOGEN_RATE_LIMIT_PER_HOUR"] = "10"  # lowered in the quota check

STUB_SOURCE = '''\
"""Stands in for videogen/generator.py: same progress lines, no Manim."""
import os, sys

topic = sys.argv[1]
if topic == "boom":
    print("error: Claude declined this request.")
    sys.exit(1)

import re
slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "lesson"

print(f'Designing a lesson on "{topic}" with claude-opus-5 ...')
print("Writing the Manim scene ...")
print("Rendering (first run synthesises gTTS audio, so it is the slow one) ...")

out = os.path.join("media", "videos", slug, "720p30")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, slug + ".mp4"), "wb") as fh:
    fh.write(b"not really an mp4")
'''


def build_stub():
    STUB.mkdir(parents=True, exist_ok=True)
    (STUB / "generator.py").write_text(STUB_SOURCE, encoding="utf-8")
    # A previous run's output would make every "generate" look instantly cached.
    media = STUB / "media"
    if media.exists():
        import shutil
        shutil.rmtree(media)


def main():
    build_stub()

    from fastapi.testclient import TestClient
    from app.main import app_http
    from app.services import video_generator as vg

    client = TestClient(app_http)
    failures = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    print("slug parity with the real CLI")
    # generator.py pulls in manim-dependent modules at import time, so the two
    # slug functions are compared by source rather than by importing it.
    real_src = (BACKEND.parent / "videogen" / "generator.py").read_text(encoding="utf-8")
    check("videogen still slugifies with the same regex",
          're.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")' in real_src,
          "videogen/generator.py:slugify changed — update video_generator.slugify")
    check("slugify matches", vg.slugify("Hash Tables & Collisions!") == "hash-tables-collisions")

    print("\nvalidation")
    r = client.post("/api/v1/videos/generate", json={"topic": "   "})
    check("empty topic rejected", r.status_code == 400, r.text)
    r = client.post("/api/v1/videos/generate", json={"topic": "x" * 200})
    check("overlong topic rejected", r.status_code == 400, r.text)
    r = client.post("/api/v1/videos/generate", json={"topic": "!!!"})
    check("letterless topic rejected", r.status_code == 400, r.text)

    print("\nhappy path")
    r = client.post("/api/v1/videos/generate", json={"topic": "binary search"})
    check("generate accepted", r.status_code == 200, r.text)
    slug = r.json().get("slug")
    check("slug returned", slug == "binary-search", str(r.json()))

    state = {}
    for _ in range(100):
        state = client.get(f"/api/v1/videos/{slug}").json()
        if state["status"] in ("ready", "failed"):
            break
        time.sleep(0.2)
    check("render reached ready", state.get("status") == "ready", str(state))
    check("progress is 100 when ready", state.get("progress") == 100)
    check("video_url exposed", state.get("video_url") == f"/api/v1/videos/{slug}/file")

    r = client.get(f"/api/v1/videos/{slug}/file")
    check("mp4 served", r.status_code == 200 and r.content == b"not really an mp4", r.status_code)
    check("served as video/mp4", r.headers.get("content-type") == "video/mp4")

    r = client.get("/api/v1/videos")
    check("gallery lists it", any(v["slug"] == slug for v in r.json()["videos"]), r.text)

    print("\nsecond request for a rendered topic is free")
    r = client.post("/api/v1/videos/generate", json={"topic": "Binary Search"})
    body = r.json()
    check("returns ready immediately", body.get("status") == "ready", str(body))
    check("no second render was started",
          body.get("elapsed_seconds", 999) < 5, str(body))

    print("\nfailure surfaces the generator's own message")
    r = client.post("/api/v1/videos/generate", json={"topic": "boom"})
    check("failing render still accepted", r.status_code == 200, r.text)
    state = {}
    for _ in range(100):
        state = client.get("/api/v1/videos/boom").json()
        if state["status"] in ("ready", "failed"):
            break
        time.sleep(0.2)
    check("reported failed", state.get("status") == "failed", str(state))
    check("error text came from the child",
          "declined" in (state.get("error") or ""), str(state.get("error")))

    print("\na killed render explains itself in words, not an exit code")
    killed = vg._Job("killed topic", "killed-topic")
    # Windows renders a killed process's -1 as 4294967295; neither number means
    # anything to somebody reading it on the landing page.
    msg = vg.VideoGenerator._explain_failure(killed, 4294967295)
    check("no raw exit code shown", "4294967295" not in msg, msg)
    check("says it was stopped", "stopped" in msg.lower(), msg)

    print("\nmanim's intermediate fragments are not videos")
    # A real render leaves ~100 mp4s under partial_movie_files/, named by hash.
    # Listing them turns the gallery into junk and offers unplayable topics.
    frag = STUB / "media" / "videos" / slug / "720p30" / "partial_movie_files" / "BinarySearchLesson"
    frag.mkdir(parents=True, exist_ok=True)
    (frag / "558484971_1433877407_3923656615.mp4").write_bytes(b"one animation")
    listed = client.get("/api/v1/videos").json()["videos"]
    check("gallery lists only the finished video",
          [v["slug"] for v in listed] == [slug], str(listed))
    check("a fragment is not servable",
          client.get("/api/v1/videos/558484971_1433877407_3923656615").status_code == 404)

    print("\na video appearing on disk clears an earlier failure")
    # The CLI writes into the same media tree, so a topic this server gave up on
    # can finish by other means. The stale failure must not mask it.
    out = STUB / "media" / "videos" / "boom" / "720p30"
    out.mkdir(parents=True, exist_ok=True)
    (out / "boom.mp4").write_bytes(b"rendered by the CLI instead")
    state = client.get("/api/v1/videos/boom").json()
    check("failure gives way to the real video", state.get("status") == "ready", str(state))
    r = client.post("/api/v1/videos/generate", json={"topic": "boom"})
    check("generate returns it rather than retrying",
          r.json().get("status") == "ready", r.text)

    print("\npath traversal")
    r = client.get("/api/v1/videos/..%2F..%2Fetc%2Fpasswd/file")
    check("traversal not served", r.status_code == 404, r.status_code)

    print("\nunknown topic")
    r = client.get("/api/v1/videos/never-generated-this")
    check("unknown slug is 404", r.status_code == 404, r.status_code)

    print("\nquota")
    vg.settings.__dict__["VIDEOGEN_RATE_LIMIT_PER_HOUR"] = 1
    vg.video_generator._starts.clear()
    r = client.post("/api/v1/videos/generate", json={"topic": "quota probe one"})
    check("first cold render allowed", r.status_code == 200, f"{r.status_code} {r.text}")
    r = client.post("/api/v1/videos/generate", json={"topic": "quota probe two"})
    check("second cold render is rate limited", r.status_code == 429, f"{r.status_code} {r.text}")
    # An already-rendered topic must stay free even at the limit.
    r = client.post("/api/v1/videos/generate", json={"topic": "binary search"})
    check("cached topic ignores the quota",
          r.status_code == 200 and r.json()["status"] == "ready", f"{r.status_code} {r.text}")
    vg.settings.__dict__["VIDEOGEN_RATE_LIMIT_PER_HOUR"] = 10

    print("\nmissing key degrades to 503, not a 500")
    vg.settings.__dict__["ANTHROPIC_API_KEY"] = ""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    vg.video_generator._starts.clear()
    r = client.post("/api/v1/videos/generate", json={"topic": "no key here"})
    check("reports unavailable", r.status_code == 503, f"{r.status_code} {r.text}")
    check("says what is missing", "ANTHROPIC_API_KEY" in r.json().get("detail", ""), r.text)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
