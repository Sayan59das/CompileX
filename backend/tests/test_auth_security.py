"""Sign-in, sign-up and password reset cannot be hammered any more (security review, problem 3).

Before: no rate limit anywhere on these routes; the reset code came from `random`; wrong guesses were counted by "read, compare, write" so guesses sent
at the same moment all got checked; asking for a new code reset the count; "Username not found" told anyone which names have accounts.

Run from the backend folder:  python -m pytest tests/test_auth_security.py -q
"""

import asyncio
import os
import re
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from app.api.v1 import routes
from app.db.database import Base, get_db
from app.main import app_http
from app.models.models import User
from app.services import auth_limits, password_reset, shared_state as ss
from app.services.email_service import email_service


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    ss.set_redis(ss.MemoryRedis())

    # The tests hash passwords dozens of times; the real cost factor would take over a minute. Any bcrypt hash verifies the same way.
    import bcrypt

    monkeypatch.setattr(routes, "get_password_hash", lambda p: bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=4)).decode())
    yield
    ss.set_redis(None)


def run(coro):
    return asyncio.run(coro)


def fake_request(forwarded=None, host="10.0.0.1"):
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (host, 5000), "method": "GET", "path": "/"})


# ── the limiter ─────────────────────────────────────────────────────────────


def test_enforce_lets_limit_attempts_through_then_says_429_with_retry_after():
    async def scenario():
        for _ in range(3):
            await auth_limits.enforce("t", "k", 3, 60)
        with pytest.raises(HTTPException) as e:
            await auth_limits.enforce("t", "k", 3, 60)
        assert e.value.status_code == 429 and 1 <= int(e.value.headers["Retry-After"]) <= 61
        await auth_limits.enforce("t", "other-key", 3, 60)              # a different key has its own count
        await auth_limits.enforce("other-bucket", "k", 3, 60)

    run(scenario())


def test_the_window_slides_so_attempts_are_allowed_again_after_it():
    async def scenario():
        await auth_limits.enforce("t", "k", 1, 0.5)
        with pytest.raises(HTTPException):
            await auth_limits.enforce("t", "k", 1, 0.5)
        await asyncio.sleep(0.6)
        await auth_limits.enforce("t", "k", 1, 0.5)

    run(scenario())


def test_parallel_attempts_cannot_all_slip_under_the_limit():
    async def scenario():
        async def one():
            try:
                await auth_limits.enforce("t", "burst", 5, 60)
                return True
            except HTTPException:
                return False

        results = await asyncio.gather(*[one() for _ in range(40)])
        assert sum(results) == 5

    run(scenario())


def test_check_does_not_count_and_record_does():
    async def scenario():
        for _ in range(10):
            await auth_limits.check("t", "k", 2, 60)               # looking never uses an attempt up
        await auth_limits.record("t", "k", 60)
        await auth_limits.check("t", "k", 2, 60)
        await auth_limits.record("t", "k", 60)
        with pytest.raises(HTTPException) as e:
            await auth_limits.check("t", "k", 2, 60)
        assert e.value.status_code == 429

    run(scenario())


def test_the_forwarded_for_header_is_only_trusted_from_the_right_and_only_when_told_to(monkeypatch):
    monkeypatch.setattr(auth_limits.settings, "TRUSTED_PROXY_HOPS", 0)
    assert auth_limits.client_ip(fake_request("6.6.6.6", host="10.0.0.1")) == "10.0.0.1"          # header ignored: nobody can dodge a limit with it
    monkeypatch.setattr(auth_limits.settings, "TRUSTED_PROXY_HOPS", 1)
    assert auth_limits.client_ip(fake_request("6.6.6.6, 203.0.113.9")) == "203.0.113.9"            # the proxy's entry, not the caller's
    assert auth_limits.client_ip(fake_request("1.2.3.4, 5.6.7.8, 203.0.113.9")) == "203.0.113.9"
    assert auth_limits.client_ip(fake_request(None, host="10.0.0.1")) == "10.0.0.1"                # no header: fall back
    monkeypatch.setattr(auth_limits.settings, "TRUSTED_PROXY_HOPS", 2)
    assert auth_limits.client_ip(fake_request("1.2.3.4, 203.0.113.9")) == "1.2.3.4"
    assert auth_limits.client_ip(fake_request("203.0.113.9")) == "10.0.0.1"                         # fewer entries than proxies: do not guess


# ── the reset code ──────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}", poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    run(create())
    maker.engine = engine
    yield maker
    run(engine.dispose())


def add_user(maker, username="pat", email="pat@example.com", password="old-password", otp=None, otp_in=timedelta(minutes=10), attempts=0):
    async def write():
        async with maker() as session:
            user = User(
                username=username, email=email, hashed_password=routes.get_password_hash(password) if password else None,
                reset_otp=otp, reset_otp_expires=datetime.utcnow() + otp_in if otp else None, reset_otp_attempts=attempts,
            )
            session.add(user)
            await session.commit()
            return user.id

    return run(write())


def read_user(maker, username="pat"):
    async def read():
        async with maker() as session:
            return (await session.execute(select(User).where(User.username == username))).scalar_one()

    return run(read())


