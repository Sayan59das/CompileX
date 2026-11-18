"""A question that is served can be played fairly, and the better-checked sources come first.

Found by measuring what every source hands a player (2026-11-14):

* the collected contest banks served questions whose statement points to a picture that was never collected, questions that accept any of
  several answers although one answer is stored and compared exactly, and answers judged with a tolerance;
* a collected question lost its own description of the input: only the generated "Then: n integers, the list arr" was served;
* 27 of the 137 templates could never be served, the simplest ones among them, because their sample ("5", then five numbers) and their
  hidden tests (the numbers alone) had different layouts;
* every template statement ended in the same sentence per difficulty ("[Hard] ... segment trees, bitmask DP ..."), whatever it was about;
* a collected question was preferred to a template, although a template's tests are computed by its own solver;
* three reviewed questions stored a test twice, and templates with few possible inputs were padded with repeated tests.
"""

import contextlib
import functools
import io
import itertools
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import dataset_generator, difficulty_templates as T, dynamic_generator as G, quality, question_db, reviewed_bank, smart_generator
from model.legacy_typing import type_question
from model.stdio import to_stdin, to_stdout


def q(statement, tests=(("1", "1"), ("2", "2"), ("3", "3")), output_format="", input_format="One line: the integer n, the number of items."):
    return {"title": "T", "problem_statement": statement, "input_format": input_format, "output_format": output_format,
            "test_cases": [{"input": i, "output": o} for i, o in tests]}


# ── what cannot be played fairly ────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("statement, why", [
    ("Take a look at the picture to see how the coordinates are defined: [Image] Find the cell.", "picture"),
    ("The field is shown in the figure below. Count the cells.", "picture"),
    ("Find a permutation. If there are multiple answers, print any of them.", "several answers"),
    ("Cover the graph with cycles. If there are several solutions, output any.", "several answers"),
    ("Print the vertices of the set in any order.", "several answers"),
    ("Print the area. Your answer is accepted if its absolute or relative error does not exceed 10^{-6}.", "tolerance"),
    ("This is an interactive problem. Ask queries and flush the output.", "interactive"),
])
def test_a_question_that_cannot_be_graded_by_one_stored_answer_is_left_out(statement, why):
    assert why in quality.disqualify(q(statement))


@pytest.mark.parametrize("statement", [
    "Given an array, print the sum of its elements.",
    "You may apply the operations in any order. Print the minimum number of operations.",   # the order is the player's freedom, the answer is one number
    "Print the average rounded to 2 decimal places.",                                        # exact once the rounding is stated
    "Imagine the array as a row of towers. Print how much water is trapped.",
    "Print the K-th largest value.",
])
def test_a_question_with_one_answer_is_kept(statement):
    assert quality.disqualify(q(statement)) is None


def test_a_question_that_never_says_what_its_input_is_is_left_out():
    """14 stored statements end at an empty '-----Input-----' heading and their input format is a placeholder or the sample's numbers."""
    cut_off = "Find the answer.\n\n-----Input-----"
    assert "does not say what the input is" in quality.disqualify(q(cut_off, input_format="Read input from standard input as described in the problem."))
    assert "does not say what the input is" in quality.disqualify(q("Find the answer.", input_format="4 1 3\n3 2 5 1"))
    assert quality.disqualify(q("Find it.\n\n-----Input-----\n\nThe first line contains n.\n\n-----Output-----\n\nOne number.", input_format="")) is None
    assert quality.disqualify(q("Add them.", input_format="Two integers")) is None


def test_a_statement_that_is_not_in_english_is_left_out():
    russian = "В Берляндском государственном университете локальная сеть. Выведите ответ."
    assert "not in English" in quality.disqualify(q(russian))
    assert quality.disqualify(q("Print the sum of a_i for 1 ≤ i ≤ n (all values ≤ 10^9).")) is None


def test_broken_stored_tests_are_left_out():
    assert "no expected output" in quality.disqualify(q("Sum.", tests=(("1", "1"), ("2", ""), ("3", "3"))))
    assert "two different answers" in quality.disqualify(q("Sum.", tests=(("1", "1"), ("1", "2"), ("3", "3"), ("4", "4"))))
    assert "fewer than 3" in quality.disqualify(q("Sum.", tests=(("1", "1"), ("1", "1"), ("2", "2"))))


