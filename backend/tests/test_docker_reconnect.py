"""After Docker Desktop restarts, the executor opens a new connection instead of failing every run until the backend restarts.

Run from the backend folder:  python -m pytest tests/test_docker_reconnect.py -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import code_executor as ce


class StaleClient:
    """What the client looks like after Docker Desktop restarted."""

    class containers:
        @staticmethod
        def run(**kwargs):
            raise OSError("(232, 'WriteFile', 'The pipe is being closed.')")


class FreshClient:
    calls = []

    def ping(self):
        return True

    class containers:
        @staticmethod
        def run(**kwargs):
            FreshClient.calls.append(kwargs)
            return "container"


@pytest.fixture
def stale(monkeypatch):
    import docker

    FreshClient.calls = []
    monkeypatch.setattr(ce, "docker_client", StaleClient)
    monkeypatch.setattr(docker, "from_env", lambda: FreshClient())
    return FreshClient


def test_a_stale_connection_is_replaced_and_the_run_is_retried_once(stale):
    assert ce._run_container(image="python:3.14-alpine", detach=True) == "container"
    assert stale.calls == [{"image": "python:3.14-alpine", "detach": True}]
    assert isinstance(ce.docker_client, FreshClient)          # later runs use the new connection


def test_when_docker_is_really_gone_the_original_error_is_raised(monkeypatch):
    import docker

    def refuse():
        raise OSError("docker is not running")

    monkeypatch.setattr(ce, "docker_client", StaleClient)
    monkeypatch.setattr(docker, "from_env", refuse)
    with pytest.raises(OSError, match="pipe is being closed"):
        ce._run_container(image="python:3.14-alpine")
