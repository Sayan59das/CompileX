"""Hidden tests stay on the server: the browser holds the examples, never the other tests' inputs or expected outputs.

The helpers are tested as plain functions; the routes are called directly on a throwaway SQLite database with the question
generator, the code runner and the logic analyzer faked, so no Docker, question service or browser is needed.

Run from the backend folder:  python -m pytest tests/test_hidden_tests.py -q
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1 import routes
from app.db.database import Base, build_engine
from app.models.models import IssuedQuestion, Lobby, Player, Question, User
from app.schemas.schemas import AIQuestionRequest, QuestionCreate
from app.services import hidden_tests as ht
from app.services.assessment_grading import SAMPLE_TESTS
from app.services.code_executor import ExecutionResult, SubmissionResult

SECRETS = [f"SECRET-IN-{i}" for i in range(6)]
ANSWERS = [f"SECRET-OUT-{i}" for i in range(6)]
FULL_TESTS = [{"input": SECRETS[i], "output": ANSWERS[i]} for i in range(6)]
STARTER = json.dumps({"python": "def solve(n):\n    # Write your logic here\n    pass\n"})


def generated():
    return {
        "title": "Echo", "base_title": "Echo", "description": "Echo it.", "difficulty": "easy", "topic": "arrays",
        "test_cases": json.dumps(FULL_TESTS), "starter_code": STARTER, "function_name": "solve",
        "parameters": json.dumps([{"name": "n", "type": "int"}]), "return_type": "int", "return_description": "x",
        "diagram": None,
    }


def leaks(value) -> list[str]:
    """Which hidden inputs or answers appear anywhere in a value (a dict, a string, a response model)."""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return [s for s in SECRETS[SAMPLE_TESTS:] + ANSWERS[SAMPLE_TESTS:] if s in text]


# ── the helpers ─────────────────────────────────────────────────────────────


def test_public_tests_keep_the_examples_and_blank_the_rest_without_changing_the_count():
    shown = json.loads(ht.public_tests(json.dumps(FULL_TESTS)))
    assert len(shown) == len(FULL_TESTS)
    assert shown[:SAMPLE_TESTS] == FULL_TESTS[:SAMPLE_TESTS]
    assert all(t == {"input": "", "output": "", "hidden": True} for t in shown[SAMPLE_TESTS:])
    assert leaks(ht.public_tests(FULL_TESTS)) == []          # a list is accepted too
    assert json.loads(ht.public_tests("not json")) == []


def test_redacted_details_keep_pass_or_fail_but_nothing_else_for_hidden_tests():
    details = [
        {"index": i, "input": SECRETS[i], "expected_output": ANSWERS[i], "actual_output": "x" + ANSWERS[i],
         "passed": i % 2 == 0, "error": "Traceback: " + SECRETS[i] if i == 3 else None}
        for i in range(6)
    ]
    shown = ht.redact_details(details)
    assert shown[:SAMPLE_TESTS] == details[:SAMPLE_TESTS]
    assert [d["passed"] for d in shown] == [d["passed"] for d in details]
    assert leaks(shown) == []
    assert shown[3]["error"] and "Traceback" not in shown[3]["error"]      # an error is reported, its text is not
    assert shown[4]["error"] is None and all(d["hidden"] for d in shown[SAMPLE_TESTS:])


# ── the routes ──────────────────────────────────────────────────────────────


class Fakes:
    def __init__(self):
        self.analyzer_saw = None
        self.fail_from = 0   # tests at or after this index fail

    async def generate_question(self, *args, **kwargs):
        return generated()

    async def execute_code(self, code, language, test_cases, time_limit_ms=2000, function_signature=None):
        results = [
            ExecutionResult(success=True, passed=i < self.fail_from, output="out" if i < self.fail_from else ANSWERS[i] + "-wrong",
                            error="boom " + SECRETS[i] if i == 5 else None)
            for i in range(len(test_cases))
        ]
        return SubmissionResult(len(test_cases), min(self.fail_from, len(test_cases)), 1.0, results, score=100)

    async def analyze_logic(self, **kwargs):
        self.analyzer_saw = kwargs["test_results"]
        return {"logic_correctness": 50, "analysis": "ok", "partial_score": 50}


@pytest.fixture
def fakes(monkeypatch):
    from app.services.logic_analyzer import logic_analyzer

    async def no_achievements(*a, **k):
        return None

    f = Fakes()
    monkeypatch.setattr(routes.ai_generator, "generate_question", f.generate_question)
    monkeypatch.setattr(routes.code_executor, "execute_code", f.execute_code)
    monkeypatch.setattr(logic_analyzer, "analyze_logic", f.analyze_logic)
    monkeypatch.setattr(routes, "_check_rate_limit", lambda *a, **k: (True, ""))
    monkeypatch.setattr(routes, "_check_achievements", no_achievements)
    return f


def run_with_db(tmp_path, scenario):
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add_all([User(username="alice"), User(username="bob")])
            await db.commit()
            alice = (await db.execute(select(User).where(User.username == "alice"))).scalar_one()
            bob = (await db.execute(select(User).where(User.username == "bob"))).scalar_one()
            await scenario(db, alice, bob)
        await engine.dispose()

    asyncio.run(main())


async def generate(db, user):
    return await routes.generate_question(AIQuestionRequest(difficulty="easy", topic="arrays"), db=db, current_user=user)


def as_create(public: dict, **over) -> QuestionCreate:
    """What the pages send back to POST /questions: the generated question echoed (Game) or rebuilt field by field (Practice)."""
    body = {k: public[k] for k in ("title", "description", "difficulty", "topic", "starter_code", "test_cases", "ref")}
    body.update(over)
    return QuestionCreate(**body)


def test_a_generated_question_reaches_the_browser_without_its_hidden_tests(tmp_path, fakes):
    async def scenario(db, alice, bob):
        public = await generate(db, alice)
        assert public["ref"] and leaks(public) == []
        shown = json.loads(public["test_cases"])
        assert len(shown) == 6 and shown[:2] == FULL_TESTS[:2]
        kept = (await db.execute(select(IssuedQuestion))).scalar_one()      # the server still has all of it
        assert kept.ref == public["ref"] and kept.user_id == alice.id
        assert json.loads(json.loads(kept.question_json)["test_cases"]) == FULL_TESTS

    run_with_db(tmp_path, scenario)


def test_creating_the_question_builds_it_from_the_servers_copy_and_does_not_hand_the_tests_back(tmp_path, fakes):
    async def scenario(db, alice, bob):
        public = await generate(db, alice)
        saved = await routes.create_question(as_create(public), db=db, current_user=alice)
        assert leaks(saved.model_dump()) == []
        row = (await db.execute(select(Question).where(Question.id == saved.id))).scalar_one()
        assert json.loads(row.test_cases) == FULL_TESTS                      # graded against the real tests
        assert row.function_name == "solve" and json.loads(row.parameters) == [{"name": "n", "type": "int"}]

    run_with_db(tmp_path, scenario)


def test_the_clients_own_tests_and_harness_are_ignored_when_a_ref_comes_with_them(tmp_path, fakes):
    async def scenario(db, alice, bob):
        public = await generate(db, alice)
        fake_tests = json.dumps([{"input": "1", "output": "1"}])
        fake_starter = json.dumps({"python": "def solve(n):\n    return n\n"})
        saved = await routes.create_question(
            as_create(public, test_cases=fake_tests, starter_code=fake_starter), db=db, current_user=alice
        )
        row = (await db.execute(select(Question).where(Question.id == saved.id))).scalar_one()
        assert json.loads(row.test_cases) == FULL_TESTS and row.starter_code == STARTER

    run_with_db(tmp_path, scenario)


def test_a_ref_belongs_to_the_player_it_was_issued_to_and_expires(tmp_path, fakes):
    async def scenario(db, alice, bob):
        public = await generate(db, alice)
        with pytest.raises(HTTPException) as e:
            await routes.create_question(as_create(public), db=db, current_user=bob)
        assert e.value.status_code == 410
        with pytest.raises(HTTPException) as e:
            await routes.create_question(as_create(public, ref="no-such-ref"), db=db, current_user=alice)
        assert e.value.status_code == 410

        # a ref older than the TTL is swept the next time one is issued
        kept = await db.get(IssuedQuestion, public["ref"])
        kept.issued_at -= ht.TTL_SECONDS + 5
        await db.commit()
        await generate(db, alice)
        assert await db.get(IssuedQuestion, public["ref"]) is None

    run_with_db(tmp_path, scenario)


def test_a_question_the_client_wrote_itself_is_stored_as_it_sent_it(tmp_path, fakes):
    async def scenario(db, alice, bob):
        own = [{"input": "1", "output": "1"}, {"input": "2", "output": "2"}, {"input": "3", "output": "3"}]
        body = QuestionCreate(title="Mine", description="d", difficulty="easy", test_cases=json.dumps(own))
        saved = await routes.create_question(body, db=db, current_user=alice)
        row = (await db.execute(select(Question).where(Question.id == saved.id))).scalar_one()
        assert json.loads(row.test_cases) == own

    run_with_db(tmp_path, scenario)


def seed_question_and_player(db, alice):
    async def go():
        public = await generate(db, alice)
        saved = await routes.create_question(as_create(public), db=db, current_user=alice)
        lobby = Lobby(code="ABC123", name="l", created_by=alice.id)
        db.add(lobby)
        await db.commit()
        db.add(Player(lobby_id=lobby.id, user_id=alice.id))
        await db.commit()
        return saved.id
    return go()


def test_run_tests_gives_input_and_answers_only_for_the_examples(tmp_path, fakes):
    async def scenario(db, alice, bob):
        qid = await seed_question_and_player(db, alice)
        fakes.fail_from = 3        # tests 0-2 pass, 3-5 fail (test 5 also errors)
        req = routes.SubmissionCreate(code="def solve(n):\n    return n\n", language="python", question_id=qid)
        out = await routes.run_tests(req, db=db, current_user=alice)
        details = out["test_case_details"]
        assert len(details) == 6 and out["total_tests"] == 6 and out["passed_tests"] == 3
        assert leaks(out) == []
        assert details[0]["input"] == SECRETS[0] and details[1]["expected_output"] == ANSWERS[1]   # the examples stay
        assert [d["passed"] for d in details] == [True, True, True, False, False, False]

    run_with_db(tmp_path, scenario)


def test_submissions_do_not_leak_and_the_analyzer_is_not_given_the_hidden_tests(tmp_path, fakes):
    async def scenario(db, alice, bob):
        qid = await seed_question_and_player(db, alice)
        fakes.fail_from = 3
        req = routes.SubmissionCreate(code="def solve(n):\n    return n\n", language="python", question_id=qid)
        out = await routes.submit_code(req, db=db, current_user=alice)
        assert leaks(out) == [] and out["total_tests"] == 6 and out["passed_tests"] == 3
        assert fakes.analyzer_saw is not None and leaks(fakes.analyzer_saw) == []
        assert [d["passed"] for d in fakes.analyzer_saw] == [True, True, True, False, False, False]   # pass/fail still informs it

    run_with_db(tmp_path, scenario)
