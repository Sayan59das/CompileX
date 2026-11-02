"""All database access of the question pool, behind one interface (PoolRepository).

The serving API, the background worker and the review tool use only these methods, so changing the storage later (a second
database, a read replica, sharding) touches this file and nothing else. Two implementations of the same SQL exist in one class:
SQLite for local development and tests, PostgreSQL for production (psycopg 3). Both use the tables from schema.py.

Rules the repository enforces itself, so no caller can break them:
  - a question starts as `pending`; only `approve` (which records who approved it) moves it to `approved`, and only an
    approved question with an approval row can be published to `live`;
  - one problem shape (signature) per (topic, difficulty) for ever: a retired question keeps its signature as a tombstone;
  - titles are unique (compared without case or extra spaces);
  - a question and its pool_index row always change in the same transaction.
"""

import json
import re
import sqlite3
import threading
import time
from contextlib import contextmanager

from . import schema


def now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def title_key(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


class PoolRepository:
    """The interface. SqlRepository implements it; tests and callers depend only on these names."""

    def init_schema(self): raise NotImplementedError
    def add_pending(self, question, spec, wording="model", now=None): raise NotImplementedError
    def approve(self, question_id, approved_by, now=None): raise NotImplementedError
    def publish(self, question_id): raise NotImplementedError
    def retire(self, question_id): raise NotImplementedError
    def get(self, question_id): raise NotImplementedError
    def sample_live(self, topic, difficulty, limit): raise NotImplementedError
    def live_ids(self, topic, difficulty): raise NotImplementedError
    def pool_sizes(self): raise NotImplementedError
    def signatures(self, topic, difficulty): raise NotImplementedError
    def title_keys(self): raise NotImplementedError
    def ids_for_titles(self, keys): raise NotImplementedError
    def max_seed(self, topic, difficulty): raise NotImplementedError
    def known_tests(self, limit=300): raise NotImplementedError
    def pending(self, topic=None, difficulty=None, limit=50): raise NotImplementedError
    def statements(self, statuses=("pending", "approved", "live")): raise NotImplementedError
    def check_consistency(self): raise NotImplementedError
    def close(self): raise NotImplementedError


class SqlRepository(PoolRepository):
    def __init__(self, connection, dialect: str):
        self.dialect = dialect
        self._conn = connection
        self._lock = threading.RLock()
        self._integrity = (sqlite3.IntegrityError,)
        if dialect == "postgres":
            import psycopg
            self._integrity = (psycopg.IntegrityError,)

    # ── connections ──
    @classmethod
    def sqlite(cls, path: str = ":memory:") -> "SqlRepository":
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=30)
        conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
        repo = cls(conn, "sqlite")
        repo.init_schema()
        return repo

    @classmethod
    def postgres(cls, url: str) -> "SqlRepository":
        import psycopg
        repo = cls(psycopg.connect(url), "postgres")
        repo.init_schema()
        return repo

    @classmethod
    def from_url(cls, url: str) -> "SqlRepository":
        """`postgresql://...` for PostgreSQL; `sqlite:///path`, a bare path or `:memory:` for SQLite."""
        if url.startswith(("postgres://", "postgresql://")):
            return cls.postgres(url)
        return cls.sqlite(url[len("sqlite:///"):] if url.startswith("sqlite:///") else url)

    # ── plumbing ──
    def _sql(self, text: str) -> str:
        return text.replace("?", "%s") if self.dialect == "postgres" else text

    @contextmanager
    def _tx(self, write: bool = False):
        with self._lock:
            if self.dialect == "sqlite":
                self._conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield
            except BaseException:
                self._conn.rollback()
                raise
            else:
                self._conn.commit()

    def _run(self, sql: str, params=()):
        cur = self._conn.cursor()
        cur.execute(self._sql(sql), tuple(params))
        return cur

    def _all(self, sql: str, params=()) -> list[dict]:
        cur = self._run(sql, params)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    def _one(self, sql: str, params=()):
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def init_schema(self) -> None:
        with self._tx(write=True):
            for statement in schema.ddl(self.dialect):
                self._run(statement)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ── writing ──
    def add_pending(self, question: dict, spec: dict, wording: str = "model", now: str | None = None):
        """Store a verified question as `pending`. Returns (id, None), or (None, reason) when its title or shape is already taken."""
        topic, difficulty, signature = question["topic"], question["difficulty"], spec["structural_signature"]
        key = title_key(question["title"])
        try:
            with self._tx(write=True):
                if self._one("SELECT 1 AS x FROM questions WHERE topic = ? AND difficulty = ? AND signature = ?", (topic, difficulty, signature)):
                    return None, "signature already in the pool"
                if self._one("SELECT 1 AS x FROM questions WHERE title_key = ?", (key,)):
                    return None, "title already in the pool"
                row = self._one(
                    """INSERT INTO questions (topic, difficulty, title, title_key, statement, input_format, output_format, constraints,
                       sample_input, sample_output, function_name, parameters, return_type, return_description, input_schema,
                       output_schema, starter_code, tests, core_idea, stress, spec, seed, signature, wording, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?) RETURNING id""",
                    (
                        topic, difficulty, question["title"], key, question["problem_statement"], question["input_format"],
                        question["output_format"], question.get("constraints", ""), question["sample_input"], question["sample_output"],
                        question["function_name"], json.dumps(question["parameters"]), question["return_type"],
                        question.get("return_description", ""), question["input_schema"], question["output_schema"],
                        json.dumps(question["starter_code"]), json.dumps(question["test_cases"]), question.get("core_idea", ""),
                        json.dumps(question["stress"]) if question.get("stress") else None, json.dumps(spec, sort_keys=True),
                        spec["seed"], signature, wording, now or now_text(),
                    ),
                )
                self._run("INSERT INTO pool_index (topic, difficulty, question_id, state) VALUES (?, ?, ?, 'pending')",
                          (topic, difficulty, row["id"]))
        except self._integrity:
            return None, "title or shape already in the pool (a concurrent insert won)"
        return row["id"], None

    def _move(self, question_id: int, allowed: tuple, target: str) -> bool:
        marks = ", ".join("?" for _ in allowed)
        cur = self._run(f"UPDATE questions SET status = ? WHERE id = ? AND status IN ({marks})", (target, question_id, *allowed))
        if cur.rowcount != 1:
            return False
        self._run("UPDATE pool_index SET state = ? WHERE question_id = ?", (target, question_id))
        return True

    def approve(self, question_id: int, approved_by: str, now: str | None = None) -> bool:
        """pending -> approved, recording who approved it. False when the question is not pending."""
        if not approved_by or not approved_by.strip():
            raise ValueError("approved_by must name the reviewer")
        with self._tx(write=True):
            if not self._move(question_id, ("pending",), "approved"):
                return False
            self._run("INSERT INTO approvals (question_id, approved_by, approved_at) VALUES (?, ?, ?)",
                      (question_id, approved_by.strip(), now or now_text()))
        return True

    def publish(self, question_id: int) -> bool:
        """approved -> live. Refuses (False) unless the question is approved AND has an approval row."""
        with self._tx(write=True):
            if not self._one("SELECT 1 AS x FROM approvals WHERE question_id = ?", (question_id,)):
                return False
            return self._move(question_id, ("approved",), "live")

    def retire(self, question_id: int) -> bool:
        """Take a question out of use for good (its shape stays taken). False if it is unknown or already retired."""
        with self._tx(write=True):
            return self._move(question_id, ("pending", "approved", "live"), "retired")

    # ── reading ──
    def get(self, question_id: int) -> dict | None:
        with self._tx():
            row = self._one("SELECT * FROM questions WHERE id = ?", (question_id,))
        return _question(row) if row else None

    def sample_live(self, topic: str, difficulty: str, limit: int) -> list[int]:
        """Up to `limit` random live question ids of the bucket: one indexed read, no pool-sized load."""
        with self._tx():
            rows = self._all(
                "SELECT question_id FROM pool_index WHERE topic = ? AND difficulty = ? AND state = 'live' ORDER BY RANDOM() LIMIT ?",
                (topic, difficulty, int(limit)),
            )
        return [r["question_id"] for r in rows]

    def live_ids(self, topic: str, difficulty: str) -> list[int]:
        with self._tx():
            rows = self._all("SELECT question_id FROM pool_index WHERE topic = ? AND difficulty = ? AND state = 'live'", (topic, difficulty))
        return [r["question_id"] for r in rows]

    def pool_sizes(self) -> dict:
        """{(topic, difficulty): {"pending": n, "approved": n, "live": n, "retired": n}}, counted from pool_index."""
        sizes: dict = {}
        with self._tx():
            rows = self._all("SELECT topic, difficulty, state, COUNT(*) AS n FROM pool_index GROUP BY topic, difficulty, state")
        for r in rows:
            sizes.setdefault((r["topic"], r["difficulty"]), {s: 0 for s in schema.STATUSES})[r["state"]] = r["n"]
        return sizes

    def signatures(self, topic: str, difficulty: str) -> set:
        with self._tx():
            rows = self._all("SELECT signature FROM questions WHERE topic = ? AND difficulty = ?", (topic, difficulty))
        return {r["signature"] for r in rows}

    def title_keys(self) -> set:
        with self._tx():
            rows = self._all("SELECT title_key FROM questions")
        return {r["title_key"] for r in rows}

    def max_seed(self, topic: str, difficulty: str) -> int:
        """The highest sampler seed used for this bucket so far (-1 when there is none), so a restarted worker never reuses one."""
        with self._tx():
            row = self._one("SELECT MAX(seed) AS top FROM questions WHERE topic = ? AND difficulty = ?", (topic, difficulty))
        return -1 if row is None or row["top"] is None else int(row["top"])

    def known_tests(self, limit: int = 300) -> list[dict]:
        """[{"title", "test_cases"}] of recent non-retired questions, for the check that a new question is not an old one in disguise."""
        with self._tx():
            rows = self._all("SELECT title, tests FROM questions WHERE status <> 'retired' ORDER BY id DESC LIMIT ?", (int(limit),))
        return [{"title": r["title"], "test_cases": json.loads(r["tests"])} for r in rows]

    def ids_for_titles(self, keys) -> list[int]:
        """Ids of the questions whose normalised title is in `keys` (what a caller that excludes by title means)."""
        keys = list(keys)
        if not keys:
            return []
        marks = ", ".join("?" for _ in keys)
        with self._tx():
            rows = self._all(f"SELECT id FROM questions WHERE title_key IN ({marks})", tuple(keys))
        return [r["id"] for r in rows]

    def pending(self, topic: str | None = None, difficulty: str | None = None, limit: int = 50) -> list[dict]:
        where, params = ["status = 'pending'"], []
        for column, value in (("topic", topic), ("difficulty", difficulty)):
            if value:
                where.append(f"{column} = ?")
                params.append(value)
        with self._tx():
            rows = self._all(f"SELECT * FROM questions WHERE {' AND '.join(where)} ORDER BY id LIMIT ?", (*params, int(limit)))
        return [_question(r) for r in rows]

    def statements(self, statuses=("pending", "approved", "live")) -> dict:
        """{question id: statement} for the novelty index."""
        marks = ", ".join("?" for _ in statuses)
        with self._tx():
            rows = self._all(f"SELECT id, statement FROM questions WHERE status IN ({marks})", tuple(statuses))
        return {r["id"]: r["statement"] for r in rows}

    def approval(self, question_id: int) -> dict | None:
        with self._tx():
            return self._one("SELECT * FROM approvals WHERE question_id = ?", (question_id,))

    def check_consistency(self) -> list[str]:
        """Disagreements between questions, pool_index and approvals (empty when the pool is sound)."""
        problems = []
        with self._tx():
            for r in self._all(
                "SELECT q.id AS id, q.status AS status, p.state AS state FROM questions q LEFT JOIN pool_index p ON p.question_id = q.id "
                "WHERE p.state IS NULL OR p.state <> q.status"
            ):
                problems.append(f"question {r['id']} is {r['status']} but its pool_index state is {r['state']}")
            for r in self._all("SELECT p.question_id AS id FROM pool_index p LEFT JOIN questions q ON q.id = p.question_id WHERE q.id IS NULL"):
                problems.append(f"pool_index points at missing question {r['id']}")
            for r in self._all(
                "SELECT q.id AS id FROM questions q LEFT JOIN approvals a ON a.question_id = q.id WHERE q.status IN ('approved', 'live') AND a.question_id IS NULL"
            ):
                problems.append(f"question {r['id']} is approved or live without an approval")
        return problems


def _question(row: dict) -> dict:
    """A stored row as the question dict the rest of the system uses (same keys as verify.verify_spec returns)."""
    return {
        "id": row["id"], "title": row["title"], "base_title": row["title"], "problem_statement": row["statement"],
        "input_format": row["input_format"], "output_format": row["output_format"], "constraints": row["constraints"],
        "sample_input": row["sample_input"], "sample_output": row["sample_output"], "test_cases": json.loads(row["tests"]),
        "function_name": row["function_name"], "parameters": json.loads(row["parameters"]), "return_type": row["return_type"],
        "return_description": row["return_description"], "input_schema": row["input_schema"], "output_schema": row["output_schema"],
        "starter_code": json.loads(row["starter_code"]), "core_idea": row["core_idea"],
        "stress": json.loads(row["stress"]) if row["stress"] else None, "topic": row["topic"], "difficulty": row["difficulty"],
        "status": row["status"], "signature": row["signature"], "seed": row["seed"], "spec": json.loads(row["spec"]),
        "wording": row["wording"], "created_at": row["created_at"], "source": "pool",
    }
