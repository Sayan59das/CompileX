"""The judge machine's setup kit (judge/deploy/) and the sandbox's user: the safety choices stay in place.

No Docker needed. Run from the backend folder:  python -m pytest tests/test_judge_deploy.py -q
"""

import os
import re

import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DEPLOY = os.path.join(ROOT, "judge", "deploy")
COMPOSE = yaml.safe_load(open(os.path.join(DEPLOY, "docker-compose.yml"), encoding="utf-8"))
CADDYFILE = open(os.path.join(DEPLOY, "Caddyfile"), encoding="utf-8").read()
EXECUTOR = open(os.path.join(ROOT, "backend", "app", "services", "code_executor.py"), encoding="utf-8").read()


def test_only_the_front_door_is_published_and_the_judge_is_not():
    assert "ports" not in COMPOSE["services"]["judge"]
    assert sorted(COMPOSE["services"]["caddy"]["ports"]) == ["443:443", "80:80"]


def test_the_judge_container_has_no_extra_powers_and_needs_a_token():
    judge = COMPOSE["services"]["judge"]
    assert judge["cap_drop"] == ["ALL"] and "no-new-privileges:true" in judge["security_opt"] and judge["read_only"] is True
    assert any(str(e).startswith("JUDGE_TOKEN=${JUDGE_TOKEN:?") for e in judge["environment"])
    assert not judge.get("privileged")


def test_the_docker_socket_is_given_to_the_judge_only():
    holders = [n for n, s in COMPOSE["services"].items() if any("docker.sock" in str(v) for v in s.get("volumes", []))]
    assert holders == ["judge"]


def test_caddy_passes_only_the_two_paths_the_backend_uses_and_caps_the_body():
    assert "path /run /health" in CADDYFILE and "reverse_proxy judge:9000" in CADDYFILE
    assert 'respond "Not found" 404' in CADDYFILE and re.search(r"max_size\s+\d+MB", CADDYFILE)


def test_the_example_settings_have_no_secret_and_name_every_required_variable():
    text = open(os.path.join(DEPLOY, ".env.example"), encoding="utf-8").read()
    assert re.search(r"^JUDGE_TOKEN=\s*$", text, re.M) and re.search(r"^JUDGE_DOMAIN=\s*$", text, re.M)


def test_the_host_setup_script_opens_only_ssh_http_and_https_and_does_not_touch_ssh():
    script = open(os.path.join(DEPLOY, "setup-host.sh"), encoding="utf-8").read()
    assert "ufw default deny incoming" in script
    assert sorted(re.findall(r"ufw allow (\d+)/tcp", script)) == ["22", "443", "80"]
    assert "sshd_config" not in script and "PasswordAuthentication" not in script


def test_the_build_context_has_every_file_the_judge_image_copies():
    dockerfile = open(os.path.join(ROOT, "judge", "Dockerfile"), encoding="utf-8").read()
    for line in re.findall(r"^COPY (.+)$", dockerfile, re.M):
        *sources, _target = line.split()
        for source in sources:
            assert os.path.exists(os.path.join(ROOT, source)), f"judge/Dockerfile copies {source}, which does not exist"
    assert COMPOSE["services"]["judge"]["build"]["context"] == "../.." and os.path.isdir(os.path.join(ROOT, "backend"))


def test_the_players_program_runs_as_an_unprivileged_user_in_every_executor_call():
    assert 'SANDBOX_USER = "65534:65534"' in EXECUTOR
    assert EXECUTOR.count("user=SANDBOX_USER") == 2, "compiling and running must both use the unprivileged user"
    assert 'user="root"' in EXECUTOR and EXECUTOR.count('user="root"') == 1, "only the one-line folder setup may run as root"
