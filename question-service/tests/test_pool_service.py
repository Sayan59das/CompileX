"""Checks for the serving logic: who gets which question, the fallback chain, hidden tests and grading."""

import json
import os
import subprocess
import sys
import time

import pytest

from pool.history import MemorySeenStore
from pool.repository import SqlRepository
from pool.service import (NoQuestion, QuestionService, ReviewedBank, backend_view, bank_id, legacy_id, normalise_output, public_view,
                          topic_candidates)
from tests.pool_helpers import Counter, FakeBank, add_live, add_pending, make_question

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bank_questions(count, topic="arrays", difficulty="easy", start=100):
    return [make_question(start + i, topic, difficulty, title=f"Bank {start + i}") | {"problem_statement": f"Bank statement {start + i}"} for i in range(count)]


def make_service(live=0, bank=0, legacy=None, topic="arrays", difficulty="easy"):
    repo = SqlRepository.sqlite(":memory:")
    ids = [add_live(repo, n, topic, difficulty) for n in range(1, live + 1)]
    fake = FakeBank({(topic, difficulty): bank_questions(bank, topic, difficulty)} if bank else {})
    service = QuestionService(repo, MemorySeenStore(clock=Counter()), ReviewedBank(fake), legacy=legacy)
    return service, ids


def draw(service, count, players=("p1",), topic="arrays", difficulty="easy"):
    return [service.pick(topic, difficulty, list(players)) for _ in range(count)]


# ── who gets what ────────────────────────────────────────────────────────

def test_a_player_never_gets_the_same_pool_question_twice_until_the_pool_is_used_up():
    service, ids = make_service(live=6)
    picked = draw(service, 6)
    assert {q["id"] for q, _ in picked} == {str(i) for i in ids} and all(repeat is False for _, repeat in picked)
    assert all(q["source"] == "pool" for q, _ in picked)


def test_when_the_pool_is_used_up_the_reviewed_bank_is_next_then_the_oldest_question_is_repeated():
    service, ids = make_service(live=2, bank=3)
    picked = draw(service, 5)
    assert [q["source"] for q, _ in picked] == ["pool", "pool", "reviewed", "reviewed", "reviewed"]
    assert len({q["id"] for q, _ in picked}) == 5 and not any(repeat for _, repeat in picked)
    again, repeat = service.pick("arrays", "easy", ["p1"])
    assert repeat is True and again["id"] == picked[0][0]["id"]                      # the one served longest ago
    follow, repeat = service.pick("arrays", "easy", ["p1"])
    assert repeat is True and follow["id"] == picked[1][0]["id"]


def test_players_do_not_share_history():
    service, _ = make_service(live=3)
    first = {q["id"] for q, _ in draw(service, 3, ["alice"])}
    second = {q["id"] for q, _ in draw(service, 3, ["bob"])}
    assert first == second and len(first) == 3 and not any(r for _, r in draw(service, 3, ["carol"]))


def test_a_lobby_gets_a_question_none_of_its_players_has_seen_and_all_of_them_are_marked():
    service, ids = make_service(live=4)
    a, _ = service.pick("arrays", "easy", ["a"])
    b, _ = service.pick("arrays", "easy", ["b"])
    lobby, repeat = service.pick("arrays", "easy", ["a", "b"])
    assert lobby["id"] not in {a["id"], b["id"]} and repeat is False
    assert service.seen.seen(["a"], "arrays", "easy") >= {a["id"], lobby["id"]}
    assert service.seen.seen(["b"], "arrays", "easy") >= {b["id"], lobby["id"]}


def test_the_repeat_is_the_question_the_lobby_got_longest_ago():
    service, _ = make_service(live=2)
    first, _ = service.pick("arrays", "easy", ["a"])
    second, _ = service.pick("arrays", "easy", ["a"])
    assert first["id"] != second["id"]
    service.seen.mark(["b"], "arrays", "easy", first["id"])        # b was given `first` after a was given `second`
    question, repeat = service.pick("arrays", "easy", ["a", "b"])
    assert repeat is True and question["id"] == second["id"]


