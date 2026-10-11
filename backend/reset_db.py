"""Drop every table and recreate the schema from the current models.

Run from the backend/ directory:
    python reset_db.py [--yes]

Without --yes it asks for confirmation, because this destroys all users,
lobbies and match history in whatever database DATABASE_URL points at.
"""

import asyncio
import sys

from app.core.config import get_settings
from app.db.database import Base, engine, init_db
from app.models import models  # noqa: F401  (import registers the tables on Base)


async def reset() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    await engine.dispose()


def main() -> int:
    print(f"Target database: {get_settings().DATABASE_URL}")

    if "--yes" not in sys.argv:
        answer = input("Drop ALL tables and recreate them? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 1

    asyncio.run(reset())
    print("Database reset: all tables dropped and recreated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
