"""'n m', then m edges, then 'src dst': the last line is read after the edges when the question's format says it is the last line.

The stored tests of such a question fit two readings equally well: the odd line comes first (the next m rows are then the edges) or last
(the m rows come first). The service used to take the first, so BFS Shortest Path was served as solve(n, m, k, q, grid) where k and q
held the FIRST EDGE and the last row of the grid was the source and destination; no solution written from the statement could read
its input, and the picture drawn from that schema was the wrong graph. The question's own words ("Last line: src dst") now decide
between readings that already fit every test, and a question that does not say so is read exactly as before.
"""

import contextlib
import io
import os
import random
import re
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import dynamic_generator as G
from model import legacy_typing as lt
from model.stdio import to_stdin, to_stdout

GRAPH_INPUTS = ["8 5\n0 1\n1 2\n2 3\n3 4\n4 5\n0 5", "6 4\n0 1\n1 2\n2 3\n4 5\n0 3", "9 6\n0 1\n1 2\n2 3\n3 4\n4 5\n5 6\n1 6"]
BFS = G._graph_bfs_shortest_path


def stored_tests(body):
    return [(to_stdin(tc["input"]), to_stdout(tc["output"])) for tc in body["test_cases"]]


# ── the rule ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_without_the_words_last_line_the_odd_line_is_still_read_first():
    """What the service serves must not change for any question that does not say so."""
    built = lt.infer_input_schema(GRAPH_INPUTS)
    assert built is not None and built[0] == "n:int m:int\nk:int q:int\ngrid:int[m][2]"
    typed = lt.type_question([(t, "0") for t in GRAPH_INPUTS], GRAPH_INPUTS[0], "0", input_format="Read input as described in the problem.")
    assert typed["input_schema"] == "n:int m:int\nk:int q:int\ngrid:int[m][2]"


@pytest.mark.parametrize("words", ["Last line: src dst.", "Final line: src dst", "the LAST LINE has the source and the destination", "then, on the last\nline, src dst"])
def test_with_the_words_last_line_the_edges_come_first(words):
    typed = lt.type_question([(t, "0") for t in GRAPH_INPUTS], GRAPH_INPUTS[0], "0", input_format=f"Line 1: n e. Next e lines: u v. {words}")
    assert typed["input_schema"] == "n:int m:int\ngrid:int[m][2]\nk:int q:int"
    assert [p["name"] for p in typed["parameters"]] == ["n", "m", "grid", "k", "q"]
    assert [p["example"] for p in typed["parameters"]][3:] == ["0", "5"], "k and q must hold the last line, not the first edge"


def test_a_cue_on_a_question_with_no_line_to_move_changes_nothing():
    """'Last line' on an input whose rows fill it exactly: there is no odd line, so both ways of reading are the same reading."""
    exact = ["3 2\n1 2\n3 4", "4 3\n1 2\n3 4\n5 6"]
    assert lt.infer_input_schema(exact, trailing=True) == lt.infer_input_schema(exact)
    assert lt.type_question([(t, "0") for t in exact], exact[0], "0", input_format="Last line: the last edge.")["input_schema"] == "n:int m:int\ngrid:int[m][2]"


def test_a_cue_whose_reading_does_not_fit_every_input_falls_back_to_the_default():
    # the count that would take the rows differs between the two inputs, so no single 'rows first' schema reads both
    inputs = ["9 3\n1 2\n3 4\n5 6\n7 8", "4 2\n1 2\n3 4\n5 6\n7 8"]
    assert lt.infer_input_schema(inputs, trailing=True) == lt.infer_input_schema(inputs)


# ── the template that had the problem ───────────────────────────────────────────────────────────────────────────────────────

def test_every_format_wording_of_bfs_shortest_path_says_where_the_last_line_is():
    formats = {BFS(random.Random(seed))["input_format"] for seed in range(200)}
    assert len(formats) == 5
    assert all(lt._LAST_LINE.search(f) for f in formats), [f for f in formats if not lt._LAST_LINE.search(f)]


def bfs_distance(n, m, grid, k, q):
    adjacent = {v: [] for v in range(n)}
    for u, v in grid:
        adjacent[u].append(v)
        adjacent[v].append(u)
    seen, queue = {k: 0}, deque([k])
    while queue:
        v = queue.popleft()
        for w in adjacent[v]:
            if w not in seen:
                seen[w] = seen[v] + 1
                queue.append(w)
    return seen.get(q, -1)


def run_starter(code, stdin, solve):
    """The served Python starter with its function body replaced by `solve`, fed `stdin`; what it prints."""
    namespace = {"__name__": "served"}
    exec(compile(code, "starter", "exec"), namespace)
    namespace["solve"] = solve
    out, saved = io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out):
            namespace["main"]()
    finally:
        sys.stdin = saved
    return out.getvalue().strip()


def served(seed):
    """(body, typed) for the template at this seed, typed the way the service types it; typed is None when it is not served."""
    body = BFS(random.Random(seed))
    return body, lt.type_question(stored_tests(body), to_stdin(body["sample_input"]), to_stdout(body["sample_output"]), input_format=body["input_format"])


SERVABLE = [seed for seed in range(80) if served(seed)[1] is not None]   # the service never serves a question it cannot type, so only these exist


def test_most_seeds_of_the_template_can_be_served():
    """The service skips a question it cannot type; the test below uses only the ones it serves, so there must be plenty of them."""
    assert len(SERVABLE) >= 60 and len(SERVABLE[:25]) == 25


@pytest.mark.parametrize("seed", SERVABLE[:25])
def test_a_solution_written_from_the_statement_passes_every_test_of_the_served_question(seed):
    body, typed = served(seed)
    assert typed is not None
    assert [p["name"] for p in typed["parameters"]] == ["n", "m", "grid", "k", "q"], typed["input_schema"]
    for stdin, want in stored_tests(body) + [(to_stdin(body["sample_input"]), to_stdout(body["sample_output"]))]:
        assert run_starter(typed["starter_code"]["python"], stdin, bfs_distance) == want.strip(), stdin


def test_the_reading_the_service_used_to_serve_could_not_pass_its_own_tests():
    """The regression this fixes, made visible: the same solution fails every test when the format's words are not heard."""
    body = BFS(random.Random(0))
    typed = lt.type_question(stored_tests(body), to_stdin(body["sample_input"]), to_stdout(body["sample_output"]))   # no input_format
    assert [p["name"] for p in typed["parameters"]] == ["n", "m", "k", "q", "grid"]
    failures = 0
    for stdin, want in stored_tests(body):
        try:
            got = run_starter(typed["starter_code"]["python"], stdin, lambda n, m, k, q, grid: bfs_distance(n, m, grid, k, q))
        except Exception:
            got = None
        failures += got != want.strip()
    assert failures > 0


def test_the_service_hands_the_questions_own_format_to_the_typing():
    import main_dynamic

    body = BFS(random.Random(0))
    result = {"test_cases": body["test_cases"], "sample_input": body["sample_input"], "sample_output": body["sample_output"], "input_format": body["input_format"]}
    typed = main_dynamic._typed_fields(result)
    assert typed is not None and typed["input_schema"] == "n:int m:int\ngrid:int[m][2]\nk:int q:int"
    # and a result without a format is typed the old way instead of failing
    del result["input_format"]
    assert main_dynamic._typed_fields(result)["input_schema"] == "n:int m:int\nk:int q:int\ngrid:int[m][2]"
