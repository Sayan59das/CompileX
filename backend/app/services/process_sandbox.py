"""Run a player's program without Docker, as an unprivileged throwaway user with limits and no internet sockets.

For machines that cannot run Docker (a free Render service is one). It is weaker than Docker and the judge says so in /health ("mode": "process"):
- each concurrent run gets its own unprivileged user id (so runs cannot read each other's files or signal each other) and its own work folder
  that is deleted afterwards; everything a run left behind is killed;
- the program starts through process_sandbox_exec.py, which drops root, sets time / process / file-size / memory limits, forbids new privileges
  and installs a syscall filter that refuses internet sockets (so no network, no DNS) and a few dangerous calls;
- the program's environment is scrubbed: no secrets, only what it needs. The judge's own secret lives in the root-owned process, which the
  unprivileged user cannot read (/proc/<pid>/environ of another user's process is refused);
- output goes to files with a size cap, never into the judge's memory without limit.

What it cannot stop (Docker could): reading other world-readable files of the machine, filling the machine's disk or memory within the limits,
and a kernel flaw. So the machine must hold no secrets that are readable by everyone, and it should be a service of its own.

Needs: Linux on x86-64, started as root (to drop privileges). `check()` proves in a real run that the sandbox works; if it does not, nothing runs.
"""

import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCHER = os.path.join(HERE, "process_sandbox_exec.py")
UID_BASE = 30000            # run slot n uses user id (and group id) UID_BASE + n; these ids do not exist in /etc/passwd, which is fine
MAX_OUTPUT_BYTES = 1_000_000
MAX_ERROR_BYTES = 8_000
CLEAN_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


@dataclass
class Limits:
    cpu_seconds: int = 10
    wall_seconds: float = 12.0
    nproc: int = 64
    nofile: int = 64
    fsize_mb: int = 16
    data_mb: int = 256          # 0 = no limit (the JVM and Node reserve address space, so they get flags instead)


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def supported() -> Tuple[bool, str]:
    if not sys.platform.startswith("linux"):
        return False, "not Linux"
    if platform.machine().lower() not in ("x86_64", "amd64"):
        return False, f"unsupported CPU architecture {platform.machine()} (the syscall filter is for x86-64)"
    if os.geteuid() != 0:
        return False, "not running as root, so it cannot drop privileges per run"
    return True, ""


class _Slots:
    """Hands out run slots (and so user ids), blocking when all are in use."""

    def __init__(self, count: int):
        self._cond = threading.Condition()
        self._free = list(range(max(1, count)))

    def acquire(self) -> int:
        with self._cond:
            while not self._free:
                self._cond.wait()
            return self._free.pop(0)

    def release(self, slot: int):
        with self._cond:
            self._free.append(slot)
            self._cond.notify()


_slots: Optional[_Slots] = None
_slots_lock = threading.Lock()


def get_slots(count: int = 2) -> _Slots:
    """The one shared pool. The first caller sets its size (the judge does so at startup from MAX_CONCURRENT_EXECUTIONS)."""
    global _slots
    with _slots_lock:
        if _slots is None:
            _slots = _Slots(count)
        return _slots


def kill_user(uid: int, wait: float = 0.0) -> int:
    """SIGKILL every process owned by `uid` (anything a run left behind, however it hid). Returns how many it found.
    With `wait`, repeats for up to that many seconds until none are left, so the next run on this user id starts clean."""
    import time

    deadline = time.time() + wait
    while True:
        found = _kill_user_once(uid)
        if found == 0 or time.time() >= deadline:
            return found
        time.sleep(0.05)


def _kill_user_once(uid: int) -> int:
    found = 0
    try:
        entries = os.listdir("/proc")
    except OSError:
        return 0
    for name in entries:
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/status", "r") as f:
                for line in f:
                    if line.startswith("Uid:"):
                        if int(line.split()[1]) == uid:
                            found += 1
                            os.kill(int(name), signal.SIGKILL)
                        break
        except (OSError, ValueError):
            continue
    return found