def test_the_spelling_of_a_topic_does_not_split_the_history():
    service, _ = make_service(live=3)
    ids = {service.pick(spelling, "easy", ["p1"])[0]["id"] for spelling in ("arrays", "Array", " ARRAYS ")}
    assert len(ids) == 3


def test_difficulties_are_separate_pools():
    service, _ = make_service(live=2)
    add_live(service.repo, 50, difficulty="hard")
    question, _ = service.pick("arrays", "hard", ["p1"])
    assert question["difficulty"] == "hard"
    with pytest.raises(NoQuestion):
        service.pick("arrays", "medium", ["p1"])


def test_questions_that_are_not_live_are_never_served():
    service, _ = make_service(live=1)
    pending = add_pending(service.repo, 90)
    approved = add_pending(service.repo, 91)
    service.repo.approve(approved, "r")
    retired = add_live(service.repo, 92)
    service.repo.retire(retired)
    served = {q["id"] for q, _ in draw(service, 4)}
    assert str(pending) not in served and str(approved) not in served and str(retired) not in served


def test_a_topic_with_nothing_at_all_has_no_question():
    service, _ = make_service()
    with pytest.raises(NoQuestion, match="no easy question exists for arrays"):
        service.pick("arrays", "easy", ["p1"])


# ── the older chain ──────────────────────────────────────────────────────

def legacy_question(title):
    return {"title": title, "problem_statement": "Old statement.", "input_format": "n", "output_format": "x", "sample_input": "1", "sample_output": "2",
            "test_cases": [{"input": "1", "output": "2"}], "topic": "trees", "difficulty": "easy", "source": "dynamic"}


def test_the_legacy_generators_serve_a_topic_the_pool_and_the_bank_know_nothing_about():
    calls = []

    def legacy(topic, difficulty, blocked):
        calls.append((topic, difficulty, set(blocked)))
        return legacy_question("Old tree question")

    service, _ = make_service(legacy=legacy)
    question, repeat = service.pick("trees", "easy", ["p1"])
    assert question["title"] == "Old tree question" and question["id"] == legacy_id(question) and repeat is False
    assert calls == [("trees", "easy", set())]
    assert service.seen.seen(["p1"], "trees", "easy") == {question["id"]}


def test_the_legacy_generators_are_not_used_when_the_pool_or_the_bank_has_questions():
    def legacy(*args):
        raise AssertionError("legacy must not be called")

    service, _ = make_service(live=1, legacy=legacy)
    service.pick("arrays", "easy", ["p1"])
    question, repeat = service.pick("arrays", "easy", ["p1"])               # everything seen: a repeat, not a legacy question
    assert repeat is True
    service2, _ = make_service(bank=1, legacy=legacy)
    service2.pick("arrays", "easy", ["p1"])
    assert service2.pick("arrays", "easy", ["p1"])[1] is True


def test_when_the_legacy_generators_have_nothing_there_is_no_question():
    service, _ = make_service(legacy=lambda *args: None)
    with pytest.raises(NoQuestion):
        service.pick("trees", "easy", ["p1"])


# ── the backend's /generate flavour ──────────────────────────────────────

def test_generate_excludes_by_title_and_never_repeats():
    service, ids = make_service(live=3)
    titles = [service.repo.get(i)["title"] for i in ids]
    result = service.generate("arrays", "easy", [], exclude_titles=titles[:2])
    assert result["title"] == titles[2] and "test_cases" in result and result["source"] == "pool"
    with pytest.raises(NoQuestion):
        service.generate("arrays", "easy", [], exclude_titles=titles)
    with pytest.raises(NoQuestion):
        service.generate("arrays", "easy", [], exclude_titles=[" " + titles[0].upper()] + titles[1:])


def test_generate_without_players_leaves_no_history_and_with_players_it_does():
    service, _ = make_service(live=2)
    service.generate("arrays", "easy", [])
    assert service.seen.seen(["anyone"], "arrays", "easy") == set() and service.seen._data == {}
    first = service.generate("arrays", "easy", ["p1"])
    second = service.generate("arrays", "easy", ["p1"])
    assert first["title"] != second["title"]
    with pytest.raises(NoQuestion):
        service.generate("arrays", "easy", ["p1"])


