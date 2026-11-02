"""Starter code the editor can lock: five languages in one shape, and a reader that provably fits the question's own tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

import main_dynamic
from model import legacy_typing as lt
from model import scaffold

FIVE = {"python", "cpp", "java", "javascript", "c"}

SCHEMAS = [
    ("n:int\narr:int[n]", "int"),
    ("n:int q:int\ns:str\nps:int[q]/lines", "int[]/lines"),
    ("n:int m:int\ngrid:int[n][3]", "int"),
    ("s:str\nk:int", "str"),
    ("n:int\nw:str[n]", "int[]"),
    ("n:int s:str\narr:int[n]", "str"),
]


# ── the shape every starter shares, which is what the editor locks against ──

@pytest.mark.parametrize("schema_text,out_text", SCHEMAS)
def test_every_language_has_the_same_locked_shape(schema_text, out_text):
    code = scaffold.starter_code(scaffold.parse_input_schema(schema_text), scaffold.parse_output_schema(out_text), "solve")
    assert set(code) == FIVE
    for language, text in code.items():
        lines = text.split("\n")
        assert text.count(scaffold.MARKER_TEXT) == 1, language
        marker = next(i for i, line in enumerate(lines) if scaffold.MARKER_TEXT in line)
        logic = next(i for i, line in enumerate(lines) if "Write your logic here" in line)
        assert logic < marker, language                  # the player's part comes before the locked harness
        assert "solve(" in lines[logic - 1], language    # the signature is the line right above the note


def test_a_list_of_strings_has_no_c_starter_but_keeps_the_other_four():
    code = scaffold.starter_code(scaffold.parse_input_schema("n:int"), scaffold.parse_output_schema("str[]/lines"), "solve")
    assert "c" not in code and FIVE - {"c"} <= set(code)


def test_the_c_starter_passes_arrays_with_their_length_and_asks_for_a_result_buffer():
    schema = scaffold.parse_input_schema("n:int\narr:int[n]")
    code = scaffold.c_code(schema, scaffold.parse_output_schema("int[]"), "solve")
    assert "long long solve(long long n, const long long* arr, long long arr_len, long long* result)" in code
    assert code.startswith("#define _POSIX_C_SOURCE 200809L")      # getline and strndup need it under -std=c17


def test_with_c_starter_only_adds_c():
    question = {"starter_code": {"python": "p", "cpp": "c++"}, "input_schema": "n:int\narr:int[n]", "output_schema": "int",
                "function_name": "solve"}
    served = scaffold.with_c_starter(question)
    assert served["python"] == "p" and served["cpp"] == "c++" and "int main(void)" in served["c"]
    assert question["starter_code"] == {"python": "p", "cpp": "c++"}          # the stored question is not touched
    assert scaffold.with_c_starter({**question, "starter_code": {"c": "mine"}}) == {"c": "mine"}
    assert scaffold.with_c_starter({"starter_code": {"python": "p"}}) == {"python": "p"}   # no schema: returned as stored
    assert scaffold.with_c_starter({}) is None


def test_a_stored_list_question_gets_stubs_that_return_an_empty_list_not_nothing():
    stored = {
        "starter_code": {
            "python": "def solve(n):\n    # Write your logic here\n    pass\n\n\n# marker\n",
            "javascript": "function solve(n) {\n    // Write your logic here\n}\n\n// marker\n",
            "cpp": "unchanged",
        },
        "input_schema": "n:int", "output_schema": "int[]", "function_name": "solve",
    }
    served = scaffold.served_starter(stored)
    assert "    return []\n" in served["python"] and "pass" not in served["python"]
    assert "    return [];\n}" in served["javascript"]
    assert served["cpp"] == "unchanged" and "int main(void)" in served["c"]
    assert stored["starter_code"]["python"].count("pass") == 1                  # the stored question is not touched
    odd = {**stored, "starter_code": {"python": "def solve(n):\n    return 7\n"}}  # a stub the scaffold did not write is left alone
    assert scaffold.served_starter(odd)["python"] == "def solve(n):\n    return 7\n"
    scalar = {**stored, "output_schema": "int"}                                  # a single value needs no change
    assert "pass" in scaffold.served_starter(scalar)["python"]


# ── reading a structure off the stored tests of an older question ──

def test_a_count_then_a_list():
    result = lt.type_question([("3\n1 2 3", "6"), ("2\n5 5", "10")], "1\n7", "7")
    assert result["input_schema"] == "n:int\narr:int[n]" and result["output_schema"] == "int"
    assert result["function_name"] == "solve" and [p["name"] for p in result["parameters"]] == ["n", "arr"]
    assert set(result["starter_code"]) == FIVE
    assert result["input_format"].startswith("First line:")


def test_two_counts_a_string_and_a_list_with_one_value_per_line():
    tests = [("3 2\nEOO\n3\n2", "1\n0"), ("2 3\nOE\n1\n2\n2", "0\n0\n1")]
    result = lt.type_question(tests, "3 2\nEOO\n3\n2", "1 0")   # the sample prints its answers on one line: still the same type
    assert result["input_schema"] == "n:int m:int\ns:str\nvals:int[m]/lines"
    assert result["output_schema"] == "int[]/lines"


def test_rows_that_hang_on_a_count_are_a_grid():
    tests = [("2 5\n1 2 3\n4 5 6", "21"), ("3 5\n1 1 1\n2 2 2\n3 3 3", "18")]
    result = lt.type_question(tests, "2 5\n1 2 3\n4 5 6", "21")
    assert result["input_schema"] == "n:int m:int\ngrid:int[n][3]"


def test_a_line_of_numbers_with_no_count_is_one_list_of_any_length():
    tests = [("13 10 2", "13"), ("5 5", "5"), ("4 9 1 2", "9")]
    result = lt.type_question(tests, "1 2 3", "3")
    assert result["input_schema"] == "arr:int[0]"
    assert result["input_format"] == "First line: one line of integers, the list arr."


def test_a_question_whose_sample_and_tests_disagree_is_not_typed():
    # the sample has a count line and the tests do not: no single reader fits both, so none is offered
    assert lt.type_question([("8 5 14", "27"), ("7 2 2", "11")], "3\n2 12 4", "18") is None


def test_numbers_beyond_64_bits_are_not_typed():
    assert lt.type_question([("3\n1 2 3", "6"), ("1\n99999999999999999999", "9")], "1\n7", "7") is None


def test_a_question_with_no_tests_is_not_typed():
    assert lt.type_question([], "1\n7", "7") is None


def test_the_output_type_is_the_most_specific_one_every_output_fits():
    assert lt.infer_output_schema(["5", "-3"], "7") == "int"
    assert lt.infer_output_schema(["1 2 3", "4"], "1 2") == "int[]"
    assert lt.infer_output_schema(["1\n2", "3"], "1 2") == "int[]/lines"
    assert lt.infer_output_schema(["YES\n0 0 1", "NO"], "NO") == "str"
    assert lt.infer_output_schema(["5", "6"], "five") == "str"     # a sample that is not a number: plain text


# ── what the service does with it ──

def _question(sample_input, tests):
    return {
        "title": "Add them up", "base_title": "Add them up", "problem_statement": "Print the sum of the numbers.",
        "input_format": "THE BANK'S OWN TEXT", "output_format": "THE BANK'S OWN TEXT",
        "sample_input": sample_input, "sample_output": "6", "test_cases": tests, "topic": "arrays", "difficulty": "easy",
    }


@pytest.fixture
def templates(monkeypatch):
    """Route /generate to a fake template generator that hands out one question and then runs dry."""
    monkeypatch.setattr(main_dynamic, "_bank_order", lambda topic, difficulty: [])
    monkeypatch.setattr(main_dynamic, "_pool_service", None)

    def serve(question):
        handed_out = []

        def fake(topic, difficulty, exclude_titles=()):
            if handed_out:
                raise main_dynamic.NoFreshQuestion("done")
            handed_out.append(question)
            return question

        monkeypatch.setattr(main_dynamic, "generate_dynamic", fake)
        return TestClient(main_dynamic.app)

    return serve


def test_a_question_that_can_be_typed_is_served_with_its_locked_starter(templates):
    client = templates(_question("3\n1 2 3", [{"input": "3\n1 2 3", "output": "6"}, {"input": "2\n4 4", "output": "8"}]))
    r = client.post("/generate", json={"topic": "arrays", "difficulty": "easy"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["function_name"] == "solve" and body["input_schema"] == "n:int\narr:int[n]"
    assert set(body["starter_code"]) == FIVE
    assert body["input_format"].startswith("First line:")      # the bank's own format text is replaced by the one read from the tests


def test_a_question_that_cannot_be_typed_is_not_served_at_all(templates):
    client = templates(_question("3\n1 2 3", [{"input": "8 5 14", "output": "27"}, {"input": "7 2 2", "output": "11"}]))
    r = client.post("/generate", json={"topic": "arrays", "difficulty": "easy"})
    assert r.status_code == 404 and "No unseen" in r.json()["detail"]
