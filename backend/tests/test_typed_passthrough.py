"""A reviewed question keeps its own signature and starter code; every other question is handled as before.

Run from the backend folder:  python -m pytest tests/test_typed_passthrough.py -q
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.models import DifficultyLevel
from app.services import ai_generator as ag

STARTER = {
    "python": "def count_pairs(n, a):\n    pass\n\n\nif __name__ == '__main__':\n    pass\n",
    "cpp": "long long count_pairs(long long n, const vector<long long>& a) { return 0; }\nint main() {}\n",
    "java": "public class Solution { static long count_pairs(long n, long[] a) { return 0; } public static void main(String[] x) {} }\n",
    "javascript": "function count_pairs(n, a) {}\nrequire('fs').readFileSync(0, 'utf8');\n",
}
PARAMS = [{"name": "n", "type": "int", "description": "A value", "example": "3"},
          {"name": "a", "type": "List[int]", "description": "A list of values", "example": "[1, 2, 3]"}]


def reviewed(**override):
    data = {
        "title": "Pair Counter", "base_title": "Pair Counter",
        "problem_statement": "Count the pairs of numbers whose sum is even.",
        "input_format": "First line: n. Second line: n integers.", "output_format": "One integer.",
        "constraints": "1 <= n <= 1000", "sample_input": "3\n1 2 3", "sample_output": "1",
        "test_cases": [{"input": "3\n1 2 3", "output": "1"}], "topic": "math",
        "function_name": "count_pairs", "parameters": PARAMS, "return_type": "int",
        "return_description": "The answer to the problem", "starter_code": STARTER,
    }
    data.update(override)
    return data


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """_build_result asks an image service and draws diagrams; neither belongs in a unit test."""
    from app.services.nvidia_image_service import nvidia_image_service

    async def nothing(self_or_text, *a, **k):
        return None

    monkeypatch.setattr(type(nvidia_image_service), "analyze_and_generate_image", nothing)


def build(data):
    return asyncio.run(ag._build_result(data, DifficultyLevel.EASY, data.get("topic")))


def test_a_reviewed_question_keeps_its_own_signature_and_starter_code():
    out = build(reviewed())
    assert out["function_name"] == "count_pairs"
    assert json.loads(out["starter_code"]) == STARTER
    assert json.loads(out["parameters"]) == PARAMS
    assert out["return_type"] == "int"


def test_the_constraints_the_service_sent_are_shown_to_the_player():
    assert "**Constraints**\n1 <= n <= 1000" in build(reviewed())["description"]


def test_base_title_still_travels_with_the_question():
    assert build(reviewed())["base_title"] == "Pair Counter"


@pytest.mark.parametrize("damage", [
    {"starter_code": None},
    {"starter_code": {"python": "x"}},
    {"starter_code": {**STARTER, "java": "   "}},
    {"parameters": []},
    {"parameters": ["n"]},
    {"function_name": ""},
    {"return_type": ""},
])
def test_an_incomplete_question_is_not_trusted_and_falls_back_to_the_old_guess(damage):
    data = reviewed(**damage)
    assert ag._typed_signature(data) is None
    out = build(data)  # must still produce a playable question the old way
    assert out["function_name"] and json.loads(out["starter_code"])


def test_a_question_without_typed_fields_is_untouched():
    legacy = reviewed()
    for key in ("function_name", "parameters", "return_type", "return_description", "starter_code"):
        legacy.pop(key)
    out = build(legacy)
    assert out["function_name"]                      # guessed from the text, as before
    assert json.loads(out["starter_code"]) != STARTER