def verify(maker, otp, username="pat", new="new-password"):
    async def go():
        async with maker() as session:
            return await password_reset.verify_and_reset(session, username, otp, lambda: routes.get_password_hash(new))

    return run(go())


def test_codes_are_six_digits_from_a_secure_source():
    codes = {password_reset.new_otp() for _ in range(200)}
    assert all(re.fullmatch(r"\d{6}", c) for c in codes) and len(codes) > 150
    source = open(password_reset.__file__, encoding="utf-8").read()
    assert "import random" not in source and "secrets.randbelow" in source


def test_the_right_code_changes_the_password_once(db):
    add_user(db, otp="123456")
    assert verify(db, "123456") == (True, "Password reset successful. You can now login with your new password.")
    user = read_user(db)
    assert routes.verify_password("new-password", user.hashed_password) and user.reset_otp is None
    assert verify(db, "123456", new="again")[0] is False                  # the code is burnt: a second use does nothing
    assert routes.verify_password("new-password", read_user(db).hashed_password)


def test_five_wrong_guesses_burn_the_code_even_when_the_right_one_comes_next(db):
    add_user(db, otp="123456")
    answers = [verify(db, f"00000{i}")[1] for i in range(5)]
    assert answers[0] == "Invalid code. 4 attempts remaining." and answers[3] == "Invalid code. 1 attempts remaining."
    assert answers[4] == "Too many failed attempts. Please request a new code."
    assert verify(db, "123456") == (False, password_reset.BAD_CODE)
    assert read_user(db).reset_otp is None and routes.verify_password("old-password", read_user(db).hashed_password)


def test_guesses_sent_at_the_same_moment_still_get_only_five_tries(db):
    add_user(db, otp="123456")

    async def burst():
        async def guess(i):
            async with db() as session:
                return await password_reset.verify_and_reset(session, "pat", f"{i:06d}", lambda: "x")

        return await asyncio.gather(*[guess(i) for i in range(20)])        # none of these is the right code

    answers = run(burst())
    compared = [m for ok, m in answers if m.startswith("Invalid code.") or m.startswith("Too many failed")]
    assert len(compared) == 5, answers                                     # five were checked; the other fifteen were refused without a look
    assert all(m == password_reset.BAD_CODE for ok, m in answers if m not in compared)
    assert read_user(db).reset_otp is None


def test_a_burst_that_includes_the_right_code_cannot_win_more_than_once(db):
    add_user(db, otp="123456")

    async def burst():
        async def go(new):
            async with db() as session:
                return await password_reset.verify_and_reset(session, "pat", "123456", lambda: routes.get_password_hash(new))

        return await asyncio.gather(*[go(f"password-{i}") for i in range(6)])

    assert sum(1 for ok, _ in run(burst()) if ok) == 1


def test_expired_unknown_and_missing_codes_all_look_the_same(db):
    add_user(db, otp="123456", otp_in=timedelta(minutes=-1))
    add_user(db, username="nocode", email="n@example.com", otp=None)
    answers = {verify(db, "123456")[1], verify(db, "123456", username="nobody")[1], verify(db, "123456", username="nocode")[1]}
    assert answers == {password_reset.BAD_CODE}
    assert read_user(db).reset_otp is None                                 # the expired one was cleared


def test_a_second_code_is_not_made_within_a_minute_of_the_first():
    user = User(username="p", reset_otp="111111", reset_otp_expires=datetime.utcnow() + timedelta(minutes=10) - timedelta(seconds=5))
    assert password_reset.made_too_recently(user, datetime.utcnow())
    old = User(username="p", reset_otp="111111", reset_otp_expires=datetime.utcnow() + timedelta(minutes=10) - timedelta(minutes=2))
    assert not password_reset.made_too_recently(old, datetime.utcnow())
    assert not password_reset.made_too_recently(User(username="p"), datetime.utcnow())


# ── the routes, through the real app ────────────────────────────────────────


@pytest.fixture
def site(db, monkeypatch):
    async def override():
        async with db() as session:
            yield session

    app_http.dependency_overrides[get_db] = override
    sent = []

    async def fake_send(to_email, username, otp):
        sent.append((to_email, username, otp))
        return True

    monkeypatch.setattr(email_service, "send_otp_email", fake_send)

    class Site:
        client = TestClient(app_http)
        mails = sent

        def post(self, path, body, ip="198.51.100.7"):
            return self.client.post(f"/api/v1{path}", json=body, headers={"x-forwarded-for": ip})

    yield Site()
    app_http.dependency_overrides.pop(get_db, None)


def login(site, username, password, ip="198.51.100.7"):
    return site.post("/auth/login", {"username": username, "password": password}, ip=ip)


def test_login_still_works_and_a_wrong_password_is_still_a_plain_401(db, site):
    add_user(db, password="right-password")
    assert login(site, "pat", "right-password").status_code == 200
    r = login(site, "pat", "wrong")
    assert r.status_code == 401 and r.json()["detail"] == "Invalid credentials"
    assert login(site, "nobody", "wrong").json()["detail"] == "Invalid credentials"        # an unknown name looks the same


