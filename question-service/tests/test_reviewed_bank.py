"""The reviewed bank: complete records only, stateless per-player selection, typed fields through /generate."""

import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

import main_dynamic
from model import reviewed_bank as rb
from model import scaffold

STARTER = {lang: f"// {lang} starter\n" for lang in ("python", "cpp", "java", "javascript")}


def record(title, topic="arrays", difficulty="easy", **override):
    q = {
        "title": title, "problem_statement": f"Solve {title} using the numbers given on the second line.",
        "input_format": "n then the numbers", "output_format": "one integer", "constraints": "1 <= n <= 100",
        "sample_input": "3\n1 2 3", "sample_output": "6",
        "test_cases": [{"input": "3\n1 2 3", "output": "6"}, {"input": "1\n5", "output": "5"}, {"input": "2\n4 4", "output": "8"}],
        "topic": topic, "difficulty": difficulty, "function_name": "solve_it",
        "parameters": [{"name": "n", "type": "int"}, {"name": "a", "type": "List[int]"}], "return_type": "int",
        "return_description": "The answer to the problem", "starter_code": copy.deepcopy(STARTER),
        "input_schema": "n:int\na:int[n]", "output_schema": "int", "source": "reviewed",
    }
    q.update(override)
    return q


@pytest.fixture
def bank(tmp_path):
    def make(*lines):
        path = tmp_path / "reviewed_bank.jsonl"
        path.write_text("\n".join(json.dumps(x) if not isinstance(x, str) else x for x in lines) + "\n", encoding="utf-8")
        rb.reload(str(path))
        return path

    yield make
    rb.reload(os.path.join(tmp_path, "does_not_exist.jsonl"))  # leave the module empty for other tests


def test_a_missing_file_means_an_empty_bank(tmp_path):
    rb.reload(str(tmp_path / "nothing.jsonl"))
    assert rb.pool_size("arrays", "easy") == 0
    assert rb.get_question("arrays", "easy") is None
    assert rb.get_stats() == {}


def test_complete_records_are_served_with_every_test_and_the_typed_fields(bank):
    bank(record("Alpha"))
    q = rb.get_question("arrays", "easy")
    assert q["title"] == q["base_title"] == "Alpha"
    assert q["source"] == "reviewed"
    assert len(q["test_cases"]) == 3
    assert set(q["starter_code"]) == {"python", "cpp", "java", "javascript"}
    assert q["function_name"] == "solve_it" and q["parameters"][0]["name"] == "n"


def test_served_questions_are_copies(bank):
    bank(record("Alpha"))
    first = rb.get_question("arrays", "easy")
    first["test_cases"].clear()
    first["starter_code"]["python"] = "ruined"
    again = rb.get_question("arrays", "easy")
    assert len(again["test_cases"]) == 3 and again["starter_code"]["python"] != "ruined"


def test_incomplete_records_are_skipped_with_a_reason(bank, capsys):
    bank(
        record("Good"),
        record("No Starter", starter_code={}),
        record("One Language Missing", starter_code={"python": "x", "cpp": "x", "java": "x"}),
        record("Too Few Tests", test_cases=[{"input": "1", "output": "1"}]),
        record("Bad Level", difficulty="impossible"),
        record("No Signature", function_name=""),
        record("Odd Parameters", parameters=["n"]),
        "{this is not json",
    )
    assert rb.pool_size("arrays", "easy") == 1
    out = capsys.readouterr().out
    for name in ("No Starter", "One Language Missing", "Too Few Tests", "Bad Level", "No Signature", "Odd Parameters"):
        assert name in out
    assert "not valid JSON" in out


def test_a_duplicate_title_is_served_only_once(bank):
    bank(record("Same"), record("same", topic="strings"))
    assert sum(rb.get_stats().get(t, {}).get("easy", 0) for t in ("arrays", "strings")) == 1


def test_selection_is_exact_about_topic_and_difficulty_and_forgiving_about_spelling(bank):
    bank(record("A", topic="arrays", difficulty="easy"), record("B", topic="sliding window", difficulty="medium"))
    assert rb.get_question("strings", "easy") is None
    assert rb.get_question("arrays", "hard") is None      # never answers with a different difficulty
    assert rb.get_question("Array", "EASY")["title"] == "A"
    assert rb.get_question("sliding-window", "medium")["title"] == "B"
    assert rb.pool_size("sliding_window", "medium") == 1


def test_a_player_never_gets_an_excluded_title_and_nothing_is_remembered(bank):
    bank(*[record(f"Q{i}") for i in range(5)])
    seen = set()
    for _ in range(5):
        q = rb.get_question("arrays", "easy", exclude_titles=[t.lower() for t in seen])
        assert q["title"] not in seen
        seen.add(q["title"])
    assert rb.get_question("arrays", "easy", exclude_titles=[t.lower() for t in seen]) is None
    # another player is unaffected by what the first one saw
    assert rb.get_question("arrays", "easy", exclude_titles=[]) is not None


def test_picks_vary(bank):
    bank(*[record(f"Q{i}") for i in range(8)])
    assert len({rb.get_question("arrays", "easy")["title"] for _ in range(60)}) > 3


# ── through the service ─────────────────────────────────────────────────────────

@pytest.fixture
def client(bank):
    return TestClient(main_dynamic.app)


def test_reviewed_questions_come_first_and_other_banks_follow(bank):
    bank(record("Alpha"))
    assert main_dynamic._bank_order("arrays", "easy")[0] == "reviewed"
    assert "reviewed" not in main_dynamic._bank_order("arrays", "hard")


def test_generate_passes_the_typed_fields_through(bank, client):
    bank(record("Alpha"))
    r = client.post("/generate", json={"topic": "arrays", "difficulty": "easy"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == body["base_title"] == "Alpha"
    assert body["function_name"] == "solve_it" and body["return_type"] == "int"
    assert set(body["starter_code"]) == {"python", "cpp", "java", "javascript", "c"}   # the four stored ones, plus the C entry added when it is served
    assert body["constraints"] == "1 <= n <= 100"
    assert len(body["test_cases"]) == 3


def test_generate_respects_the_players_history_then_falls_back(bank, client, monkeypatch):
    bank(record("Alpha"), record("Beta"))
    seen, reviewed = [], []
    for _ in range(2):
        body = client.post("/generate", json={"topic": "arrays", "difficulty": "easy", "exclude_titles": seen}).json()
        reviewed.append(body["title"])
        seen += [body["title"].lower(), body["base_title"].lower()]
    assert sorted(reviewed) == ["Alpha", "Beta"]
    third = client.post("/generate", json={"topic": "arrays", "difficulty": "easy", "exclude_titles": seen}).json()
    assert third["title"] not in ("Alpha", "Beta")      # both reviewed questions are used up for this player


def test_questions_from_other_banks_come_with_a_verified_locked_starter(bank, client):
    bank()  # nothing reviewed, so the older banks answer
    r = client.post("/generate", json={"topic": "arrays", "difficulty": "medium"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["function_name"] == "solve" and body["parameters"] and body["input_schema"] and body["output_schema"]
    assert {"python", "cpp", "java", "javascript"} <= set(body["starter_code"])
    for language, code in body["starter_code"].items():
        assert scaffold.MARKER_TEXT in code, language   # the line the editor locks from


def test_stats_counts_the_reviewed_questions(bank, client):
    bank(record("A"), record("B", topic="strings"))
    assert client.get("/stats").json()["reviewed_questions"] == 2
