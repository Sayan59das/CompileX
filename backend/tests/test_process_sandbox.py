"""The no-Docker judge (process sandbox): the parts that can be tested anywhere. The real sandbox (users, limits, the syscall filter in the kernel) is
exercised by judge/checks/*.py inside the Render-like container; CI runs them (see .github/workflows/ci.yml).

Run from the backend folder:  python -m pytest tests/test_process_sandbox.py -q
"""

import asyncio
import importlib.util
import os
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import yaml
from fastapi.testclient import TestClient

from app.services import code_executor as ce
from app.services import process_sandbox as ps
from app.services import process_sandbox_exec as pse

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
TOKEN = "a-long-enough-secret-token"
X86_64, AARCH64 = 0xC000003E, 0xC00000B7
ALLOW, EPERM, KILL = 0x7FFF0000, 0x00050001, 0x80000000


# ── the syscall filter, run through a small BPF interpreter ─────────────────


def run_filter(nr, arch=X86_64, arg0=0):
    """What the kernel would answer for a syscall: interprets the program from build_filter()."""
    raw = pse.build_filter()
    prog = [struct.unpack("HBBI", raw[i:i + 8]) for i in range(0, len(raw), 8)]
    data = {0: nr, 4: arch, 16: arg0}
    acc, pc = 0, 0
    for _ in range(200):
        code, jt, jf, k = prog[pc]
        if code == pse.BPF_LD_W_ABS:
            acc, pc = data[k], pc + 1
        elif code == pse.BPF_JEQ_K:
            pc += 1 + (jt if acc == k else jf)
        elif code == pse.BPF_RET_K:
            return k
        else:
            raise AssertionError(f"unexpected instruction {code:#x}")
    raise AssertionError("the filter does not end")


@pytest.mark.parametrize("domain,name", [(2, "AF_INET"), (10, "AF_INET6"), (17, "AF_PACKET")])
def test_internet_and_packet_sockets_are_refused(domain, name):
    assert run_filter(pse.SYS_SOCKET, arg0=domain) == EPERM, name


@pytest.mark.parametrize("domain", [1, 16])      # AF_UNIX, AF_NETLINK: runtimes use these for themselves and they reach nothing outside
def test_local_sockets_are_still_allowed(domain):
    assert run_filter(pse.SYS_SOCKET, arg0=domain) == ALLOW


@pytest.mark.parametrize("nr", [101, 165, 166, 272, 308, 298, 321, 310, 311, 250, 248, 249, 425, 426, 427])
def test_dangerous_calls_are_refused_including_io_uring(nr):
    assert run_filter(nr) == EPERM


@pytest.mark.parametrize("nr", [0, 1, 2, 3, 9, 12, 56, 59, 60, 202, 231, 435, 334])       # read write open close mmap brk clone execve exit futex exit_group clone3 rseq
def test_ordinary_calls_stay_allowed_so_every_language_runtime_works(nr):
    assert run_filter(nr) == ALLOW


def test_a_different_cpu_architecture_is_killed_not_allowed():
    assert run_filter(1, arch=AARCH64) == KILL


def test_every_jump_in_the_filter_goes_forward_and_lands_inside_the_program():
    raw = pse.build_filter()
    prog = [struct.unpack("HBBI", raw[i:i + 8]) for i in range(0, len(raw), 8)]
    for pc, (code, jt, jf, _k) in enumerate(prog):
        if code == pse.BPF_JEQ_K:
            assert pc + 1 + jt < len(prog) and pc + 1 + jf < len(prog)
    assert prog[-1][3] == EPERM and prog[-2][3] == ALLOW and len(prog) < 4096


# ── the comparison grading uses ─────────────────────────────────────────────


@pytest.mark.parametrize("actual,expected,same", [
    ("6", "6", True), ("6\n", "6", True), ("6", "7", False),
    ("1 2 3", "[1, 2, 3]", True), ("1,2,3", "1 2 3", True),
    ("YES", "yes", True), ("True", "true", True),
    ("a\nb\n\n", "a\nb", True), ("a\nb", "a\nc", False), ("a", "a\na", False),
    ("  4   5 ", "4 5", True), ("", "", True), ("", "x", False),
])
def test_outputs_are_compared_the_way_the_docker_path_compares_them(actual, expected, same):
    assert ce.code_executor._outputs_match(actual, expected) is same


# ── when the process sandbox is used and when it is refused ─────────────────


@pytest.fixture
def no_docker(monkeypatch):
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", False)
    monkeypatch.setattr(ce, "docker_client", None)
    monkeypatch.setattr(ce.settings, "JUDGE_URL", "")


def cases_for():
    return [ce.TestCase(input_data="1", expected_output="1")]


def test_process_mode_without_docker_uses_the_process_sandbox_and_never_the_unsandboxed_path(no_docker, monkeypatch):
    used = []

    async def sandboxed(self, *a, **k):
        used.append("sandbox")
        return ce.SubmissionResult(1, 1, 0.0, [ce.ExecutionResult(True, True, "1")], 100)

    async def unsandboxed(self, *a, **k):
        used.append("UNSANDBOXED")

    monkeypatch.setattr(ce.settings, "SANDBOX_MODE", "process")
    monkeypatch.setattr(ce.settings, "DEBUG", True)             # even in development the sandbox wins when it is configured
    monkeypatch.setattr(ce.CodeExecutor, "_execute_in_process_sandbox", sandboxed)
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_subprocess", unsandboxed)
    asyncio.run(ce.code_executor.execute_code("print(1)", "python", cases_for()))
    assert used == ["sandbox"]


