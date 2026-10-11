"""Question history service tests. Run from backend/: python -m pytest tests/test_question_history.py"""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.database import Base, build_engine
from app.models.models import User
from app.services import question_history as qh


def run_with_db(tmp_path, scenario):
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add_all([User(username=f"u{i}") for i in range(1, 4)])
            await db.commit()
            await scenario(db)
        await engine.dispose()

    asyncio.run(main())


def test_key_ignores_case_and_spacing():
    assert qh.question_key("Two  Sum ") == qh.question_key("two sum")
    assert qh.question_key("Two Sum") != qh.question_key("Three Sum")


def test_seen_titles_is_per_user_and_per_topic(tmp_path):
    async def scenario(db):
        await qh.record_seen(db, [1], "Two Sum", "arrays", "easy")
        await qh.record_seen(db, [1], "Reverse String", "strings", "easy")
        await qh.record_seen(db, [2], "Max Subarray", "arrays", "medium")

        assert await qh.seen_titles(db, [1], "arrays") == ["two sum"]
        assert set(await qh.seen_titles(db, [1])) == {"two sum", "reverse string"}
        assert await qh.seen_titles(db, [3], "arrays") == []

    run_with_db(tmp_path, scenario)


def test_lobby_exclusion_is_the_union_of_all_players(tmp_path):
    async def scenario(db):
        await qh.record_seen(db, [1], "Two Sum", "arrays", "easy")
        await qh.record_seen(db, [2], "Max Subarray", "arrays", "easy")

        assert set(await qh.seen_titles(db, [1, 2, 3], "arrays")) == {"two sum", "max subarray"}

    run_with_db(tmp_path, scenario)


def test_topic_spelling_variants_match(tmp_path):
    async def scenario(db):
        await qh.record_seen(db, [1], "Coin Change", "dynamic-programming", "medium")

        assert await qh.seen_titles(db, [1], "Dynamic Programming") == ["coin change"]

    run_with_db(tmp_path, scenario)


def test_recording_twice_keeps_one_row_per_user(tmp_path):
    async def scenario(db):
        await qh.record_seen(db, [1, 2], "Two Sum", "arrays", "easy")
        await qh.record_seen(db, [2, 3], "two sum", "arrays", "easy")

        assert await qh.seen_titles(db, [1], "arrays") == ["two sum"]
        assert await qh.seen_titles(db, [3], "arrays") == ["two sum"]
        from sqlalchemy import func, select
        from app.models.models import UserQuestionHistory

        total = (await db.execute(select(func.count()).select_from(UserQuestionHistory))).scalar_one()
        assert total == 3

    run_with_db(tmp_path, scenario)


def test_limit_keeps_the_most_recent(tmp_path):
    async def scenario(db):
        for i in range(5):
            await qh.record_seen(db, [1], f"Problem {i}", "arrays", "easy")
            await asyncio.sleep(1.1)  # seen_at has one-second resolution in SQLite

        assert await qh.seen_titles(db, [1], "arrays", limit=2) == ["problem 4", "problem 3"]

    run_with_db(tmp_path, scenario)