def test_guessing_passwords_for_one_name_from_one_address_is_stopped_after_eight_failures(db, site):
    add_user(db, password="right-password")
    codes = [login(site, "pat", f"guess-{i}").status_code for i in range(8)]
    assert codes == [401] * 8
    blocked = login(site, "pat", "right-password")                       # even the right password is refused for now
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0
    assert login(site, "other", "x", ip="198.51.100.8").status_code == 401     # other names and other addresses are not affected


def test_guessing_for_one_name_from_many_addresses_is_stopped_too(db, site, monkeypatch):
    monkeypatch.setattr(auth_limits.settings, "TRUSTED_PROXY_HOPS", 1)         # so each "ip" below really is a different caller
    add_user(db, password="right-password")
    codes = [login(site, "pat", f"guess-{i}", ip=f"203.0.113.{i}").status_code for i in range(31)]
    assert codes[:30] == [401] * 30 and codes[30] == 429


def test_names_that_do_not_exist_are_throttled_exactly_like_real_ones(db, site):
    codes = [login(site, "ghost", f"guess-{i}").status_code for i in range(9)]
    assert codes == [401] * 8 + [429]


def test_one_address_cannot_try_more_than_sixty_logins_in_ten_minutes(db, site):
    codes = [login(site, f"user{i}", "x").status_code for i in range(61)]
    assert codes[:60] == [401] * 60 and codes[60] == 429


def test_a_caller_cannot_dodge_the_limit_by_inventing_forwarded_for_entries(db, site, monkeypatch):
    monkeypatch.setattr(auth_limits.settings, "TRUSTED_PROXY_HOPS", 1)
    add_user(db, password="right-password")
    codes = [login(site, "pat", f"g{i}", ip=f"{i}.{i}.{i}.{i}, 198.51.100.7").status_code for i in range(9)]       # a new fake caller every time
    assert codes == [401] * 8 + [429]


def test_signing_up_is_limited_per_address(db, site):
    codes = [site.post("/auth/register", {"username": f"new{i}", "password": "secret1"}).status_code for i in range(21)]
    assert codes[:20] == [201] * 20 and codes[20] == 429


def test_asking_for_a_code_gives_the_same_answer_whoever_you_ask_about(db, site):
    add_user(db, username="withmail", email="a@example.com")
    add_user(db, username="nomail", email=None)
    answers = [site.post("/auth/forgot-password-otp", {"username": u}, ip=f"198.51.100.{i}") for i, u in enumerate(["withmail", "nomail", "nobody"])]
    assert [a.status_code for a in answers] == [200, 200, 200]
    assert answers[0].json() == answers[1].json() == answers[2].json() == password_reset.GENERIC_REQUEST_REPLY
    assert [m[0] for m in site.mails] == ["a@example.com"]               # only the real one got a mail
    assert re.fullmatch(r"\d{6}", site.mails[0][2])


def test_the_token_reset_request_does_not_reveal_who_has_an_account_either(db, site, monkeypatch):
    async def fake(to_email, username, reset_token):
        return True

    monkeypatch.setattr(email_service, "send_password_reset_email", fake)
    add_user(db, username="withmail", email="a@example.com")
    a = site.post("/auth/forgot-password", {"username": "withmail"})
    b = site.post("/auth/forgot-password", {"username": "nobody"}, ip="198.51.100.9")
    assert a.status_code == b.status_code == 200 and a.json() == b.json()


def test_a_name_can_only_ask_for_three_codes_an_hour_and_a_new_code_does_not_reset_the_tries(db, site):
    add_user(db, otp=None)
    ok = [site.post("/auth/forgot-password-otp", {"username": "pat"}, ip=f"198.51.100.{i}").status_code for i in range(3)]
    assert ok == [200, 200, 200] and len(site.mails) == 1                 # the 2nd and 3rd came within a minute: no new code was made
    blocked = site.post("/auth/forgot-password-otp", {"username": "pat"}, ip="198.51.100.77")
    assert blocked.status_code == 429


def test_the_whole_reset_works_through_the_routes_and_wrong_codes_are_limited(db, site):
    add_user(db)
    site.post("/auth/forgot-password-otp", {"username": "pat"})
    code = site.mails[0][2]
    wrong = "000000" if code != "000000" else "000001"
    for i in range(4):
        r = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": wrong, "new_password": "brand-new1"}, ip=f"198.51.100.{i}")
        assert r.status_code == 400 and r.json()["detail"] == f"Invalid code. {4 - i} attempts remaining."
    ok = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": code, "new_password": "brand-new1"}, ip="198.51.100.50")
    assert ok.status_code == 200 and ok.json()["success"] is True
    assert login(site, "pat", "brand-new1").status_code == 200


def test_trying_codes_for_one_name_is_limited_to_ten_an_hour(db, site):
    add_user(db)
    codes = [
        site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": "123456", "new_password": "brand-new1"}, ip=f"198.51.100.{i}").status_code
        for i in range(11)
    ]
    assert codes[:10] == [400] * 10 and codes[10] == 429
