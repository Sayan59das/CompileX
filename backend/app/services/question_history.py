import hashlib
import re
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import UserQuestionHistory

# The question service excludes by title, so cap what we send per request.
MAX_EXCLUDED_TITLES = 1000


def normalize_title(title: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def normalize_topic(topic: Optional[str]) -> str:
    return re.sub(r"[\s_-]+", " ", (topic or "").strip().lower())


def question_key(title: str) -> str:
    return hashlib.sha1(normalize_title(title).encode()).hexdigest()[:20]


async def seen_titles(
    db: AsyncSession,
    user_ids: Iterable[int],
    topic: Optional[str] = None,
    limit: int = MAX_EXCLUDED_TITLES,
) -> list[str]:
    """Titles any of these users has already seen, most recent first."""
    user_ids = list(set(user_ids))
    if not user_ids:
        return []
    stmt = select(func.max(UserQuestionHistory.title)).where(
        UserQuestionHistory.user_id.in_(user_ids)
    )
    if topic:
        stmt = stmt.where(UserQuestionHistory.topic == normalize_topic(topic))
    stmt = (
        stmt.group_by(UserQuestionHistory.question_key)
        .order_by(func.max(UserQuestionHistory.seen_at).desc())
        .limit(limit)
    )
    return [normalize_title(t) for t in (await db.execute(stmt)).scalars().all()]


async def record_seen(
    db: AsyncSession,
    user_ids: Iterable[int],
    title: Optional[str],
    topic: Optional[str],
    difficulty,
) -> None:
    """Mark a question as seen by each user; users who already saw it are skipped."""
    title = (title or "").strip()
    user_ids = set(user_ids)
    if not title or not user_ids:
        return

    key = question_key(title)
    already = set(
        (
            await db.execute(
                select(UserQuestionHistory.user_id).where(
                    UserQuestionHistory.question_key == key,
                    UserQuestionHistory.user_id.in_(user_ids),
                )
            )
        ).scalars()
    )
    for uid in user_ids - already:
        db.add(
            UserQuestionHistory(
                user_id=uid,
                question_key=key,
                title=title[:255],
                topic=normalize_topic(topic) or None,
                difficulty=getattr(difficulty, "value", difficulty),
            )
        )
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent request recorded the same (user, question); nothing to add.
        await db.rollback()
