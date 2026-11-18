"""Sign in with Google / GitHub can no longer take over a password account (security review, problem 2).

Before: signing up with someone's email address (never checked) and then having them use "Sign in with Google" handed them YOUR account; the
address a provider reported was trusted even when the provider had not verified it; the OAuth `state` was the constant provider name.

Run from the backend folder:  python -m pytest tests/test_oauth_security.py -q
"""

import asyncio
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.v1 import routes
from app.db.database import Base, get_db
from app.main import app_http
from app.models.models import User
from app.services import oauth_service as oauth_module

STATE = "a-random-state-value-from-this-browser"


# ── what a provider's answer is worth ───────────────────────────────────────


def provider_answers(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def google(verified):
    return lambda req: httpx.Response(200, json={"id": "g1", "email": "pat@example.com", "verified_email": verified, "name": "Pat"})


@pytest.mark.parametrize("verified,expected", [(True, "pat@example.com"), (False, None), ("true", None), (None, None)])
def test_google_email_counts_only_when_google_verified_it(monkeypatch, verified, expected):
    provider_answers(monkeypatch, google(verified) if verified is not None else lambda r: httpx.Response(200, json={"id": "g1", "email": "pat@example.com"}))
    info = asyncio.run(oauth_module.oauth_service._get_google_user_info("t"))
    assert info["email"] == expected


@pytest.mark.parametrize("emails,expected", [
    ([{"email": "a@x.com", "primary": True, "verified": True}], "a@x.com"),
    ([{"email": "a@x.com", "primary": True, "verified": False}], None),                                  # unverified primary
    ([{"email": "a@x.com", "primary": False, "verified": True}], None),                                  # verified, but not the primary one
    ([{"email": "a@x.com", "primary": False, "verified": False}], None),                                 # the old "first in the list" fallback
    ([{"email": "u@x.com", "primary": False, "verified": False}, {"email": "p@x.com", "primary": True, "verified": True}], "p@x.com"),
    ([], None),
    ([{"email": "a@x.com", "primary": True}], None),                                                     # no verified flag at all
])
def test_github_email_counts_only_when_it_is_the_primary_and_verified(monkeypatch, emails, expected):
    def answer(req):
        if str(req.url).endswith("/user/emails"):
            return httpx.Response(200, json=emails)
        return httpx.Response(200, json={"id": 7, "login": "pat", "avatar_url": None})

    provider_answers(monkeypatch, answer)
    assert asyncio.run(oauth_module.oauth_service._get_github_user_info("t"))["email"] == expected


# ── the callback, against a real (throwaway) database ───────────────────────


@pytest.fixture
def site(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'oauth.db'}", poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create())

    async def override():
        async with maker() as db:
            yield db

    app_http.dependency_overrides[get_db] = override
    monkeypatch.setattr(routes.settings, "FRONTEND_URL", "https://app.example.com")
    monkeypatch.setattr(routes.settings, "GOOGLE_CLIENT_ID", "client-id")

    profile = {"provider_id": "g-1", "email": "pat@example.com", "name": "Pat", "picture": None}
    svc = oauth_module.oauth_service
    monkeypatch.setattr(svc, "is_provider_configured", lambda provider: True)

    async def exchange(provider, code, redirect_uri):
        return "access"

    async def info(provider, access_token):
        return dict(profile)

    monkeypatch.setattr(svc, "exchange_code_for_token", exchange)
    monkeypatch.setattr(svc, "get_user_info", info)

    class Site:
        client = TestClient(app_http)
        profile_info = profile

        def callback(self, state=STATE, cookie=STATE, **params):
            query = {"code": "abc", "state": state, **params}
            query = {k: v for k, v in query.items() if v is not None}
            headers = {"cookie": f"oauth_state={cookie}"} if cookie else {}
            return self.client.get(f"/api/v1/auth/google/callback?{urllib.parse.urlencode(query)}", headers=headers, follow_redirects=False)

        def users(self):
            async def read():
                async with maker() as db:
                    return list((await db.execute(select(User))).scalars())

            return asyncio.run(read())

        def add_user(self, **fields):
            async def write():
                async with maker() as db:
                    db.add(User(**fields))
                    await db.commit()

            asyncio.run(write())

    yield Site()
    app_http.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())


