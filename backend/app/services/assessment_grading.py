"""The rules of the Skill Assessment, applied on the server.

The browser used to run the tests, decide pass or fail, count the points and pick the next difficulty, and the server took
its word for all of it. Now the server keeps each question (with its hidden tests) in `assessment_items`, starts the clock
when it hands the question out, runs the player's code on every test itself and scores it with the rules below. The rules
are the ones the page used, so a player sees the same numbers as before.

  * 5 questions, one per slot. Points per slot: 200, 200, 300, 400, 500.
  * All tests pass: full points. Some pass: 70% of the points times the share passed. None pass: 0.
  * Time limit: easy 5 min, medium 7 min, hard 10 min. The page submits by itself when its timer runs out; that answer still
    scores points but gets no speed bonus. An answer arriving more than LATE_CUTOFF_SECONDS after the limit scores nothing,
    and a question left open that long is closed as unanswered.
  * Next difficulty: solved moves up (easy -> medium -> hard), nothing passed moves down (hard -> medium -> easy),
    partly solved stays.
  * The questions are answered in order and cannot be re-rolled: asking for a question while one is open gives the open
    one back with the time it has left.
"""

from __future__ import annotations

import json
from typing import Any

TOTAL_QUESTIONS = 5
SAMPLE_TESTS = 2   # the tests the player sees (examples and Run); the rest stay on the server

TIME_LIMITS = {"easy": 300, "medium": 420, "hard": 600}
LATE_CUTOFF_SECONDS = 60
TIMED_OUT_SECONDS = 9999   # what the rating formula is given for an answer sent by the timer (no speed bonus)

_UP = {"easy": "medium", "medium": "hard", "hard": "hard"}
_DOWN = {"easy": "easy", "medium": "easy", "hard": "medium"}


def max_points(slot: int) -> int:
    return {4: 500, 3: 400, 2: 300}.get(slot, 200)


def time_limit(difficulty: str) -> int:
    return TIME_LIMITS.get(difficulty, TIME_LIMITS["easy"])


def points_for(slot: int, passed_tests: int, total_tests: int) -> int:
    top = max_points(slot)
    if total_tests <= 0 or passed_tests <= 0:
        return 0
    if passed_tests >= total_tests:
        return top
    # the page used JavaScript's Math.round, which rounds halves up
    return int(top * (passed_tests / total_tests) * 0.7 + 0.5)


def next_difficulty(difficulty: str, passed_tests: int, total_tests: int) -> str:
    if total_tests > 0 and passed_tests >= total_tests:
        return _UP.get(difficulty, difficulty)
    if passed_tests <= 0:
        return _DOWN.get(difficulty, difficulty)
    return difficulty


def grade(
    slot: int,
    passed_tests: int,
    total_tests: int,
    elapsed_seconds: float,
    limit_seconds: int,
    timed_out: bool = False,
) -> dict:
    """Score one answer. `timed_out` is the page saying its timer sent the answer; the server's own clock decides too."""
    over = elapsed_seconds > limit_seconds
    late = elapsed_seconds > limit_seconds + LATE_CUTOFF_SECONDS
    timed_out = bool(timed_out or over)
    solved = total_tests > 0 and passed_tests >= total_tests and not late
    points = 0 if late else points_for(slot, passed_tests, total_tests)
    return {
        "solved": solved,
        "partial": (not solved) and passed_tests > 0,
        "points_earned": points,
        "max_points": max_points(slot),
        "time_taken_seconds": int(round(elapsed_seconds)),
        "timed_out": timed_out,
        "late": late,
    }


def expired(issued_at: float, limit_seconds: int, now: float) -> bool:
    """An open question nobody answered in time: it is closed as unanswered."""
    return now - issued_at > limit_seconds + LATE_CUTOFF_SECONDS


def parse_tests(raw: Any) -> list[dict]:
    try:
        tests = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return []
    return [t for t in tests if isinstance(t, dict)] if isinstance(tests, list) else []


def test_input(test: dict) -> str:
    return str(test.get("input", test.get("stdin", "")))


def test_output(test: dict) -> str:
    return str(test.get("output", test.get("expected_output", "")))


def public_question(question: dict) -> dict:
    """What the player gets: the question with only the sample tests, plus how many tests it is graded on."""
    tests = parse_tests(question.get("test_cases"))
    shown = {k: v for k, v in question.items() if k != "test_cases"}
    shown["test_cases"] = json.dumps(tests[:SAMPLE_TESTS])
    shown["tests_count"] = len(tests)
    return shown


def rating_input(item: Any) -> dict:
    """One graded item in the shape `elo_service.calculate_initial_rating` reads."""
    return {
        "difficulty": item.difficulty,
        "solved": bool(item.solved),
        "time_taken_seconds": TIMED_OUT_SECONDS if item.timed_out else int(item.time_taken_seconds or TIMED_OUT_SECONDS),
        "points_earned": int(item.points_earned or 0),
        "topic": item.skill,
        "passed_tests": int(item.passed_tests or 0),
        "total_tests": int(item.total_tests or 0),
    }


def result_view(item: Any) -> dict:
    """A graded item as the page shows it (progress dots, the result screen)."""
    passed = int(item.passed_tests or 0)
    return {
        "slot": item.slot,
        "title": item.title,
        "difficulty": item.difficulty,
        "skill_dimension": item.skill,
        "passed": bool(item.solved),
        "partial": (not item.solved) and passed > 0,
        "passed_tests": passed,
        "total_tests": int(item.total_tests or 0),
        "points_earned": int(item.points_earned or 0),
        "max_points": max_points(item.slot),
        "time_taken_seconds": None if item.timed_out else item.time_taken_seconds,
        "timed_out": bool(item.timed_out),
    }


def topic_scores(items: list) -> dict[str, int]:
    """Average share of tests passed per skill, 0-100 (the radar chart on the result screen)."""
    scores: dict[str, list[int]] = {}
    for item in items:
        total = int(item.total_tests or 0) or 1
        scores.setdefault(item.skill or "general", []).append(int((int(item.passed_tests or 0) / total) * 100))
    return {skill: int(sum(v) / len(v)) for skill, v in scores.items()}


def remaining_seconds(issued_at: float, limit_seconds: int, now: float) -> int:
    return max(0, int(limit_seconds - (now - issued_at)))