class Sandbox:
    """One run's private folder and user id. Use as a context manager."""

    def __init__(self, slot: int):
        self.slot = slot
        self.uid = UID_BASE + slot
        self.dir = ""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="judge-run-")
        os.chown(self.dir, self.uid, self.uid)
        os.chmod(self.dir, 0o700)
        return self

    def __exit__(self, *exc):
        kill_user(self.uid, wait=2.0)
        shutil.rmtree(self.dir, ignore_errors=True)
        return False

    def write(self, name: str, data: bytes):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as f:
            f.write(data)
        os.chown(path, self.uid, self.uid)
        os.chmod(path, 0o644)
        return path

    def env(self, extra: Optional[dict] = None) -> dict:
        env = {"PATH": CLEAN_PATH, "HOME": self.dir, "TMPDIR": self.dir, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
        env.update(extra or {})
        return env

    def run(self, command: List[str], stdin_bytes: bytes, limits: Limits, extra_env: Optional[dict] = None) -> RunResult:
        stdin_path = self.write(f"stdin-{os.urandom(4).hex()}", stdin_bytes)
        out_path = os.path.join(self.dir, f"stdout-{os.urandom(4).hex()}")
        err_path = os.path.join(self.dir, f"stderr-{os.urandom(4).hex()}")
        launcher = [
            sys.executable, "-I", LAUNCHER,
            str(self.uid), str(self.uid), str(limits.cpu_seconds), str(limits.nproc), str(limits.nofile), str(limits.fsize_mb), str(limits.data_mb),
            self.dir, "--", *command,
        ]
        timed_out = False
        with open(stdin_path, "rb") as fin, open(out_path, "wb") as fout, open(err_path, "wb") as ferr:
            proc = subprocess.Popen(launcher, stdin=fin, stdout=fout, stderr=ferr, env=self.env(extra_env), close_fds=True)
            try:
                proc.wait(timeout=limits.wall_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    proc.kill()
                proc.wait()
            finally:
                kill_user(self.uid)
        return RunResult(
            proc.returncode,
            _read_capped(out_path, MAX_OUTPUT_BYTES),
            _read_capped(err_path, MAX_ERROR_BYTES),
            timed_out,
        )


def _read_capped(path: str, cap: int) -> str:
    try:
        with open(path, "rb") as f:
            return f.read(cap).decode("utf-8", "replace")
    except OSError:
        return ""


# ── proof that the sandbox works, run for real ──────────────────────────────

_check_cache: Optional[Tuple[bool, str]] = None
_PROBE = (
    "import os, socket\n"
    "print('uid', os.getuid())\n"
    "try:\n"
    "    socket.socket(socket.AF_INET, socket.SOCK_STREAM); print('inet-socket-allowed')\n"
    "except OSError:\n"
    "    print('inet-socket-refused')\n"
    "try:\n"
    "    os.setuid(0); print('root-regained')\n"
    "except OSError:\n"
    "    print('root-refused')\n"
    "try:\n"
    "    open('/etc/judge-sandbox-probe', 'w'); print('system-write-allowed')\n"
    "except OSError:\n"
    "    print('system-write-refused')\n"
)


def check(force: bool = False) -> Tuple[bool, str]:
    """(works, reason). Runs a probe program through the real sandbox once and checks what it could and could not do."""
    global _check_cache
    if _check_cache is not None and not force:
        return _check_cache
    ok, why = supported()
    if not ok:
        _check_cache = (False, why)
        return _check_cache
    slot_numbers = get_slots()
    slot = slot_numbers.acquire()
    try:
        with Sandbox(slot) as box:
            result = box.run([sys.executable, "-I", "-c", _PROBE], b"", Limits(cpu_seconds=5, wall_seconds=10, data_mb=0))
    except Exception as e:
        _check_cache = (False, f"probe could not run: {type(e).__name__}: {e}")
        return _check_cache
    finally:
        slot_numbers.release(slot)
    lines = result.stdout.split()
    expected = [f"uid", str(UID_BASE + slot), "inet-socket-refused", "root-refused", "system-write-refused"]
    _check_cache = (True, "") if lines == expected and result.returncode == 0 else (False, f"probe gave {result.stdout!r} {result.stderr[:200]!r}")
    return _check_cache
