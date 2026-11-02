"""Checks for the pool database layer (SQLite here; PostgreSQL when COMPILEX_TEST_PG_URL is set)."""

import json
import os
import re

import pytest

from pool import schema
from pool.repository import SqlRepository, title_key
from tests.pool_helpers import add_live, add_pending, make_question, make_spec


@pytest.fixture
def repo():
    repository = SqlRepository.sqlite(":memory:")
    yield repository
    repository.close()


# ── schema ───────────────────────────────────────────────────────────────

def columns(ddl_statements, table):
    for statement in ddl_statements:
        if statement.startswith(f"CREATE TABLE IF NOT EXISTS {table} ("):
            return re.findall(r"^\s{4}(\w+) ", statement, re.M)
    raise AssertionError(table)


def test_both_databases_get_the_same_tables_and_columns():
    for table in ("questions", "pool_index", "approvals"):
        assert columns(schema.ddl("sqlite"), table) == columns(schema.ddl("postgres"), table)
    assert columns(schema.ddl("sqlite"), "questions")[:6] == ["id", "topic", "difficulty", "title", "title_key", "statement"]


def test_postgres_partitions_the_pick_table_by_difficulty_and_sqlite_does_not():
    pg = "\n".join(schema.ddl("postgres"))
    assert "PARTITION BY LIST (difficulty)" in pg
    for level in schema.DIFFICULTIES:
        assert f"pool_index_{level} PARTITION OF pool_index FOR VALUES IN ('{level}')" in pg
    assert "PARTITION" not in "\n".join(schema.ddl("sqlite"))


def test_the_ddl_for_an_unknown_dialect_is_refused():
    with pytest.raises(ValueError):
        schema.ddl("oracle")


def test_the_pick_is_one_indexed_lookup():
    for dialect in ("sqlite", "postgres"):
        assert any("ix_pool_pick ON pool_index (topic, difficulty, state)" in s for s in schema.ddl(dialect))


# ── life cycle ───────────────────────────────────────────────────────────

def test_a_new_question_is_pending_and_not_servable(repo):
    question_id = add_pending(repo, 1)
    stored = repo.get(question_id)
    assert stored["status"] == "pending" and stored["title"] == "Question 1" and stored["signature"] == "sig-arrays-easy-1"
    assert repo.sample_live("arrays", "easy", 10) == [] and repo.live_ids("arrays", "easy") == []
    assert repo.pool_sizes()[("arrays", "easy")] == {"pending": 1, "approved": 0, "live": 0, "retired": 0}


def test_stored_json_comes_back_as_it_went_in(repo):
    question_id = add_pending(repo, 3)
    stored = repo.get(question_id)
    original = make_question(3)
    assert stored["test_cases"] == original["test_cases"] and stored["starter_code"] == original["starter_code"]
    assert stored["parameters"] == original["parameters"] and stored["spec"] == make_spec(3) and stored["stress"] is None
    assert stored["problem_statement"] == original["problem_statement"] and stored["source"] == "pool"


def test_stress_information_is_kept(repo):
    question = make_question(4)
    question["stress"] = {"size": 3000, "seconds": 0.2}
    question_id, _ = repo.add_pending(question, make_spec(4))
    assert repo.get(question_id)["stress"] == {"size": 3000, "seconds": 0.2}


def test_only_an_approved_question_can_be_published_and_approval_needs_a_reviewer(repo):
    question_id = add_pending(repo, 1)
    assert repo.publish(question_id) is False and repo.get(question_id)["status"] == "pending"
    with pytest.raises(ValueError):
        repo.approve(question_id, "  ")
    assert repo.approve(question_id, "sayan", now="2026-10-16T10:00:00Z") is True
    assert repo.get(question_id)["status"] == "approved"
    assert repo.approval(question_id) == {"question_id": question_id, "approved_by": "sayan", "approved_at": "2026-10-16T10:00:00Z"}
    assert repo.approve(question_id, "someone else") is False
    assert repo.publish(question_id) is True and repo.get(question_id)["status"] == "live"
    assert repo.publish(question_id) is False
    assert repo.sample_live("arrays", "easy", 5) == [question_id]