def where(response):
    return urllib.parse.urlsplit(response.headers["location"])


def query(response):
    return urllib.parse.parse_qs(where(response).query)


def test_a_new_person_is_signed_up_and_gets_a_token(site):
    r = site.callback()
    assert r.status_code in (302, 307) and where(r).netloc == "app.example.com"
    q = query(r)
    assert q["oauth_success"] == ["true"] and q["username"] == ["pat"] and q["token"][0].count(".") == 2
    assert [(u.username, u.email, u.oauth_provider, u.hashed_password) for u in site.users()] == [("pat", "pat@example.com", "google", None)]


def test_an_existing_password_account_is_not_taken_over_by_a_provider_login_with_the_same_email(site):
    site.add_user(username="attacker", email="pat@example.com", hashed_password="a-bcrypt-hash-the-attacker-knows")
    r = site.callback()
    assert query(r) == {"oauth_error": ["email_in_use"]}
    (user,) = site.users()
    assert user.oauth_provider is None and user.oauth_provider_id is None and user.hashed_password == "a-bcrypt-hash-the-attacker-knows"


def test_an_account_that_came_from_a_provider_is_still_linked_by_email_to_another_provider(site):
    site.add_user(username="pat", email="pat@example.com", hashed_password=None, oauth_provider="github", oauth_provider_id="gh-9")
    r = site.callback()
    assert query(r)["oauth_success"] == ["true"] and query(r)["username"] == ["pat"]
    (user,) = site.users()
    assert (user.oauth_provider, user.oauth_provider_id) == ("google", "g-1")


def test_a_returning_provider_user_signs_in_to_the_same_account(site):
    site.add_user(username="pat", email="pat@example.com", hashed_password=None, oauth_provider="google", oauth_provider_id="g-1")
    assert query(site.callback())["oauth_success"] == ["true"] and len(site.users()) == 1


def test_a_provider_user_with_a_changed_email_still_matches_by_provider_id(site):
    site.add_user(username="pat", email="old@example.com", hashed_password=None, oauth_provider="google", oauth_provider_id="g-1")
    assert query(site.callback())["username"] == ["pat"] and len(site.users()) == 1


@pytest.mark.parametrize("state,cookie", [(STATE, None), (None, STATE), ("one", "two"), (STATE, "")], ids=["no-cookie", "no-state", "mismatch", "empty-cookie"])
def test_a_callback_without_the_matching_state_cookie_is_refused_and_creates_nothing(site, state, cookie):
    r = site.callback(state=state, cookie=cookie)
    assert query(r) == {"oauth_error": ["invalid_state"]} and site.users() == []


def test_the_state_cookie_is_cleared_after_every_attempt(site):
    for r in (site.callback(), site.callback(state="wrong", cookie="other")):
        assert "oauth_state=" in r.headers["set-cookie"] and ("Max-Age=0" in r.headers["set-cookie"] or "expires" in r.headers["set-cookie"].lower())


def test_what_the_provider_sends_back_cannot_add_parameters_to_the_redirect(site):
    r = site.callback(error="x&token=stolen&oauth_success=true")
    assert query(r) == {"oauth_error": ["x&token=stolen&oauth_success=true"]}            # one parameter, its value intact
    assert "&token=stolen" not in where(r).query


def test_a_provider_address_that_is_not_verified_signs_nobody_in(site):
    site.profile_info["email"] = None                    # what oauth_service now returns for an unverified address
    assert query(site.callback()) == {"oauth_error": ["no_email"]} and site.users() == []


def test_the_start_of_a_sign_in_gives_each_browser_its_own_random_state_in_a_cookie(site):
    first = site.client.get("/api/v1/auth/google", follow_redirects=False)
    second = site.client.get("/api/v1/auth/google", follow_redirects=False)
    states = [urllib.parse.parse_qs(urllib.parse.urlsplit(r.headers["location"]).query)["state"][0] for r in (first, second)]
    assert states[0] != states[1] and all(len(s) >= 24 and s != "google" for s in states)
    for r, state in zip((first, second), states):
        cookie = r.headers["set-cookie"]
        assert f"oauth_state={state}" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api/v1/auth" in cookie
