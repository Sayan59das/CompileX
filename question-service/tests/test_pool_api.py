"""Checks for the HTTP routes of the pool, and for how main_dynamic mounts them."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pool.api import build_router, players_from
from pool.history import MemorySeenStore
from pool.repository import SqlRepository
from pool.service import QuestionService, ReviewedBank
from tests.pool_helpers import Counter, FakeBank, add_live, make_question

TOKEN = "s3cret-token"


def make_client(live=3, bank=0, token=TOKEN):
    repo = SqlRepository.sqlite(":memory:")
    ids = [add_live(repo, n) for n in range(1, live + 1)]
    questions = [make_question(100 + i, title=f"Bank {100 + i}") for i in range(bank)]
    service = QuestionService(repo, MemorySeenStore(clock=Counter()), ReviewedBank(FakeBank({("arrays", "easy"): questions} if bank else {})))
    app = FastAPI()
    app.include_router(build_router(service, token))
    return TestClient(app), service, ids


def test_players_are_read_from_repeated_and_comma_separated_values():
    assert players_from(["1", "2"]) == ["1", "2"] and players_from(["1, 2", "3"]) == ["1", "2", "3"]
    assert players_from(None) == [] and players_from([" ", ","]) == []


def test_a_question_comes_back_without_its_hidden_tests():
    client, _, _ = make_client()
    response = client.get("/api/question", params={"topic": "arrays", "difficulty": "easy", "player_id": "p1"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"].startswith("Question") and body["sample_tests"][0]["output"].startswith("SAMPLE-") and body["repeat"] is False
    assert "test_cases" not in body and "HIDDEN" not in response.text and body["prefetched"] is False
    assert set(body["starter_code"]) == {"python", "cpp", "java", "javascript", "c"}   # C is added when a question is served


def test_the_same_player_gets_different_questions_until_the_pool_runs_out():
    client, _, _ = make_client(live=3)
    params = {"topic": "arrays", "difficulty": "easy", "player_id": "p1"}
    ids = [client.get("/api/question", params=params).json()["id"] for _ in range(3)]
    assert len(set(ids)) == 3
    again = client.get("/api/question", params=params).json()
    assert again["repeat"] is True and again["id"] == ids[0]


def test_a_lobby_can_be_given_as_repeated_or_comma_separated_player_ids():
    client, service, _ = make_client(live=4)
    first = client.get("/api/question", params=[("topic", "arrays"), ("difficulty", "easy"), ("player_id", "a"), ("player_id", "b")]).json()
    assert first["id"] in service.seen.seen(["a"], "arrays", "easy") and first["id"] in service.seen.seen(["b"], "arrays", "easy")
    second = client.get("/api/question", params={"topic": "arrays", "difficulty": "easy", "player_id": "a,c"}).json()
    assert second["id"] != first["id"] and second["id"] in service.seen.seen(["c"], "arrays", "easy")


def test_prefetch_gives_a_question_and_counts_it_as_served():
    client, _, _ = make_client(live=3)
    params = {"topic": "arrays", "difficulty": "easy", "player_id": "p1"}
    ahead = client.get("/api/question/prefetch", params=params).json()
    assert ahead["prefetched"] is True
    shown = client.get("/api/question", params=params).json()
    assert shown["id"] != ahead["id"]


def test_bad_requests_are_refused_with_a_reason():
    client, _, _ = make_client()
    assert client.get("/api/question", params={"topic": "arrays", "difficulty": "easy"}).status_code == 400
    assert client.get("/api/question", params={"topic": "arrays", "difficulty": "easy", "player_id": ","}).status_code == 400
    response = client.get("/api/question", params={"topic": "arrays", "difficulty": "extreme", "player_id": "p"})
    assert response.status_code == 400 and "difficulty" in response.json()["detail"]
    assert client.get("/api/question", params={"difficulty": "easy", "player_id": "p"}).status_code == 422
    assert client.get("/api/question", params={"topic": "arrays", "difficulty": "hard", "player_id": "p"}).status_code == 404


def test_difficulty_may_be_written_in_any_case():
    client, _, _ = make_client()
    assert client.get("/api/question", params={"topic": "Arrays", "difficulty": " EASY ", "player_id": "p"}).status_code == 200


def test_the_status_matches_the_database():
    client, service, ids = make_client(live=2, bank=2)
    body = client.get("/api/pool/status").json()
    row = next(p for p in body["pools"] if p["topic"] == "arrays" and p["difficulty"] == "easy")
    assert row["live"] == 2 and row["bank"] == 2 and body["live"] == 2
    service.repo.retire(ids[0])
    row = next(p for p in client.get("/api/pool/status").json()["pools"] if p["difficulty"] == "easy")
    assert row["live"] == 1 and row["retired"] == 1


def test_submit_grades_outputs_without_revealing_the_expected_ones():
    client, _, ids = make_client(live=1)
    qid = str(ids[0])
    good = client.post("/api/submit", json={"question_id": qid, "results": [f"HIDDEN-1-{i}" for i in range(5)]})
    assert good.status_code == 200 and good.json()["all_passed"] is True and good.json()["passed"] == 5
    bad = client.post("/api/submit", json={"question_id": qid, "results": ["x", "HIDDEN-1-1", "y", "z", "w"]})
    assert bad.json()["failed"] == [0, 2, 3, 4] and "HIDDEN" not in bad.text
    assert client.post("/api/submit", json={"question_id": qid, "results": ["x"]}).status_code == 400
    assert client.post("/api/submit", json={"question_id": "424242", "results": ["x"] * 5}).status_code == 404
    assert client.post("/api/submit", json={"results": []}).status_code == 422


def test_the_hidden_tests_need_the_internal_token():
    client, _, ids = make_client(live=1)
    url = f"/internal/questions/{ids[0]}/tests"
    assert client.get(url).status_code == 403
    assert client.get(url, headers={"X-Internal-Token": "wrong"}).status_code == 403
    ok = client.get(url, headers={"X-Internal-Token": TOKEN})
    assert ok.status_code == 200 and ok.json()["tests"][0] == {"input": "0\n0", "output": "HIDDEN-1-0"} and len(ok.json()["tests"]) == 5
    assert client.get("/internal/questions/999999/tests", headers={"X-Internal-Token": TOKEN}).status_code == 404


def test_the_internal_endpoint_is_switched_off_without_a_configured_token():
    client, _, ids = make_client(live=1, token=None)
    for headers in ({}, {"X-Internal-Token": ""}, {"X-Internal-Token": "anything"}):
        assert client.get(f"/internal/questions/{ids[0]}/tests", headers=headers).status_code == 403


def test_the_hidden_tests_never_appear_on_any_public_route():
    client, _, ids = make_client(live=2, bank=1)
    seen_text = []
    for player in ("a", "b", "c", "d"):
        seen_text.append(client.get("/api/question", params={"topic": "arrays", "difficulty": "easy", "player_id": player}).text)
        seen_text.append(client.get("/api/question/prefetch", params={"topic": "arrays", "difficulty": "easy", "player_id": player}).text)
    seen_text.append(client.get("/api/pool/status").text)
    assert not any("HIDDEN" in text for text in seen_text)


# ── mounted in the real service ──────────────────────────────────────────

def test_main_dynamic_mounts_the_pool_routes_and_asks_the_pool_first(monkeypatch):
    import main_dynamic
    repo = SqlRepository.sqlite(":memory:")
    add_live(repo, 1, topic="arrays", difficulty="easy")
    service = QuestionService(repo, MemorySeenStore(), ReviewedBank(FakeBank({})))
    monkeypatch.setattr(main_dynamic, "_pool_service", service)
    client = TestClient(main_dynamic.app)
    assert client.get("/api/pool/status").status_code == 200
    answer = client.post("/generate", json={"topic": "arrays", "difficulty": "easy", "exclude_titles": []})
    assert answer.status_code == 200 and answer.json()["title"] == "Question 1" and len(answer.json()["test_cases"]) == 5
    after = client.post("/generate", json={"topic": "arrays", "difficulty": "easy", "exclude_titles": ["question 1"]})
    assert after.status_code in (200, 404) and (after.status_code == 404 or after.json()["title"] != "Question 1")


def test_main_dynamic_loads_no_trained_model_and_no_torch():
    """Checked in a fresh interpreter: other tests legitimately import the older main.py in the same session."""
    import os
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys, main_dynamic\n"
        "assert not hasattr(main_dynamic, '_trained_generator')\n"
        "bad = [m for m in ('torch', 'model.generator', 'model.transformer_model') if m in sys.modules]\n"
        "assert not bad, bad\n"
        "print('clean')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and "clean" in result.stdout, result.stderr


def test_the_deployment_files_include_the_pool_and_no_torch():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dockerfile = open(os.path.join(root, "Dockerfile"), encoding="utf-8").read()
    requirements = open(os.path.join(root, "requirements.txt"), encoding="utf-8").read()
    assert "COPY pool/ ./pool/" in dockerfile and "torch" not in dockerfile and "torch" not in requirements
    assert "redis" in requirements and "psycopg" in requirements
