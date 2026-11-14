"""The Skill Assessment is graded on the server: the browser no longer decides pass/fail, points, time or difficulty.

The rules are tested as plain functions; the routes are called directly on a throwaway SQLite database with the question
generator and the code runner faked, so no Docker, question service or browser is needed.

Run from the backend folder:  python -m pytest tests/test_assessment_grading.py -q
"""

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1 import routes
from app.db.database import Base, build_engine
from app.models.models import AssessmentItem, DifficultyLevel, User
from app.services import assessment_grading as g
from app.services.code_executor import ExecutionResult, SubmissionResult
from app.services.elo_service import calculate_initial_rating

MARK = "You do not need to edit below"
STARTER = (
    "import sys\n\n\ndef solve(n, arr):\n    # Write your logic here\n    pass\n\n\n"
    f"# ===== Reads the input and prints the answer. {MARK}. =====\n"
    "def main():\n    n = int(input())\n    arr = list(map(int, input().split()))\n    print(solve(n, arr))\n\n\n"
    "if __name__ == '__main__':\n    main()\n"
)
HARNESS = STARTER[STARTER.index("# =====") :]


def answer(passing: int) -> str:
    """Player code that the fake runner treats as passing the first `passing` tests."""
    return STARTER.replace("    pass\n", f"    return 0  # PASS:{passing}\n")


# ── the rules ───────────────────────────────────────────────────────────────


def test_points_follow_the_page_rules_including_its_rounding():
    assert [g.max_points(s) for s in range(5)] == [200, 200, 300, 400, 500]
    assert g.points_for(0, 5, 5) == 200
    assert g.points_for(4, 3, 5) == 210          # 500 * 3/5 * 0.7
    assert g.points_for(2, 1, 4) == 53           # 52.5 rounds up, as JavaScript's Math.round did
    assert g.points_for(3, 0, 5) == 0
    assert g.points_for(3, 0, 0) == 0


def test_difficulty_moves_up_on_a_solve_down_on_nothing_and_stays_on_partial():
    assert g.next_difficulty("easy", 5, 5) == "medium"
    assert g.next_difficulty("medium", 5, 5) == "hard"
    assert g.next_difficulty("hard", 5, 5) == "hard"
    assert g.next_difficulty("hard", 0, 5) == "medium"
    assert g.next_difficulty("medium", 0, 5) == "easy"
    assert g.next_difficulty("easy", 0, 5) == "easy"
    assert g.next_difficulty("medium", 2, 5) == "medium"


def test_the_server_clock_decides_timeouts_and_late_answers_score_nothing():
    on_time = g.grade(0, 5, 5, elapsed_seconds=40, limit_seconds=300)
    assert on_time["solved"] and on_time["points_earned"] == 200 and not on_time["timed_out"]
    assert on_time["time_taken_seconds"] == 40

    by_timer = g.grade(0, 5, 5, elapsed_seconds=304, limit_seconds=300)   # the page submits a few seconds after 0:00
    assert by_timer["solved"] and by_timer["points_earned"] == 200 and by_timer["timed_out"] and not by_timer["late"]

    late = g.grade(0, 5, 5, elapsed_seconds=300 + g.LATE_CUTOFF_SECONDS + 1, limit_seconds=300)
    assert late["late"] and not late["solved"] and late["points_earned"] == 0

    flagged = g.grade(0, 5, 5, elapsed_seconds=100, limit_seconds=300, timed_out=True)
    assert flagged["timed_out"]


def test_the_player_only_gets_the_sample_tests():
    tests = [{"input": str(i), "output": str(i * 2)} for i in range(5)]
    shown = g.public_question({"title": "T", "test_cases": json.dumps(tests)})
    assert json.loads(shown["test_cases"]) == tests[:2]
    assert shown["tests_count"] == 5


# ── the routes ──────────────────────────────────────────────────────────────


