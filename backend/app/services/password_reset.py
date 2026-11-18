"""The password-reset code (OTP): making one, and trying one so that a guess can never be tried more than five times.

Before: the code came from `random` (not meant for secrets), and each guess was "read the count, compare, write count + 1" in separate steps, so
many guesses sent at the same moment all read the same count and all got checked: far more than five tries per code. A new code also reset the
count, so asking again and again gave endless fresh tries.

Now: the code comes from `secrets`; a guess first spends one of the five tries in a single UPDATE the database applies one request at a time (and
only while the code is live and tries remain), and only the request that spent a try gets to compare. A right code is burnt in the same statement
that changes the password, so it works once.
"""

import hmac
import secrets
from datetime import datetime, timedelta
from typing import Tuple

from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User

MAX_ATTEMPTS = 5
OTP_MINUTES = 10
COOLDOWN_SECONDS = 60            # a new code is not made if one was made less than this long ago (it is still valid)

GENERIC_REQUEST_REPLY = {
    "message": "If that account has an email address, a code has been sent to it.",
    "success": True,
}
BAD_CODE = "Invalid or expired code. Please request a new one."


def new_otp() -> str:
    return f"{secrets.randbelow(10 ** 6):06d}"


def made_too_recently(user: User, now: datetime) -> bool:
    return bool(user.reset_otp and user.reset_otp_expires and user.reset_otp_expires - timedelta(minutes=OTP_MINUTES) > now - timedelta(seconds=COOLDOWN_SECONDS))


async def store_new_otp(db: AsyncSession, user_id: int, otp: str, now: datetime) -> None:
    await db.execute(
        update(User).where(User.id == user_id)
        .values(reset_otp=otp, reset_otp_expires=now + timedelta(minutes=OTP_MINUTES), reset_otp_attempts=0)
        .execution_options(synchronize_session=False)
    )
    await db.commit()


async def clear_otp(db: AsyncSession, user_id: int) -> None:
    """Forget a code that could not be delivered, so asking again straight away makes a new one."""
    await db.execute(
        update(User).where(User.id == user_id)
        .values(reset_otp=None, reset_otp_expires=None, reset_otp_attempts=0).execution_options(synchronize_session=False)
    )
    await db.commit()


async def _burn(db: AsyncSession, username: str, now: datetime) -> None:
    """Remove a code that has expired or run out of tries, so a new one has to be asked for."""
    await db.execute(
        update(User).where(
            User.username == username, User.reset_otp.is_not(None),
            or_(User.reset_otp_expires <= now, User.reset_otp_attempts >= MAX_ATTEMPTS),
        ).values(reset_otp=None, reset_otp_expires=None, reset_otp_attempts=0).execution_options(synchronize_session=False)
    )
    await db.commit()


async def verify_and_reset(db: AsyncSession, username: str, otp: str, make_hash) -> Tuple[bool, str]:
    """(done, message). The same answer for an unknown user, no code, an expired code and a used-up code.

    `make_hash()` returns the new password's hash; it is only called for a right code, because hashing is slow and a wrong guess should cost little."""
    now = datetime.utcnow()

    spent = (
        await db.execute(
            update(User).where(
                User.username == username, User.reset_otp.is_not(None), User.reset_otp_expires > now, User.reset_otp_attempts < MAX_ATTEMPTS,
            )
            .values(reset_otp_attempts=User.reset_otp_attempts + 1)
            .returning(User.id, User.reset_otp, User.reset_otp_attempts)
            .execution_options(synchronize_session=False)
        )
    ).first()
    await db.commit()

    if spent is None:
        await _burn(db, username, now)
        return False, BAD_CODE

    user_id, stored, attempts = spent
    if not hmac.compare_digest(str(stored).encode(), str(otp).encode()):
        remaining = MAX_ATTEMPTS - attempts
        if remaining <= 0:
            await _burn(db, username, now)
            return False, "Too many failed attempts. Please request a new code."
        return False, f"Invalid code. {remaining} attempts remaining."

    # Right code: burn it and change the password in one statement; if another request got here first it matches nothing.
    changed = (
        await db.execute(
            update(User).where(User.id == user_id, User.reset_otp == stored)
            .values(hashed_password=make_hash(), reset_otp=None, reset_otp_expires=None, reset_otp_attempts=0)
            .execution_options(synchronize_session=False)
        )
    ).rowcount
    await db.commit()
    return (True, "Password reset successful. You can now login with your new password.") if changed == 1 else (False, BAD_CODE)
