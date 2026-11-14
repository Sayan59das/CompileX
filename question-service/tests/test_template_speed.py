"""The N-Queens template is solved once per board size, not once per question (docs/scaling-plan.md, Phase 0).

Serving one question builds its template several times to top up the tests, and each build solved the n = 9 and n = 10 boards again:
about three seconds of one CPU per question, on a service that handles every player's request in threads of one process.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import dynamic_generator as G

# The number of ways to place n non-attacking queens on an n x n board (OEIS A000170), written out so that the test does not check
# the solver against itself.
KNOWN = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92, 9: 352, 10: 724}


@pytest.mark.parametrize("n", sorted(KNOWN))
def test_the_solver_gives_the_known_counts(n):
    assert G._n_queens_solutions(n) == KNOWN[n]


def test_a_board_size_is_solved_only_once():
    G._n_queens_solutions.cache_clear()
    for _ in range(25):
        G._n_queens_solutions(8)
    info = G._n_queens_solutions.cache_info()
    assert info.misses == 1 and info.hits == 24


@pytest.mark.parametrize("seed", range(12))
def test_every_question_the_template_builds_has_the_right_answers(seed):
    body = G._backtracking_n_queens_count(random.Random(seed))
    assert int(body["sample_output"]) == KNOWN[int(body["sample_input"])]
    assert len(body["test_cases"]) >= 5
    for case in body["test_cases"]:
        assert case["output"] == KNOWN[case["input"]], case


def test_building_the_template_again_does_not_solve_anything_again():
    G._n_queens_solutions.cache_clear()
    for seed in range(40):
        G._backtracking_n_queens_count(random.Random(seed))
    info = G._n_queens_solutions.cache_info()
    assert info.misses <= 10 and info.hits > 100, info   # at most one solve per board size 1..10