def test_no_bank_holds_a_question_that_cannot_be_played_fairly():
    question_db._load(), dataset_generator._load(), smart_generator._load_questions()
    held = [x for bucket in question_db._store.values() for x in bucket] + list(dataset_generator._dataset or []) + list(smart_generator._questions or [])
    assert len(held) > 200, "the banks look empty: nothing was checked"
    assert [x["title"] for x in held if quality.disqualify(x)] == []


def test_the_reviewed_bank_serves_no_test_twice(tmp_path):
    # A reviewed question that stored a test twice: the loader keeps the first of each input, so it is served with three tests.
    record = {
        "title": "Echo The Count", "problem_statement": "Return n.", "input_format": "One line: the integer n.",
        "output_format": "The integer n.", "sample_input": "1", "sample_output": "1",
        "test_cases": [{"input": "1", "output": "1"}, {"input": "2", "output": "2"}, {"input": "2", "output": "2"}, {"input": "3", "output": "3"}],
        "topic": "arrays", "difficulty": "easy", "function_name": "echo", "parameters": [{"name": "n", "type": "int"}],
        "return_type": "int", "starter_code": {lang: "write the logic here" for lang in ("python", "cpp", "java", "javascript")},
    }
    bank = tmp_path / "reviewed_bank.jsonl"
    bank.write_text(json.dumps(record) + "\n", encoding="utf-8")
    try:
        reviewed_bank.reload(str(bank))
        [served] = [x for bucket in reviewed_bank._store.values() for x in bucket]
        assert [c["input"] for c in served["test_cases"]] == ["1", "2", "3"]
        # The real bank is kept out of the repository (it is listed in .git/info/exclude), so CI and a fresh clone have none.
        # Where this checkout has it, every question in it is checked as well.
        if os.path.exists(reviewed_bank._PATH):
            reviewed_bank.reload()
            repeated = [x["title"] for bucket in reviewed_bank._store.values() for x in bucket
                        if len({str(c["input"]) for c in x["test_cases"]}) != len(x["test_cases"])]
            assert repeated == [] and sum(len(b) for b in reviewed_bank._store.values()) >= 100
    finally:
        reviewed_bank.reload()   # leave the module loaded from its own file, as the other tests expect


# ── a collected question keeps its own words about its input ────────────────────────────────────────────────────────────────

CONTEST = ("Mike has n heads over an endless array of tracks.\n\n-----Input-----\n\nThe first line contains n and m, the number of heads and of tracks to read. "
           "The second line contains the initial positions h_i.\n\n-----Output-----\n\nPrint the minimum time.\n\n-----Examples-----\nInput\n3 4\n")


def test_the_sections_of_a_contest_statement_are_found():
    sections = quality.statement_sections(CONTEST)
    assert sections["input"].startswith("The first line contains n and m") and sections["output"] == "Print the minimum time."
    assert quality.statement_sections("A plain statement with no sections.") == {}


def test_the_served_format_says_how_the_values_arrive_and_what_they_mean():
    given, wanted = quality.served_formats(CONTEST, "First line: the integers n, m.\nThen: n integers, the list arr.", "One integer: the answer.")
    assert given.startswith("First line: the integers n, m.\nThen: n integers, the list arr.")
    assert "number of heads and of tracks" in given and "initial positions h_i" in given
    assert wanted.startswith("Print the minimum time.") and wanted.endswith("One integer: the answer.")
    assert quality.served_formats("No sections here.", "First line: n.", "One integer: the answer.") == ("First line: n.", "One integer: the answer.")


def test_without_sections_the_questions_own_formats_are_kept_when_they_are_words():
    given, wanted = quality.served_formats("Find the largest.", "First line: the integer n.\nThen: n integers, the list arr.", "One integer: the answer.",
                                           "First line contains N (1 <= N <= 10^5).\nSecond line contains N integers.", "Print the maximum element.")
    assert "First line contains N (1 <= N <= 10^5)." in given and wanted.startswith("Print the maximum element.")
    placeholder = quality.served_formats("Find.", "First line: n.", "One integer: the answer.", "Read input from standard input as described in the problem.", "3\n1 2 3")
    assert placeholder == ("First line: n.", "One integer: the answer.")


