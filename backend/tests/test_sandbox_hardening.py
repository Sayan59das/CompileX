"""The deployment file and the sandbox keep the safety settings the audit asked for (see docs/judge-evaluation.md, section 4).

These read docker-compose.yml and code_executor.py; they run no container. Run from the backend folder:
    python -m pytest tests/test_sandbox_hardening.py -q
"""

import os
import re

import pytest
import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
COMPOSE = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8"))
EXECUTOR = open(os.path.join(os.path.dirname(__file__), "..", "app", "services", "code_executor.py"), encoding="utf-8").read()


@pytest.mark.parametrize("service", ["db", "redis", "ai"])
def test_internal_services_listen_on_this_machine_only(service):
    for port in COMPOSE["services"][service].get("ports", []):
        assert str(port).startswith("127.0.0.1:"), f"{service} publishes {port} to every network interface"


def test_redis_needs_a_password_and_every_client_sends_it():
    command = " ".join(COMPOSE["services"]["redis"]["command"])
    assert "--requirepass" in command and "REDIS_PASSWORD" in command
    for service in ("api", "ai"):
        urls = [e for e in COMPOSE["services"][service]["environment"] if str(e).startswith("REDIS_URL=")]
        assert urls and all(":${REDIS_PASSWORD" in u for u in urls), f"{service} connects to Redis without the password"


def test_debug_is_off_unless_asked_for():
    assert "DEBUG=${DEBUG:-False}" in COMPOSE["services"]["api"]["environment"]


def test_the_example_env_file_lists_every_variable_compose_requires_and_holds_no_secrets():
    text = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read()
    needed = set(re.findall(r"\$\{([A-Z_]+)[:?\-}]", open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8").read()))
    needed -= set(re.findall(r"\$\{([A-Z_]+):-", open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8").read()))   # has a default
    for name in needed:
        assert re.search(rf"^{name}=", text, re.M), f"{name} is missing from .env.example"
        if re.search(r"PASSWORD|KEY", name):
            assert re.search(rf"^{name}=\s*$", text, re.M), f"{name} has a value in .env.example"


def test_sandbox_containers_are_limited():
    for setting in ('pids_limit=128', 'cap_drop=["ALL"]', 'security_opt=["no-new-privileges"]', 'network_disabled=True', 'memswap_limit="256m"'):
        assert setting in EXECUTOR, f"sandbox no longer sets {setting}"


def test_test_input_never_passes_through_a_shell_command_line():
    assert "echo \\\"" not in EXECUTOR and 'echo "' not in EXECUTOR, "test input is again put into a shell `echo`"
    assert "< /sandbox/input.txt" in EXECUTOR