def test_generate_also_excludes_bank_questions_by_title():
    service, _ = make_service(bank=2)
    first = service.generate("arrays", "easy", [])
    other = service.generate("arrays", "easy", [], exclude_titles=[first["title"]])
    assert other["title"] != first["title"]
    with pytest.raises(NoQuestion):
        service.generate("arrays", "easy", [], exclude_titles=["Bank 100", "Bank 101"])


# ── what leaves the service ──────────────────────────────────────────────

def test_a_player_gets_the_sample_and_never_the_hidden_tests():
    service, _ = make_service(live=1)
    shown = service.get_question("arrays", "easy", ["p1"])
    text = json.dumps(shown)
    assert "HIDDEN" not in text and "test_cases" not in shown
    assert shown["sample_tests"] == [{"input": "1\n2", "output": "SAMPLE-1"}] and shown["tests_count"] == 5 and shown["repeat"] is False
    assert shown["starter_code"]["python"] and shown["function_name"] == "solve_1" and shown["id"].isdigit()


def test_the_backend_flavour_carries_every_test_case_in_the_old_shape():
    service, _ = make_service(live=1)
    shown = service.generate("arrays", "easy", [])
    assert [c["output"] for c in shown["test_cases"]] == [f"HIDDEN-1-{i}" for i in range(5)]
    for key in ("title", "base_title", "problem_statement", "input_format", "output_format", "sample_input", "sample_output",
                "topic", "difficulty", "source", "function_name", "parameters", "return_type", "starter_code"):
        assert key in shown, key


def test_views_work_for_a_reviewed_question_too():
    bank = ReviewedBank(FakeBank({("arrays", "easy"): bank_questions(1)}))
    question = bank.questions("arrays", "easy")[0]
    assert question["id"] == bank_id(question) and question["id"].startswith("rb:") and question["source"] == "reviewed"
    assert "HIDDEN" not in json.dumps(public_view(question)) and "test_cases" in backend_view(question)


# ── grading ──────────────────────────────────────────────────────────────

def test_grading_compares_with_the_hidden_outputs_and_reveals_none_of_them():
    service, ids = make_service(live=1)
    qid = str(ids[0])
    good = [f"HIDDEN-1-{i}" for i in range(5)]
    assert service.grade(qid, good) == {"question_id": qid, "total": 5, "passed": 5, "failed": [], "all_passed": True}
    wrong = list(good)
    wrong[1], wrong[3] = "nope", "HIDDEN-1-3 extra"
    result = service.grade(qid, wrong)
    assert result["passed"] == 3 and result["failed"] == [1, 3] and result["all_passed"] is False and "HIDDEN" not in json.dumps(result)


def test_grading_ignores_trailing_spaces_and_blank_ends_but_not_content():
    service, ids = make_service(live=1)
    qid = str(ids[0])
    padded = [f"  HIDDEN-1-{i}  \n\n" for i in range(5)]
    assert service.grade(qid, padded)["all_passed"] is True
    assert normalise_output("a  \nb \n\n") == "a\nb"


def test_grading_refuses_a_wrong_number_of_results_and_unknown_or_unpublished_questions():
    service, ids = make_service(live=1, bank=1)
    with pytest.raises(ValueError, match="expected 5 results, got 2"):
        service.grade(str(ids[0]), ["a", "b"])
    with pytest.raises(NoQuestion):
        service.grade("987654", ["a"] * 5)
    with pytest.raises(NoQuestion):
        service.grade("nonsense", ["a"] * 5)
    hidden = add_pending(service.repo, 70)
    with pytest.raises(NoQuestion):
        service.grade(str(hidden), ["a"] * 5)
    bank_one = service.bank.questions("arrays", "easy")[0]
    assert service.grade(bank_one["id"], [c["output"] for c in bank_one["test_cases"]])["all_passed"] is True