# ── templates: the hidden tests use the layout of the sample ────────────────────────────────────────────────────────────────

def test_tests_are_rewritten_in_the_layout_of_the_sample():
    assert quality.align_tests_with_sample("5\n9 6 12 12 12", ["6 12 5", "4"]) == ["3\n6 12 5", "1\n4"]            # N, then N numbers
    assert quality.align_tests_with_sample("10 38", ["33\n16", "7\n7"]) == ["33 16", "7 7"]                        # A B on one line
    assert quality.align_tests_with_sample("3 2\n8 17 32\n29 49", ["7 14 32\n25 28"]) == ["3 2\n7 14 32\n25 28"]   # N1 N2, then two lists
    # N, the list, Q, then Q queries of two numbers: both counts are put back
    assert quality.align_tests_with_sample("3\n98 9 33\n2\n0 1\n1 2", ["3 4 84 70 2\n1 3\n0 4\n2 2"]) == ["5\n3 4 84 70 2\n3\n1 3\n0 4\n2 2"]
    # "N K" on one line, then N rows, against N and K on a line each
    assert quality.align_tests_with_sample("3 7\n5 37 49\n8 17 32\n29 31 49", ["2\n1\n2 32\n25 28"]) == ["2 1\n2 32\n25 28"]


def test_tests_that_already_follow_the_sample_or_fit_no_rule_are_left_alone():
    assert quality.align_tests_with_sample("5\n9 6 12 12 12", ["3\n6 12 5"]) is None
    assert quality.align_tests_with_sample("6 5\n0 1\n1 2", ["4 2\n0 1\n1 2"]) is None
    assert quality.align_tests_with_sample("3\n98 9 33\n2\n0 1\n1 2", ["3\n4 84 70\n2\n1 3\n0 4"]) is None
    assert quality.align_tests_with_sample("abc", ["abd"]) is None
    assert quality.align_tests_with_sample("5\n9 6 12 12 12", ["6 12 5", "3\n1 2 3"]) is None, "all of a template's tests, or none"
    assert quality.align_tests_with_sample("5\n9 6 12 12 12", []) is None


def all_templates():
    found = {}
    for topic, fns in G.TOPIC_TEMPLATES.items():
        for fn in fns:
            found.setdefault(fn.__name__, (fn, topic))
    for (topic, _), fns in T._get_difficulty_templates().items():
        for fn in fns:
            found.setdefault(fn.__name__, (fn, topic))
    return found


@contextlib.contextmanager
def only_template(fn, topic, seed):
    """generate_dynamic with one template to choose from and its random choices fixed."""
    saved = G._rng, G._seed, G.TOPIC_TEMPLATES[topic], T.get_difficulty_templates
    counter = itertools.count(seed * 1000 + 17)
    G._rng = lambda: random.Random(next(counter))
    G._seed = lambda: next(counter)
    G.TOPIC_TEMPLATES[topic] = [fn]
    T.get_difficulty_templates = lambda a, b: None
    G.clear_title_cache()
    try:
        yield
    finally:
        G._rng, G._seed, G.TOPIC_TEMPLATES[topic], T.get_difficulty_templates = saved
        G.clear_title_cache()


def served(name, seed, difficulty="medium"):
    fn, topic = all_templates()[name]
    with only_template(fn, topic, seed):
        return G.generate_dynamic(topic, difficulty)


def typed(result):
    tests = [(to_stdin(c["input"]), to_stdout(c["output"])) for c in result["test_cases"]]
    return type_question(tests, to_stdin(result["sample_input"]), to_stdout(result["sample_output"]), input_format=str(result.get("input_format") or ""))