class Fakes:
    """Stands in for the question generator and the Docker runner, and records what they were asked."""

    def __init__(self):
        self.generated: list[DifficultyLevel] = []
        self.runs: list[dict] = []

    async def generate_question(self, difficulty, topic=None, num_test_cases=None, description=None, exclude_titles=None, player_ids=None):
        self.generated.append(difficulty)
        n = len(self.generated)
        tests = [{"input": f"1\n{i}", "output": str(i)} for i in range(5)]
        return {
            "title": f"Question {n}",
            "base_title": f"Question {n}",
            "description": "Return the number.",
            "difficulty": difficulty,
            "topic": topic,
            "test_cases": json.dumps(tests),
            "starter_code": json.dumps({"python": STARTER}),
            "function_name": "solve",
            "parameters": json.dumps([{"name": "n", "type": "int"}, {"name": "arr", "type": "List[int]"}]),
            "return_type": "int",
            "return_description": "The number",
            "diagram": None,
        }

    async def execute_code(self, code, language, test_cases, time_limit_ms=2000, function_signature=None):
        self.runs.append({"code": code, "tests": len(test_cases)})
        m = re.search(r"PASS:(\d+)", code)
        passing = int(m.group(1)) if m else 0
        results = [
            ExecutionResult(success=True, passed=i < passing, output=tc.expected_output if i < passing else "wrong")
            for i, tc in enumerate(test_cases)
        ]
        return SubmissionResult(len(test_cases), min(passing, len(test_cases)), 1.0, results)


@pytest.fixture
def fakes(monkeypatch):
    f = Fakes()
    monkeypatch.setattr(routes.ai_generator, "generate_question", f.generate_question)
    monkeypatch.setattr(routes.code_executor, "execute_code", f.execute_code)
    async def allowed(*a, **k):
        return True, ""

    monkeypatch.setattr(routes, "_check_rate_limit", allowed)
    return f


def run_with_db(tmp_path, scenario):
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add_all([User(username="alice", rating=1000), User(username="bob", rating=1000)])
            await db.commit()
            alice = (await db.execute(select(User).where(User.username == "alice"))).scalar_one()
            bob = (await db.execute(select(User).where(User.username == "bob"))).scalar_one()
            await scenario(db, alice, bob)
        await engine.dispose()

    asyncio.run(main())


async def issue(db, user, **body):
    return await routes.generate_assessment_question(body, db=db, current_user=user)


async def submit(db, user, item_id, code, timed_out=False, language="python"):
    req = routes.AssessmentAnswerRequest(item_id=item_id, code=code, language=language, timed_out=timed_out)
    return await routes.submit_assessment_question(req, db=db, current_user=user)


async def finish(db, user, **body):
    return await routes.submit_skill_assessment(routes.SkillAssessmentRequest(**body), db=db, current_user=user)


def test_a_whole_assessment_is_graded_and_rated_by_the_server(tmp_path, fakes):
    async def scenario(db, alice, bob):
        plan = [5, 2, 0, 5, 3]   # tests passed per question, out of 5
        seen_results = []
        for slot, passing in enumerate(plan):
            q = await issue(db, alice, slot=0, difficulty_override="hard")   # the page's slot/difficulty are ignored
            assert q["slot"] == slot
            assert len(json.loads(q["test_cases"])) == 2 and q["tests_count"] == 5
            assert len(q["previous_results"]) == slot
            r = await submit(db, alice, q["item_id"], answer(passing))
            assert r["passed_tests"] == passing and r["total_tests"] == 5
            assert r["points_earned"] == g.points_for(slot, passing, 5)
            assert len(r["tests"]) == 5
            seen_results.append(r)

        # easy solved -> medium; 2/5 stays medium; 0/5 -> easy; solved -> medium
        assert [d.value for d in fakes.generated] == ["easy", "medium", "medium", "easy", "medium"]
        assert seen_results[-1]["finished"] and seen_results[-1]["next_difficulty"] is None

        items = (await db.execute(select(AssessmentItem))).scalars().all()
        expected = calculate_initial_rating([g.rating_input(i) for i in items])

        claimed = [{"difficulty": "hard", "solved": True, "time_taken_seconds": 5, "points_earned": 500}] * 5
        done = await finish(db, alice, results=claimed)   # what the page claims is ignored
        assert done["rating"] == expected and done["already_completed"] is False
        assert [r["passed_tests"] for r in done["results"]] == plan
        assert alice.skill_quiz_completed and alice.rating == expected
        assert (await db.execute(select(AssessmentItem))).scalars().all() == []

        again = await finish(db, alice)
        assert again["already_completed"] is True
        with pytest.raises(HTTPException) as e:
            await issue(db, alice)
        assert e.value.status_code == 409

    run_with_db(tmp_path, scenario)


def test_asking_again_returns_the_open_question_so_it_cannot_be_rerolled(tmp_path, fakes):
    async def scenario(db, alice, bob):
        first = await issue(db, alice)
        again = await issue(db, alice, slot=0)
        assert again["item_id"] == first["item_id"] and again["title"] == first["title"]
        assert len(fakes.generated) == 1
        assert 0 < again["time_remaining_seconds"] <= again["time_limit_seconds"] == 300

    run_with_db(tmp_path, scenario)