def test_the_hidden_tests_are_available_to_the_backend_only_through_tests():
    service, ids = make_service(live=1)
    assert service.tests(str(ids[0]))[0] == {"input": "0\n0", "output": "HIDDEN-1-0"} and service.tests("123456") is None


# ── status ───────────────────────────────────────────────────────────────

def test_the_status_is_counted_from_the_database_and_the_bank():
    service, ids = make_service(live=2, bank=3)
    pending = add_pending(service.repo, 80)
    approved = add_pending(service.repo, 81)
    service.repo.approve(approved, "r")
    add_live(service.repo, 82, difficulty="hard")
    status = service.status()
    rows = {(p["topic"], p["difficulty"]): p for p in status["pools"]}
    assert rows[("arrays", "easy")] == {"topic": "arrays", "difficulty": "easy", "bank": 3, "pending": 1, "approved": 1, "live": 2, "retired": 0}
    assert rows[("arrays", "hard")]["live"] == 1 and rows[("arrays", "hard")]["bank"] == 0
    assert status["live"] == 3 and status["bank"] == 3
    service.repo.retire(ids[0])
    assert {(p["topic"], p["difficulty"]): p for p in service.status()["pools"]}[("arrays", "easy")]["live"] == 1


def test_topic_spellings_are_tried_exactly_then_with_and_without_an_s():
    assert topic_candidates("Array") == ["array", "arrays"]
    assert topic_candidates(" Dynamic_Programming ") == ["dynamic programming", "dynamic programmings"]
    assert topic_candidates("graphs") == ["graphs", "graph"]
    assert topic_candidates("s") == ["s", "ss"]


# ── the serving path stays free of models and generators ─────────────────

FORBIDDEN = ("torch", "transformers", "verify", "spec", "builder", "generate", "novelty", "writer", "pipeline", "worker", "prim_runtime", "primitives")


def test_importing_the_serving_code_loads_no_model_verifier_or_generator():
    code = (
        "import sys, pool.service, pool.api, pool.history, pool.repository\n"
        f"bad = [m for m in {FORBIDDEN!r} if m in sys.modules]\n"
        "assert not bad, bad\n"
        "print('clean')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=SERVICE_DIR, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and "clean" in result.stdout, result.stderr


def test_serving_works_even_when_every_model_verifier_and_generator_would_raise(monkeypatch):
    class Poison:
        def __getattr__(self, name):
            raise AssertionError(f"the serving path touched {name}")

    for name in FORBIDDEN:
        monkeypatch.setitem(sys.modules, name, Poison())
    service, ids = make_service(live=2, bank=2)
    for _ in range(4):
        service.get_question("arrays", "easy", ["p1"])
    service.generate("arrays", "easy", [], exclude_titles=["Question 1"])
    service.grade(str(ids[0]), ["x"] * 5)
    service.status()


# ── speed ────────────────────────────────────────────────────────────────

def test_a_pick_from_a_full_warm_pool_is_fast_even_for_a_player_with_a_long_history():
    service, ids = make_service(live=200)
    service.seen.mark(["veteran"], "arrays", "easy", "x")
    for question_id in ids[:150]:
        service.seen.mark(["veteran"], "arrays", "easy", str(question_id))
    times = []
    for i in range(120):
        player = "veteran" if i % 2 else f"fresh{i}"
        started = time.perf_counter()
        service.get_question("arrays", "easy", [player])
        times.append(time.perf_counter() - started)
    times.sort()
    assert times[int(len(times) * 0.95)] < 0.05            # the target: 95th percentile under 50 ms (in process, warm)


def test_a_player_who_has_seen_most_of_the_pool_still_always_gets_an_unseen_question_if_one_exists():
    service, ids = make_service(live=200)
    for i in range(25):
        player = f"veteran{i}"
        for question_id in ids[:-1]:
            service.seen.mark([player], "arrays", "easy", str(question_id))
        question, repeat = service.pick("arrays", "easy", [player])
        assert question["id"] == str(ids[-1]) and repeat is False