RECOVERED = ["_hard_array_range_sum_queries", "_easy_array_sum", "_easy_array_max", "_easy_array_reverse", "_easy_array_count_even_odd", "_easy_math_gcd", "_easy_recursion_power",
             "_easy_sorting_bubble", "_easy_sorting_find_second_max", "_hard_array_count_inversions", "_hard_array_longest_increasing_subarray",
             "_hard_array_max_subarray_with_indices", "_hard_array_trapping_rain_water", "_hard_searching_median_two_arrays",
             "_hard_sorting_largest_number", "_hard_tree_serialize_deserialize"]


@pytest.mark.parametrize("name", RECOVERED)
def test_a_template_whose_sample_and_tests_disagreed_can_now_be_served(name):
    fn, _ = all_templates()[name]
    raw = fn(random.Random(0))
    assert typed(raw) is None, "its own tests still do not follow its sample: that is what generate_dynamic repairs"
    assert all(typed(served(name, seed)) is not None for seed in range(4))


def test_most_templates_can_be_served():
    servable = [name for name in all_templates() if any(typed(served(name, seed)) is not None for seed in range(3))]
    assert len(all_templates()) >= 130 and len(servable) >= 120, f"{len(servable)} of {len(all_templates())}"


def run_starter(code, stdin, solve):
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
    return out.getvalue().split()


def rain(n, heights):
    return sum(max(0, min(max(heights[:i + 1]), max(heights[i:])) - heights[i]) for i in range(len(heights)))


