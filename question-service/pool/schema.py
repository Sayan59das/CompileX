"""DDL of the pool database. One definition for SQLite (local development) and PostgreSQL (production).

The tables and columns are identical. Only three spellings differ, and ddl() is the one place that knows them:
the auto-numbered key, the wide integer, and (PostgreSQL only) the LIST partitioning of pool_index by difficulty, so that a
pick for (topic, difficulty) reads one small partition through one index. Timestamps are ISO-8601 UTC text and JSON is stored as
text in both, so a row means the same thing in either database.

questions     one row per generated question, with everything needed to serve it and to regenerate it (spec, seed)
pool_index    (topic, difficulty, question_id, state): the only table the serving path reads to choose a question
approvals     who approved which question and when; a question cannot go live without a row here
"""

DIFFICULTIES = ("easy", "medium", "hard")
STATUSES = ("pending", "approved", "live", "retired")


def ddl(dialect: str) -> list[str]:
    if dialect not in ("sqlite", "postgres"):
        raise ValueError(f"unknown dialect {dialect!r}")
    sqlite = dialect == "sqlite"
    key = "INTEGER PRIMARY KEY AUTOINCREMENT" if sqlite else "BIGSERIAL PRIMARY KEY"
    big = "INTEGER" if sqlite else "BIGINT"
    levels = ", ".join(f"'{d}'" for d in DIFFICULTIES)
    states = ", ".join(f"'{s}'" for s in STATUSES)
    statements = [
        f"""CREATE TABLE IF NOT EXISTS questions (
    id {key},
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ({levels})),
    title TEXT NOT NULL,
    title_key TEXT NOT NULL,
    statement TEXT NOT NULL,
    input_format TEXT NOT NULL,
    output_format TEXT NOT NULL,
    constraints TEXT NOT NULL,
    sample_input TEXT NOT NULL,
    sample_output TEXT NOT NULL,
    function_name TEXT NOT NULL,
    parameters TEXT NOT NULL,
    return_type TEXT NOT NULL,
    return_description TEXT NOT NULL,
    input_schema TEXT NOT NULL,
    output_schema TEXT NOT NULL,
    starter_code TEXT NOT NULL,
    tests TEXT NOT NULL,
    core_idea TEXT NOT NULL,
    stress TEXT,
    spec TEXT NOT NULL,
    seed {big} NOT NULL,
    signature TEXT NOT NULL,
    wording TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ({states})),
    created_at TEXT NOT NULL
)""",
        # one problem shape per (topic, difficulty) for ever: a retired question keeps its signature as a tombstone
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_signature ON questions (topic, difficulty, signature)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_title ON questions (title_key)",
        "CREATE INDEX IF NOT EXISTS ix_questions_status ON questions (topic, difficulty, status)",
    ]
    pool_columns = f"""(
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ({levels})),
    question_id {big} NOT NULL REFERENCES questions (id),
    state TEXT NOT NULL CHECK (state IN ({states})),
    PRIMARY KEY (topic, difficulty, question_id)
)"""
    if sqlite:
        statements.append(f"CREATE TABLE IF NOT EXISTS pool_index {pool_columns}")
    else:
        statements.append(f"CREATE TABLE IF NOT EXISTS pool_index {pool_columns} PARTITION BY LIST (difficulty)")
        statements += [
            f"CREATE TABLE IF NOT EXISTS pool_index_{d} PARTITION OF pool_index FOR VALUES IN ('{d}')" for d in DIFFICULTIES
        ]
    statements += [
        "CREATE INDEX IF NOT EXISTS ix_pool_pick ON pool_index (topic, difficulty, state)",
        f"""CREATE TABLE IF NOT EXISTS approvals (
    question_id {big} PRIMARY KEY REFERENCES questions (id),
    approved_by TEXT NOT NULL,
    approved_at TEXT NOT NULL
)""",
    ]
    return statements
