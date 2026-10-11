"""Copy all data from a SQLite database into a Postgres database.

Run from the backend/ directory:
    python migrate_sqlite_to_postgres.py --sqlite ./CompileX.db --postgres "postgresql://user:pw@host:5432/db"

The target schema is created from the current models. The script refuses to run
if the target already has rows (pass --truncate to empty it first). The SQLite
file is only read, never modified.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from app.db.database import Base, build_engine
from app.models import models  # noqa: F401  (import registers the tables on Base)

BATCH_SIZE = 500


def _as_utc(value):
    # SQLite's CURRENT_TIMESTAMP is UTC but comes back naive; asyncpg would treat
    # naive values as local time and shift them.
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _count(conn, table) -> int:
    return (await conn.execute(select(func.count()).select_from(table))).scalar_one()


async def migrate(sqlite_url: str, postgres_url: str, truncate: bool) -> bool:
    src_path = make_url(sqlite_url).database
    if not src_path or not os.path.isfile(src_path):
        print(f"SQLite file not found: {src_path}")
        return False

    src = build_engine(sqlite_url, echo=False)
    dst = build_engine(postgres_url, echo=False)
    if dst.dialect.name != "postgresql":
        print("Target URL is not a Postgres URL.")
        return False

    tables = list(Base.metadata.sorted_tables)

    async with dst.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if truncate:
            names = ", ".join(f'"{t.name}"' for t in tables)
            await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        else:
            non_empty = [t.name for t in tables if await _count(conn, t)]
            if non_empty:
                print(f"Target already has data in: {', '.join(non_empty)}. Use --truncate to overwrite.")
                return False

    ok = True
    async with src.connect() as sconn:
        src_columns = {
            t.name: {c["name"] for c in await sconn.run_sync(lambda c, n=t.name: inspect(c).get_columns(n))}
            for t in tables
            if await sconn.run_sync(lambda c, n=t.name: inspect(c).has_table(n))
        }

        if not src_columns:
            print("None of the app's tables exist in the SQLite file; nothing to migrate.")
            return False

        # One transaction: a failure part-way leaves the target untouched.
        async with dst.begin() as dconn:
            for table in tables:
                if table.name not in src_columns:
                    print(f"{table.name:<24} missing in SQLite, skipped")
                    continue
                cols = [c for c in table.c if c.name in src_columns[table.name]]
                rows = (await sconn.execute(select(*cols))).mappings().all()
                payload = [{k: _as_utc(v) for k, v in row.items()} for row in rows]
                for i in range(0, len(payload), BATCH_SIZE):
                    await dconn.execute(table.insert(), payload[i : i + BATCH_SIZE])

                pk = list(table.primary_key.columns)
                if len(pk) == 1 and pk[0].name == "id":
                    await dconn.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', 'id'), "
                            f'COALESCE((SELECT MAX(id) FROM "{table.name}"), 1), '
                            f'(SELECT MAX(id) FROM "{table.name}") IS NOT NULL)'
                        )
                    )

                copied = await _count(dconn, table)
                status = "ok" if copied == len(rows) else "MISMATCH"
                ok &= copied == len(rows)
                print(f"{table.name:<24} {len(rows):>7} rows -> {copied:>7}  {status}")

    await src.dispose()
    await dst.dispose()
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite", required=True, help="path or URL of the source SQLite database")
    parser.add_argument("--postgres", required=True, help="URL of the target Postgres database")
    parser.add_argument("--truncate", action="store_true", help="empty the target tables before copying")
    args = parser.parse_args()

    sqlite_url = args.sqlite if "://" in args.sqlite else f"sqlite+aiosqlite:///{args.sqlite}"
    ok = asyncio.run(migrate(sqlite_url, args.postgres, args.truncate))
    print("Migration complete." if ok else "Migration FAILED or was aborted.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
