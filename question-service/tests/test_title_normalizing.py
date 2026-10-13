"""A player's history is sent as normalised titles (lowercase, spaces collapsed). Every bank must match against that form.

Some stored titles contain a double space, so comparing raw titles never matched and those questions could be served again.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import dataset_generator, question_db, reviewed_bank
from model.titles import normalize_title

MESSY = "Permutation p is an ordered set,  of integers"   # note the double space
HISTORY = [normalize_title(MESSY)]                         # what the backend sends back after the player saw it


def test_normalize_title_is_what_the_backend_stores():
    assert normalize_title("  Two   Sum \n") == "two sum"
    assert normalize_title(None) == ""
    assert normalize_title(MESSY) == "permutation p is an ordered set, of integers"


def _question(title, **extra):
    return {"title": title, "problem_statement": "Do the thing with the input given.", "input_format": "n", "output_format": "x",
            "sample_input": "1", "sample_output": "1", "test_cases": [{"input": "1", "output": "1"}] * 3,
            "topic": "arrays", "difficulty": "hard", **extra}


def test_question_db_does_not_serve_a_messy_title_the_player_already_had(monkeypatch):
    monkeypatch.setattr(question_db, "_loaded", True)
    monkeypatch.setattr(question_db, "_store", {("arrays", "hard"): [_question(MESSY)]})
    assert question_db.get_question("arrays", "hard", exclude_titles=HISTORY) is None
    assert question_db.get_question("arrays", "hard", exclude_titles=[])["title"] == MESSY


def test_dataset_bank_does_not_serve_a_messy_title_the_player_already_had(monkeypatch):
    q = _question(MESSY)
    monkeypatch.setattr(dataset_generator, "_load", lambda: None)
    monkeypatch.setattr(dataset_generator, "_dataset", [q])
    monkeypatch.setattr(dataset_generator, "_dataset_by_topic", {"arrays": [q]})
    assert dataset_generator.get_from_dataset("arrays", "hard", exclude_titles=HISTORY) is None
    assert dataset_generator.get_from_dataset("arrays", "hard", exclude_titles=[])["title"] == MESSY


def test_reviewed_bank_does_not_serve_a_messy_title_the_player_already_had(tmp_path):
    import json

    record = {**_question(MESSY, difficulty="easy"), "function_name": "solve_it",
              "parameters": [{"name": "n", "type": "int"}], "return_type": "int",
              "starter_code": {lang: "x" for lang in ("python", "cpp", "java", "javascript")}}
    path = tmp_path / "bank.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    reviewed_bank.reload(str(path))
    try:
        assert reviewed_bank.get_question("arrays", "easy", exclude_titles=HISTORY) is None
        assert reviewed_bank.get_question("arrays", "easy")["title"] == MESSY
    finally:
        reviewed_bank.reload(str(tmp_path / "nothing.jsonl"))


@pytest.mark.parametrize("raw", ["Two  Sum", " Two Sum", "Two\tSum", "TWO SUM\n"])
def test_any_spacing_of_the_same_title_counts_as_seen(raw):
    assert normalize_title(raw) == "two sum"