def test_a_question_without_an_approval_row_cannot_be_published_even_if_marked_approved(repo):
    question_id = add_pending(repo, 1)
    with repo._tx(write=True):                      # tampering that the interface itself does not allow
        repo._run("UPDATE questions SET status = 'approved' WHERE id = ?", (question_id,))
        repo._run("UPDATE pool_index SET state = 'approved' WHERE question_id = ?", (question_id,))
    assert repo.publish(question_id) is False
    assert any("without an approval" in p for p in repo.check_consistency())


def test_retiring_removes_a_question_from_service_but_keeps_its_shape_taken(repo):
    question_id = add_live(repo, 1)
    assert repo.retire(question_id) is True and repo.retire(question_id) is False
    assert repo.sample_live("arrays", "easy", 5) == [] and repo.pool_sizes()[("arrays", "easy")]["retired"] == 1
    again, reason = repo.add_pending(make_question(2), make_spec(1))             # same signature, other title
    assert again is None and reason == "signature already in the pool"
    assert make_spec(1)["structural_signature"] in repo.signatures("arrays", "easy")
    assert repo.retire(99999) is False


def test_pending_questions_can_be_rejected_and_unknown_ids_are_harmless(repo):
    question_id = add_pending(repo, 1)
    assert repo.retire(question_id) and repo.approve(question_id, "x") is False and repo.get(424242) is None


def test_a_shape_or_a_title_can_be_stored_only_once(repo):
    add_pending(repo, 1)
    same_shape, why = repo.add_pending(make_question(2), make_spec(1))
    assert same_shape is None and why == "signature already in the pool"
    same_title, why = repo.add_pending(make_question(1, title="  QUESTION   1 "), make_spec(2))
    assert same_title is None and why == "title already in the pool"
    other_bucket, _ = repo.add_pending(make_question(5, topic="strings"), {**make_spec(1), "structural_signature": "sig-arrays-easy-1"})
    assert other_bucket is not None                                                # the same shape in another topic is fine


def test_a_failed_write_leaves_nothing_behind(repo, monkeypatch):
    original = repo._run

    def failing(sql, params=()):
        if sql.startswith("INSERT INTO pool_index"):
            raise RuntimeError("disk full")
        return original(sql, params)

    monkeypatch.setattr(repo, "_run", failing)
    with pytest.raises(RuntimeError):
        repo.add_pending(make_question(1), make_spec(1))
    monkeypatch.setattr(repo, "_run", original)
    assert repo.title_keys() == set() and repo.pool_sizes() == {} and repo.check_consistency() == []
    assert repo.add_pending(make_question(1), make_spec(1))[0] is not None          # and the same question can still be added


def test_approve_and_publish_roll_back_together(repo, monkeypatch):
    question_id = add_pending(repo, 1)
    original = repo._run

    def failing(sql, params=()):
        if sql.startswith("INSERT INTO approvals"):
            raise RuntimeError("boom")
        return original(sql, params)

    monkeypatch.setattr(repo, "_run", failing)
    with pytest.raises(RuntimeError):
        repo.approve(question_id, "sayan")
    monkeypatch.setattr(repo, "_run", original)
    assert repo.get(question_id)["status"] == "pending" and repo.approval(question_id) is None and repo.check_consistency() == []


# ── picking and counting ─────────────────────────────────────────────────

def test_sampling_stays_inside_the_bucket_respects_the_limit_and_varies(repo):
    easy = [add_live(repo, n) for n in range(1, 11)]
    add_live(repo, 11, difficulty="hard")
    add_live(repo, 12, topic="strings")
    add_pending(repo, 13)
    assert set(repo.live_ids("arrays", "easy")) == set(easy)
    assert len(repo.sample_live("arrays", "easy", 4)) == 4 and len(set(repo.sample_live("arrays", "easy", 50))) == 10
    assert repo.sample_live("arrays", "easy", 0) == []
    seen = set()
    for _ in range(60):
        seen |= set(repo.sample_live("arrays", "easy", 2))
    assert seen == set(easy)
    assert repo.sample_live("graphs", "easy", 5) == []