def test_production_without_docker_and_without_the_sandbox_still_refuses(no_docker, monkeypatch):
    monkeypatch.setattr(ce.settings, "SANDBOX_MODE", "")
    monkeypatch.setattr(ce.settings, "DEBUG", False)

    async def never(self, *a, **k):
        raise AssertionError("code must not run")

    monkeypatch.setattr(ce.CodeExecutor, "_execute_in_process_sandbox", never)
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_subprocess", never)
    result = asyncio.run(ce.code_executor.execute_code("print(1)", "python", cases_for()))
    assert result.passed_tests == 0 and "unavailable" in result.results[0].error


def test_when_the_sandbox_self_check_fails_nothing_runs(no_docker, monkeypatch):
    monkeypatch.setattr(ce.settings, "SANDBOX_MODE", "process")
    monkeypatch.setattr(ps, "check", lambda force=False: (False, "not Linux"))

    def boom(*a, **k):
        raise AssertionError("a program was started")

    monkeypatch.setattr(ps, "Sandbox", boom)
    result = asyncio.run(ce.code_executor.execute_code("print(1)", "python", cases_for()))
    assert result.passed_tests == 0 and result.total_tests == 1 and "unavailable" in result.results[0].error


def test_this_machine_is_reported_as_unsupported_unless_it_is_linux_x86_root():
    works, why = ps.supported()
    if sys.platform.startswith("linux") and os.geteuid() == 0:
        pytest.skip("this machine could run the sandbox")
    assert works is False and why


def test_run_slots_block_when_all_are_taken_and_hand_back_when_released():
    pool = ps._Slots(2)
    a, b = pool.acquire(), pool.acquire()
    assert {a, b} == {0, 1}
    got = []
    waiter = threading.Thread(target=lambda: got.append(pool.acquire()))
    waiter.start()
    time.sleep(0.2)
    assert got == []                                  # still waiting: both slots are in use
    pool.release(a)
    waiter.join(timeout=3)
    assert got == [a]


# ── the judge service in process mode ───────────────────────────────────────


def load_judge():
    spec = importlib.util.spec_from_file_location("judge_main_process", os.path.join(ROOT, "judge", "main.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_judge_in_process_mode_reports_its_mode_and_refuses_to_run_without_a_working_sandbox(monkeypatch):
    judge = load_judge()
    monkeypatch.setenv("JUDGE_TOKEN", TOKEN)
    monkeypatch.setattr(ce.settings, "SANDBOX_MODE", "process")
    monkeypatch.setattr(ps, "check", lambda force=False: (False, "probe failed"))
    # The health report's "docker" field is a fact about the machine; fix it here, or the test depends on where it runs (GitHub's
    # runners have a Docker daemon, a laptop or a test container may not).
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", False)
    monkeypatch.setattr(ce, "docker_client", None)
    ran = []

    async def fake(self, *a, **k):
        ran.append(1)
        return ce.SubmissionResult(1, 1, 0.0, [ce.ExecutionResult(True, True, "1")], 100)

    monkeypatch.setattr(ce.CodeExecutor, "execute_code", fake)
    body = {"code": "print(1)", "language": "python", "test_cases": [{"input_data": "1", "expected_output": "1"}]}
    with TestClient(judge.app) as client:
        assert client.get("/health").json() == {"status": "no-sandbox", "mode": "process", "sandbox": False, "docker": False}
        assert client.post("/run", json=body, headers={"X-Judge-Token": TOKEN}).status_code == 503
        monkeypatch.setattr(ps, "check", lambda force=False: (True, ""))
        assert client.get("/health").json() == {"status": "ok", "mode": "process", "sandbox": True, "docker": False}
        assert client.post("/run", json=body, headers={"X-Judge-Token": TOKEN}).status_code == 200
        # on a machine with Docker the report says so, and the mode stays the one configured
        monkeypatch.setattr(ce, "DOCKER_AVAILABLE", True)
        monkeypatch.setattr(ce, "docker_client", object())
        assert client.get("/health").json() == {"status": "ok", "mode": "process", "sandbox": True, "docker": True}
    assert ran == [1]


# ── the Render files ────────────────────────────────────────────────────────


def test_the_render_image_has_an_init_process_the_compilers_and_the_sandbox_files():
    text = open(os.path.join(ROOT, "judge", "Dockerfile.render"), encoding="utf-8").read()
    assert 'ENTRYPOINT ["tini", "--"]' in text and "nodejs tini" in text
    for needed in ("gcc", "g++", "default-jdk-headless", "nodejs", "process_sandbox.py", "process_sandbox_exec.py", "code_executor.py", "judge/main.py"):
        assert needed in text
    assert "SANDBOX_MODE=process" in text


def test_the_render_blueprint_has_a_free_judge_service_whose_secret_is_shared_with_the_backend_without_typing_it():
    blueprint = yaml.safe_load(open(os.path.join(ROOT, "render.yaml"), encoding="utf-8"))
    services = {s["name"]: s for s in blueprint["services"]}
    judge = services["compilex-judge"]
    assert judge["plan"] == "free" and judge["dockerfilePath"] == "./judge/Dockerfile.render" and judge["dockerContext"] == "."
    env = {e["key"]: e for e in judge["envVars"]}
    assert env["JUDGE_TOKEN"].get("generateValue") is True
    shared = {e["key"]: e for e in services["compilex-backend"]["envVars"]}["JUDGE_TOKEN"]["fromService"]
    assert shared == {"type": "web", "name": "compilex-judge", "envVarKey": "JUDGE_TOKEN"}
