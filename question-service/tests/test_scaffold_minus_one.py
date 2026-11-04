"""'n, then n-1 rows' in the schema notation, and the extended readings of legacy typing that are off unless asked for.

A tree gives n and then n-1 edges. The notation could not say that, so a question with such an input could not be typed and its
starter code was a guess that read the wrong lines. `grid:int[n-1][2]` now says it, in all five languages; the question service
itself still types exactly what it typed before (the extra readings are for the backend's own hand-written questions).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import legacy_typing as lt
from model import scaffold

TREE = "n:int\ngrid:int[n-1][2]"
TREE_INPUTS = ["5\n1 2\n1 3\n2 4\n2 5", "1", "2\n1 2", "4\n1 2\n2 3\n3 4"]


def test_a_count_of_n_minus_one_is_read_and_enforced():
    schema = scaffold.parse_input_schema(TREE)
    assert scaffold.parse_input_text(schema, "5\n1 2\n1 3\n2 4\n2 5") == [5, [[1, 2], [1, 3], [2, 4], [2, 5]]]
    assert scaffold.parse_input_text(schema, "1") == [1, []]  # one node: no rows at all
    with pytest.raises(ValueError):
        scaffold.parse_input_text(schema, "5\n1 2\n1 3")  # too few rows
    with pytest.raises(ValueError):
        scaffold.parse_input_text(schema, "2\n1 2\n1 3")  # a row left over


@pytest.mark.parametrize("bad", ["n:int\ne:int[n-1]", "n:int\ne:int[3-1][2]", "e:int[n-1][2]", "n:int\ne:int[n-2][2]", "n:int\ne:int[m-1][2]"])
def test_a_misuse_of_the_count_is_refused(bad):
    with pytest.raises(ValueError):
        scaffold.parse_input_schema(bad)


def test_text_lines_can_hang_on_n_minus_one_too():
    schema = scaffold.parse_input_schema("n:int\ntexts:str[n-1]/lines")
    assert scaffold.parse_input_text(schema, "3\n1 2 L\n1 3 R") == [3, ["1 2 L", "1 3 R"]]


@pytest.mark.parametrize("lang", scaffold.LANGUAGES)
def test_every_language_gets_a_reader_for_n_minus_one_rows(lang):
    code = scaffold.starter_code(scaffold.parse_input_schema(TREE), scaffold.parse_output_schema("int"), "solve")
    assert lang in code and scaffold.MARKER_TEXT in code[lang]
    assert "n-1" in code[lang]


# ── legacy typing: the extra readings are opt in ────────────────────────────────────────────────────────────────────────

def test_the_service_does_not_type_a_tree_input_unless_asked_to():
    """What the service serves must not change: an input it could not type before is still refused by default."""
    assert lt.infer_input_schema(TREE_INPUTS) is None
    assert lt.type_question([(t, "0") for t in TREE_INPUTS], TREE_INPUTS[0], "0") is None


def test_the_extended_reading_types_it_and_verifies_every_input():
    built = lt.infer_input_schema(TREE_INPUTS, extended=True)
    assert built is not None and built[0] == TREE
    typed = lt.type_question([(t, "0") for t in TREE_INPUTS], TREE_INPUTS[0], "0", extended=True)
    assert typed["input_schema"] == TREE and set(typed["starter_code"]) == set(scaffold.LANGUAGES)


def test_the_extended_reading_still_refuses_what_does_not_fit_every_input():
    assert lt.infer_input_schema(["5\n1 2\n1 3\n2 4\n2 5", "4\n1 2\n2 3"], extended=True) is None  # n=4 but two rows


def test_text_lines_on_a_count_are_read_only_when_asked():
    words = ["3\nflower\nflow\nflight", "1\nhello", "2\nabc\nabd"]
    assert lt.infer_input_schema(words) is None
    assert lt.infer_input_schema(words, extended=True)[0] == "n:int\ntexts:str[n]/lines"


def test_what_was_typed_before_is_typed_the_same_with_the_extended_readings_on():
    for inputs in (["5\n3 -1 4 1 5", "3\n1 2 3"], ["2 9\n1 2 3\n4 5 6", "1 9\n7 8 9"], ["hello\n42", "ab\n7"]):
        assert lt.infer_input_schema(inputs, extended=True) == lt.infer_input_schema(inputs)