def test_pool_sizes_count_every_state_per_bucket(repo):
    a, b, c, d = (add_pending(repo, n) for n in range(1, 5))
    repo.approve(a, "r"); repo.publish(a)
    repo.approve(b, "r")
    repo.retire(c)
    add_live(repo, 9, difficulty="medium")
    sizes = repo.pool_sizes()
    assert sizes[("arrays", "easy")] == {"pending": 1, "approved": 1, "live": 1, "retired": 1}
    assert sizes[("arrays", "medium")]["live"] == 1 and repo.check_consistency() == []


def test_listing_and_lookup_helpers(repo):
    first, second = add_pending(repo, 1), add_pending(repo, 2, difficulty="hard")
    add_live(repo, 3)
    assert [q["id"] for q in repo.pending()] == [first, second]
    assert [q["id"] for q in repo.pending(difficulty="hard")] == [second] and repo.pending(topic="strings") == []
    assert len(repo.pending(limit=1)) == 1
    assert repo.statements()[first] == "Statement number 1 about trays of rolls."
    assert set(repo.statements(("live",))) == {3}
    assert repo.title_keys() == {"question 1", "question 2", "question 3"}
    assert set(repo.ids_for_titles({"question 1", "question 3", "nothing"})) == {first, 3} and repo.ids_for_titles([]) == []
    assert repo.signatures("arrays", "easy") == {"sig-arrays-easy-1", "sig-arrays-easy-3"}
    assert repo.max_seed("arrays", "easy") == 3 and repo.max_seed("graphs", "easy") == -1
    known = repo.known_tests(10)
    assert {k["title"] for k in known} == {"Question 1", "Question 2", "Question 3"} and known[0]["test_cases"][0]["input"]


def test_known_tests_leave_out_retired_questions(repo):
    gone = add_live(repo, 1)
    add_live(repo, 2)
    repo.retire(gone)
    assert [k["title"] for k in repo.known_tests()] == ["Question 2"]


# ── files and urls ───────────────────────────────────────────────────────

def test_a_file_database_keeps_its_data_and_two_connections_share_it(tmp_path):
    path = str(tmp_path / "pool.db")
    first = SqlRepository.sqlite(path)
    question_id = add_live(first, 1)
    second = SqlRepository.from_url(path)
    assert second.live_ids("arrays", "easy") == [question_id]
    add_live(second, 2)
    assert set(first.live_ids("arrays", "easy")) == {question_id, 2}
    first.close(); second.close()
    reopened = SqlRepository.from_url(f"sqlite:///{path}")
    assert len(reopened.live_ids("arrays", "easy")) == 2 and reopened.check_consistency() == []
    reopened.close()


def test_the_database_enforces_the_rules_itself(repo):
    add_pending(repo, 1)
    with pytest.raises(Exception):
        with repo._tx(write=True):
            repo._run("UPDATE questions SET status = 'weird' WHERE id = 1")
    with pytest.raises(Exception):
        with repo._tx(write=True):
            repo._run("INSERT INTO pool_index (topic, difficulty, question_id, state) VALUES ('arrays', 'easy', 999, 'live')")
    with pytest.raises(Exception):
        with repo._tx(write=True):
            repo._run("UPDATE questions SET difficulty = 'extreme' WHERE id = 1")


def test_title_keys_ignore_case_and_spacing():
    assert title_key("  Tray   Totals ") == title_key("tray totals") == "tray totals"


@pytest.mark.skipif(not os.environ.get("COMPILEX_TEST_PG_URL"), reason="set COMPILEX_TEST_PG_URL to run against PostgreSQL")
def test_the_same_life_cycle_works_on_postgres():
    repository = SqlRepository.postgres(os.environ["COMPILEX_TEST_PG_URL"])
    try:
        with repository._tx(write=True):
            repository._run("DELETE FROM approvals"); repository._run("DELETE FROM pool_index"); repository._run("DELETE FROM questions")
        question_id = add_pending(repository, 1)
        assert repository.publish(question_id) is False
        assert repository.approve(question_id, "tester") and repository.publish(question_id)
        assert repository.sample_live("arrays", "easy", 3) == [question_id]
        assert repository.pool_sizes()[("arrays", "easy")]["live"] == 1 and repository.check_consistency() == []
        assert repository.add_pending(make_question(2), make_spec(1))[0] is None
    finally:
        repository.close()