def median(n, m, a, b):
    merged = sorted(a + b)
    size = len(merged)
    return str(merged[size // 2]) if size % 2 else f"{(merged[size // 2 - 1] + merged[size // 2]) / 2:.1f}"


def largest(n, arr):
    order = functools.cmp_to_key(lambda x, y: -1 if x + y > y + x else (1 if x + y < y + x else 0))
    return int("".join(sorted(map(str, arr), key=order)))


SOLUTIONS = {
    "_easy_array_sum": lambda n, arr: sum(arr),
    "_easy_array_reverse": lambda n, arr: arr[::-1],
    "_easy_array_count_even_odd": lambda n, arr: [sum(1 for x in arr if x % 2 == 0), sum(1 for x in arr if x % 2)],
    "_easy_math_gcd": lambda n, m: math.gcd(n, m),
    "_easy_recursion_power": lambda n, m: n ** m,
    "_easy_sorting_find_second_max": lambda n, arr: sorted(set(arr))[-2],
    "_hard_array_count_inversions": lambda n, arr: sum(1 for i in range(len(arr)) for j in range(i + 1, len(arr)) if arr[i] > arr[j]),
    "_hard_array_trapping_rain_water": rain,
    "_hard_searching_median_two_arrays": median,
    "_hard_sorting_largest_number": largest,
    "_hard_array_range_sum_queries": lambda n, arr, m, grid: [sum(arr[left:right + 1]) for left, right in grid],
}


@pytest.mark.parametrize("name", sorted(SOLUTIONS))
def test_a_solution_written_from_the_statement_passes_every_served_test(name):
    """Through the Python starter the service serves: its reader, the call, the printing."""
    for seed in range(3):
        result = served(name, seed, "hard")
        code = typed(result)["starter_code"]["python"]
        for case in result["test_cases"] + [{"input": result["sample_input"], "output": result["sample_output"]}]:
            assert run_starter(code, to_stdin(case["input"]), SOLUTIONS[name]) == to_stdout(case["output"]).split(), to_stdin(case["input"])


# ── template statements and tests ───────────────────────────────────────────────────────────────────────────────────────────

def test_no_statement_ends_in_the_same_advice_for_every_question():
    for name in ("_string_reverse_words", "_graph_dijkstra", "_hard_dp_word_break", "_easy_array_sum"):
        for difficulty in ("easy", "medium", "hard"):
            statement = served(name, 1, difficulty)["problem_statement"]
            assert "segment trees" not in statement and "[Hard]" not in statement and "[Easy]" not in statement and "[Medium]" not in statement


def test_a_statement_with_numbers_says_they_are_the_samples():
    with_numbers = served("_easy_array_sum", 0)
    assert any(ch.isdigit() for ch in with_numbers["problem_statement"].replace(G.SAMPLE_NOTE, ""))
    assert with_numbers["problem_statement"].endswith(G.SAMPLE_NOTE)
    for name, (fn, _) in all_templates().items():
        raw = fn(random.Random(2))["problem_statement"]
        if not any(ch.isdigit() for ch in raw):
            assert not served(name, 2)["problem_statement"].endswith(G.SAMPLE_NOTE), name
            break


def test_no_template_question_repeats_a_test():
    for name in ("_easy_math_factorial", "_easy_math_fibonacci", "_easy_recursion_sum_natural", "_easy_math_prime_check"):
        for seed in range(6):
            inputs = [str(c["input"]) for c in served(name, seed, "hard")["test_cases"]]
            assert len(inputs) == len(set(inputs)) and len(inputs) >= 3, name


# ── the order in which the sources are asked ────────────────────────────────────────────────────────────────────────────────

def test_has_topic_knows_the_template_topics_and_their_aliases():
    assert G.has_topic("arrays") and G.has_topic("Graphs") and G.has_topic("dp") and G.has_topic("linked lists")
    assert not G.has_topic("file handling") and not G.has_topic("") and not G.has_topic("pointers")


@pytest.fixture(scope="module")
def play():
    from fastapi.testclient import TestClient
    import main_dynamic

    client = TestClient(main_dynamic.app)

    def kind_of(body):
        """Where the service says the question came from (the reviewed bank answers through the pool, which calls it 'reviewed')."""
        source = body.get("source", "")
        return "reviewed" if source in ("reviewed", "dynamic-reviewed") else "template" if source == "dynamic-templates" else "collected"

    def kinds(topic, difficulty, limit=60):
        seen, out = [], []
        for _ in range(limit):
            answer = client.post("/generate", json={"topic": topic, "difficulty": difficulty, "exclude_titles": seen})
            if answer.status_code != 200:
                break
            body = answer.json()
            out.append((kind_of(body), body))
            seen += [body["title"], body["base_title"]]
        return out

    return kinds


def sometimes_unservable():
    """Base titles of the templates the service cannot type on some seeds (it skips such a question, so the template can turn up again later)."""
    flaky = set()
    for name in all_templates():
        results = [served(name, seed) for seed in range(6)]
        if any(typed(r) is None for r in results):
            flaky.add(results[0]["base_title"])
    return flaky


@pytest.mark.parametrize("topic, difficulty", [("arrays", "hard"), ("strings", "medium"), ("graphs", "hard"), ("sorting", "hard"), ("math", "easy")])
def test_reviewed_questions_come_first_then_templates_then_collected_ones(play, topic, difficulty):
    served_in_order = play(topic, difficulty)
    order = [kind for kind, _ in served_in_order]
    assert "template" in order and "collected" in order, order
    reviewed = [i for i, kind in enumerate(order) if kind == "reviewed"]
    assert reviewed == list(range(len(reviewed))), f"a reviewed question came after another kind: {order}"
    first_collected = order.index("collected")
    late = {body["base_title"] for kind, body in served_in_order[first_collected:] if kind != "collected"}
    assert late <= sometimes_unservable(), f"templates that are always servable came after a collected question: {late}"


def test_every_served_question_says_where_it_came_from(play):
    assert {body["source"] for _, body in play("arrays", "easy", limit=30)} <= {"reviewed", "dynamic-reviewed", "dynamic-templates",
                                                                                 "dynamic-question_db", "dynamic-smart", "dynamic-dataset"}


def test_a_hard_question_is_a_checked_one_before_it_is_a_collected_one(play):
    """There are no reviewed hard questions yet, and hard used to start with a collected contest problem."""
    assert play("arrays", "hard", limit=1)[0][0] == "template"


def test_a_collected_question_is_served_with_its_own_description_of_the_input(play):
    collected = [body for kind, body in play("strings", "hard") if kind == "collected"]
    assert len(collected) >= 10
    for body in collected:
        assert "What the values mean, in the problem's own words:" in body["input_format"], body["title"]
        section = quality.statement_sections(body["problem_statement"]).get("input")
        if section:
            assert section[:40] in body["input_format"]
        assert quality.disqualify(body) is None