def test_a_question_is_graded_once_and_only_by_its_owner(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        with pytest.raises(HTTPException) as e:
            await submit(db, bob, q["item_id"], answer(5))
        assert e.value.status_code == 404

        await submit(db, alice, q["item_id"], answer(1))
        with pytest.raises(HTTPException) as e:
            await submit(db, alice, q["item_id"], answer(5))
        assert e.value.status_code == 409

    run_with_db(tmp_path, scenario)


def test_the_harness_runs_from_the_server_copy(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        tampered = answer(0).replace("print(solve(n, arr))", "print('PASS:5')")
        r = await submit(db, alice, q["item_id"], tampered)
        assert r["passed_tests"] == 0
        assert fakes.runs[-1]["code"].endswith(HARNESS)

    run_with_db(tmp_path, scenario)


def test_a_removed_harness_is_refused_unless_the_timer_sent_it(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        no_harness = "def solve(n, arr):\n    # Write your logic here\n    return 0  # PASS:5\n"
        with pytest.raises(HTTPException) as e:
            await submit(db, alice, q["item_id"], no_harness)
        assert e.value.status_code == 400

        r = await submit(db, alice, q["item_id"], no_harness, timed_out=True)
        assert r["passed_tests"] == 0 and r["points_earned"] == 0 and r["timed_out"]

    run_with_db(tmp_path, scenario)


def test_late_answers_score_nothing_and_abandoned_questions_are_closed(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        item = await db.get(AssessmentItem, q["item_id"])
        item.issued_at -= item.time_limit_seconds + g.LATE_CUTOFF_SECONDS + 5
        await db.commit()
        runs_before = len(fakes.runs)
        r = await submit(db, alice, q["item_id"], answer(5))
        assert r["late"] and r["points_earned"] == 0 and not r["passed"]
        assert len(fakes.runs) == runs_before   # not even run

        q2 = await issue(db, alice)
        item2 = await db.get(AssessmentItem, q2["item_id"])
        item2.issued_at -= item2.time_limit_seconds + g.LATE_CUTOFF_SECONDS + 5
        await db.commit()
        q3 = await issue(db, alice)   # the abandoned question 2 is closed as unanswered, question 3 is issued
        assert q3["slot"] == 2
        closed = q3["previous_results"][1]
        assert closed["passed_tests"] == 0 and closed["timed_out"] and closed["total_tests"] == 5

    run_with_db(tmp_path, scenario)


def test_a_rolled_back_history_write_does_not_break_the_next_question(tmp_path, fakes, monkeypatch):
    async def rolled_back(db, *args, **kwargs):   # what record_seen does when another request saved the same title first
        await db.rollback()

    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        await submit(db, alice, q["item_id"], answer(5))
        monkeypatch.setattr(routes.question_history, "record_seen", rolled_back)
        q2 = await issue(db, alice)
        assert q2["slot"] == 1 and q2["previous_results"][0]["passed"] is True

    run_with_db(tmp_path, scenario)


def test_run_uses_only_the_sample_tests_and_grades_nothing(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        req = routes.AssessmentRunRequest(item_id=q["item_id"], code=answer(5), language="python")
        out = await routes.run_assessment_samples(req, db=db, current_user=alice)
        assert out["total_tests"] == 2 and out["passed_tests"] == 2
        assert fakes.runs[-1]["tests"] == 2
        assert (await db.get(AssessmentItem, q["item_id"])).graded_at is None

        await submit(db, alice, q["item_id"], answer(5))
        with pytest.raises(HTTPException) as e:
            await routes.run_assessment_samples(req, db=db, current_user=alice)
        assert e.value.status_code == 409

    run_with_db(tmp_path, scenario)


def test_skip_gives_the_default_rating_and_an_open_question_counts_as_unanswered(tmp_path, fakes):
    async def scenario(db, alice, bob):
        q = await issue(db, alice)
        await submit(db, alice, q["item_id"], answer(5))
        done = await finish(db, alice, skip=True)
        assert done["rating"] == 1000 and done["results"] == []

        await issue(db, bob)   # bob leaves question 1 open and finishes
        done = await finish(db, bob)
        assert done["rating"] == calculate_initial_rating(
            [{"difficulty": "easy", "solved": False, "time_taken_seconds": 9999, "points_earned": 0}]
        )
        assert done["results"][0]["passed_tests"] == 0

    run_with_db(tmp_path, scenario)
