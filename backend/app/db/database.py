from typing import AsyncGenerator
from uuid import uuid4
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()


def _normalize_db_url(url: str) -> str:
    """Ensure the database URL uses an async-compatible driver scheme."""
    # Render / Supabase provide plain postgres:// or postgresql:// URLs;
    # SQLAlchemy async needs postgresql+asyncpg:// (or sqlite+aiosqlite://)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def build_engine(raw_url: str, **overrides) -> AsyncEngine:
    """Create an async engine, adding the settings Postgres hosts need."""
    url = make_url(_normalize_db_url(raw_url))
    kwargs: dict = {"echo": settings.DEBUG, "future": True}

    if url.get_backend_name() == "postgresql":
        query = dict(url.query)
        # asyncpg has no `sslmode`; connection strings copied from Supabase/Render often carry one.
        sslmode = query.pop("sslmode", None)
        if sslmode and "ssl" not in query:
            query["ssl"] = sslmode
        host = url.host or ""
        if "supabase" in host and "ssl" not in query:
            query["ssl"] = "require"
        url = url.set(query=query)

        kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800)

        # Supabase's pooler runs pgbouncer in transaction mode, which breaks asyncpg prepared statements.
        if "pooler.supabase.com" in host or url.port == 6543:
            kwargs["connect_args"] = {
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
            }

    kwargs.update(overrides)
    return create_async_engine(url, **kwargs)


engine = build_engine(settings.DATABASE_URL)

# expire_on_commit=False so we can still read attributes after committing
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


async def init_db():
    # creates all tables if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns to existing tables if they don't exist (safe migration)
        await conn.run_sync(_migrate_add_columns)


def _migrate_add_columns(conn):
    """Safely add new columns to existing tables without dropping data."""
    from sqlalchemy import text, inspect
    inspector = inspect(conn)

    # New columns added to the users table
    new_user_columns = [
        ("skill_quiz_completed", "BOOLEAN DEFAULT FALSE"),
        ("peak_rating",          "INTEGER DEFAULT 1000"),
        ("games_played",         "INTEGER DEFAULT 0"),
        ("wins",                 "INTEGER DEFAULT 0"),
    ]

    existing = {col["name"] for col in inspector.get_columns("users")}
    for col_name, col_def in new_user_columns:
        if col_name not in existing:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
            print(f"[DB MIGRATION] Added column users.{col_name}")
