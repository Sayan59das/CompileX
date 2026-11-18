"""Who is on the other end of a socket.

A socket used to be trusted with whatever it said: any browser could send any user id, any score, or "start the game" for someone else's lobby. Now a
socket must carry the player's sign-in token when it connects, and the server takes the user from the token, never from the message.

`authenticate` and `player_belongs` are the only two places that touch the token and the database, so the tests can replace them.
"""

from typing import Optional

import jwt
from sqlalchemy import select

from app.core.config import get_settings

settings = get_settings()


async def authenticate(token) -> Optional[dict]:
    """{"user_id", "username"} for a valid, unexpired sign-in token of a user that still exists; otherwise None."""
    if not token or not isinstance(token, str):
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None

    from app.db.database import session_factory
    from app.models.models import User

    async with session_factory() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return {"user_id": user.id, "username": user.username} if user else None


async def player_belongs(player_id, lobby_id, user_id) -> bool:
    """True when `player_id` is this user's seat in this lobby (the row the join request created)."""
    if not isinstance(player_id, int) or not isinstance(lobby_id, int):
        return False

    from app.db.database import session_factory
    from app.models.models import Player

    async with session_factory() as db:
        row = (
            await db.execute(select(Player.id).where(Player.id == player_id, Player.lobby_id == lobby_id, Player.user_id == user_id))
        ).first()
    return row is not None
