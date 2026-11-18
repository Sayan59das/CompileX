"""The password-reset email, sent for real over SMTP to a mailbox the test runs, and the whole reset done with what arrives in it.

The mail server below speaks what Gmail speaks to this app: it greets, offers STARTTLS (with a self-signed certificate), only accepts a login
after the connection is encrypted, checks the user name and password, then takes the message. Nothing leaves the machine: it listens on 127.0.0.1.
So this exercises the real email_service (smtplib, the message it builds) and the real routes, not a stand-in for either.

Run from the backend folder:  python -m pytest tests/test_reset_email_delivery.py -q
"""

import asyncio
import base64
import email as email_lib
import email.policy
import os
import re
import ssl
import sys
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from app.api.v1 import routes
from app.db.database import get_db
from app.main import app_http
from app.services import email_service as email_module
from app.services import shared_state as ss
from test_auth_security import add_user, db, fresh_limits, read_user, run, login      # noqa: F401  (the throwaway database, a clean limiter, helpers)

SMTP_USER, SMTP_PASSWORD = "mailer@example.com", "an-app-password"


class MiniSMTP:
    """A small SMTP server on 127.0.0.1 that requires STARTTLS and AUTH before it accepts a message."""

    def __init__(self, certfile, keyfile):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile, keyfile)
        self.messages = []          # {"from", "to", "data", "tls", "user"}
        self.refused_logins = 0
        self.plain_auth_attempts = 0
        self.port = None

    def start(self):
        ready = threading.Event()

        def serve():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.server = self.loop.run_until_complete(asyncio.start_server(self._client, "127.0.0.1", 0))
            self.port = self.server.sockets[0].getsockname()[1]
            ready.set()
            self.loop.run_forever()

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()
        assert ready.wait(5)

    def stop(self):
        self.loop.call_soon_threadsafe(self.server.close)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)

    async def _client(self, reader, writer):
        async def say(line):
            writer.write((line + "\r\n").encode())
            await writer.drain()

        tls, user, sender, recipients = False, None, None, []
        try:
            await say("220 mini ESMTP ready")
            while True:
                raw = await reader.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").rstrip("\r\n")
                word = line.upper()
                if word.startswith(("EHLO", "HELO")):
                    await say("250-mini")
                    await say("250-AUTH PLAIN LOGIN" if tls else "250-STARTTLS")
                    await say("250 8BITMIME")
                elif word == "STARTTLS":
                    await say("220 go ahead")
                    await writer.start_tls(self.context)
                    tls = True
                elif word.startswith("AUTH PLAIN"):
                    if not tls:
                        self.plain_auth_attempts += 1
                        await say("530 5.7.0 Must issue a STARTTLS command first")
                        continue
                    parts = line.split()
                    blob = parts[2] if len(parts) > 2 else None
                    _, name, password = base64.b64decode(blob).split(b"\0")
                    if (name.decode(), password.decode()) == (SMTP_USER, SMTP_PASSWORD):
                        user = name.decode()
                        await say("235 2.7.0 Accepted")
                    else:
                        self.refused_logins += 1
                        await say("535 5.7.8 Username and Password not accepted")
                elif word.startswith("MAIL FROM"):
                    if not user:
                        await say("530 5.7.0 Authentication required")
                        continue
                    sender, recipients = re.search(r"<([^>]*)>", line).group(1), []
                    await say("250 OK")
                elif word.startswith("RCPT TO"):
                    recipients.append(re.search(r"<([^>]*)>", line).group(1))
                    await say("250 OK")
                elif word == "DATA":
                    await say("354 End data with <CR><LF>.<CR><LF>")
                    body = []
                    while True:
                        chunk = await reader.readline()
                        if chunk == b".\r\n":
                            break
                        body.append(chunk[1:] if chunk.startswith(b"..") else chunk)
                    self.messages.append({"from": sender, "to": list(recipients), "data": b"".join(body), "tls": tls, "user": user})
                    await say("250 2.0.0 OK queued")
                elif word == "QUIT":
                    await say("221 bye")
                    break
                else:
                    await say("250 OK")
        except (ConnectionError, ssl.SSLError):
            pass
        finally:
            writer.close()

    def parsed(self, index=-1):
        return email_lib.message_from_bytes(self.messages[index]["data"], policy=email.policy.default)


@pytest.fixture
def mailbox(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(days=1)).not_valid_after(datetime.utcnow() + timedelta(days=1)).sign(key, hashes.SHA256())
    )
    certfile, keyfile = tmp_path / "cert.pem", tmp_path / "key.pem"
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    server = MiniSMTP(str(certfile), str(keyfile))
    server.start()
    yield server
    server.stop()


@pytest.fixture
def site(db, mailbox, monkeypatch):
    service = email_module.email_service
    for attribute, value in (
        ("smtp_host", "127.0.0.1"), ("smtp_port", mailbox.port), ("smtp_user", SMTP_USER), ("smtp_password", SMTP_PASSWORD),
        ("from_email", SMTP_USER), ("from_name", "CompileX"),
    ):
        monkeypatch.setattr(service, attribute, value)
    monkeypatch.setattr(email_module.settings, "FRONTEND_URL", "https://app.example.com")

    async def override():
        async with db() as session:
            yield session

    app_http.dependency_overrides[get_db] = override

    class Site:
        client = TestClient(app_http)
        box = mailbox

        def post(self, path, body, ip="198.51.100.7"):
            return self.client.post(f"/api/v1{path}", json=body, headers={"x-forwarded-for": ip})

        def ask_for_code(self, username="pat", ip="198.51.100.7"):
            return self.post("/auth/forgot-password-otp", {"username": username}, ip=ip)

    yield Site()
    app_http.dependency_overrides.pop(get_db, None)


def code_in(message):
    """The six-digit code in the plain-text part of a mail."""
    text = message.get_body(preferencelist=("plain",)).get_content()
    found = re.findall(r"(?<!\d)\d{6}(?!\d)", text)
    assert len(found) == 1, text
    return found[0]


# ── the mail itself ─────────────────────────────────────────────────────────


def test_the_code_email_is_delivered_encrypted_to_the_right_person_with_the_right_content(db, site):
    add_user(db, username="pat", email="pat@example.com")
    assert site.ask_for_code().json()["success"] is True

    (sent,) = site.box.messages
    assert sent["tls"] is True and sent["user"] == SMTP_USER and sent["from"] == SMTP_USER and sent["to"] == ["pat@example.com"]
    assert site.box.plain_auth_attempts == 0                                   # it never tried to log in before encrypting the connection

    message = site.box.parsed()
    assert message["Subject"] == "Your CompileX Password Reset Code" and message["To"] == "pat@example.com"
    assert message["From"] == f"CompileX <{SMTP_USER}>" and message.get_content_type() == "multipart/alternative"
    text = message.get_body(preferencelist=("plain",)).get_content()
    page = message.get_body(preferencelist=("html",)).get_content()

    code = code_in(message)
    assert read_user(db).reset_otp == code                                      # the mailed code is the stored code
    assert code in page and "pat" in text and "pat" in page and "10 minutes" in text
    assert "hashed_password" not in text + page and read_user(db).hashed_password not in text + page


def test_the_whole_reset_works_with_the_code_from_the_email(db, site):
    add_user(db, username="pat", email="pat@example.com", password="old-password")
    site.ask_for_code()
    code = code_in(site.box.parsed())
    wrong = "000000" if code != "000000" else "000001"

    bad = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": wrong, "new_password": "brand-new-pass"})
    assert bad.status_code == 400 and bad.json()["detail"] == "Invalid code. 4 attempts remaining."

    good = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": code, "new_password": "brand-new-pass"})
    assert good.status_code == 200 and good.json()["success"] is True

    assert login(site, "pat", "brand-new-pass").status_code == 200
    assert login(site, "pat", "old-password").status_code == 401
    again = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": code, "new_password": "another-pass"})
    assert again.status_code == 400                                              # the code worked once


def test_asking_twice_within_a_minute_sends_one_mail_and_the_first_code_still_works(db, site):
    add_user(db, username="pat", email="pat@example.com")
    first, second = site.ask_for_code(), site.ask_for_code(ip="198.51.100.8")
    assert first.json() == second.json() and len(site.box.messages) == 1
    ok = site.post("/auth/verify-otp-reset-password", {"username": "pat", "otp": code_in(site.box.parsed()), "new_password": "brand-new-pass"})
    assert ok.status_code == 200


def test_nothing_is_mailed_for_unknown_names_or_accounts_without_an_email(db, site):
    add_user(db, username="noemail", email=None)
    answers = [site.ask_for_code("ghost", ip="198.51.100.1"), site.ask_for_code("noemail", ip="198.51.100.2")]
    assert [a.status_code for a in answers] == [200, 200] and answers[0].json() == answers[1].json() and site.box.messages == []


# ── when sending fails ──────────────────────────────────────────────────────


def test_when_the_mail_server_refuses_the_login_the_player_is_told_and_no_code_is_left_behind(db, site, monkeypatch):
    add_user(db, username="pat", email="pat@example.com")
    monkeypatch.setattr(email_module.email_service, "smtp_password", "the-wrong-password")
    failed = site.ask_for_code()
    assert failed.status_code == 500 and failed.json()["detail"] == "Failed to send OTP email. Please try again later."
    assert site.box.refused_logins == 1 and site.box.messages == []
    assert read_user(db).reset_otp is None                                       # a code nobody received must not stay behind

    monkeypatch.setattr(email_module.email_service, "smtp_password", SMTP_PASSWORD)    # the owner fixes the setting; the player tries again at once
    retry = site.ask_for_code(ip="198.51.100.9")
    assert retry.status_code == 200 and len(site.box.messages) == 1 and code_in(site.box.parsed()) == read_user(db).reset_otp


def test_when_the_mail_server_is_down_the_player_is_told_and_no_code_is_left_behind(db, site, monkeypatch):
    add_user(db, username="pat", email="pat@example.com")
    site.box.stop()
    failed = site.ask_for_code()
    assert failed.status_code == 500 and read_user(db).reset_otp is None


def test_when_email_is_not_configured_at_all_the_player_is_told(db, site, monkeypatch):
    add_user(db, username="pat", email="pat@example.com")
    monkeypatch.setattr(email_module.email_service, "smtp_user", "")
    assert site.ask_for_code().status_code == 500 and read_user(db).reset_otp is None


# ── what a stranger can put into someone else's mail ────────────────────────


def test_a_username_cannot_inject_html_into_the_email_a_victim_receives(db, site):
    evil = 'x<a href="https://evil.example/login">Log in</a>'
    add_user(db, username=evil, email="victim@example.com")
    site.ask_for_code(evil)
    page = site.box.parsed().get_body(preferencelist=("html",)).get_content()
    assert 'href="https://evil.example' not in page and "&lt;a href=" in page
    assert evil in site.box.parsed().get_body(preferencelist=("plain",)).get_content()      # plain text shows it as text, which is harmless


def test_an_address_with_a_line_break_is_never_mailed_and_cannot_add_recipients(db, site):
    add_user(db, username="sneaky", email="a@example.com\r\nBcc: victim@example.com")
    failed = site.ask_for_code("sneaky")
    assert failed.status_code == 500 and site.box.messages == []


def test_sign_up_refuses_things_that_are_not_email_addresses(db, site):
    bad = ["a@example.com\r\nBcc: v@example.com", "no-at-sign.example.com", "two@@example.com", "spaces in@example.com", "<b>@x.com", "a@b", 'q"uote@x.com']
    for i, address in enumerate(bad):
        r = site.post("/auth/register", {"username": f"user{i}", "password": "secret1", "email": address}, ip=f"198.51.100.{i + 20}")
        assert r.status_code == 422, address
    ok = site.post("/auth/register", {"username": "fine", "password": "secret1", "email": "  Fine.Person+tag@Example.co.uk "}, ip="198.51.100.60")
    assert ok.status_code == 201 and ok.json()["email"] == "Fine.Person+tag@Example.co.uk"
    nomail = site.post("/auth/register", {"username": "plain", "password": "secret1"}, ip="198.51.100.61")
    assert nomail.status_code == 201 and nomail.json()["email"] is None


# ── the other reset mail (the link) ─────────────────────────────────────────


def test_the_link_email_is_delivered_and_its_link_resets_the_password(db, site):
    add_user(db, username="pat", email="pat@example.com", password="old-password")
    assert site.post("/auth/forgot-password", {"username": "pat"}).status_code == 200
    (sent,) = site.box.messages
    assert sent["tls"] is True and sent["to"] == ["pat@example.com"]
    message = site.box.parsed()
    assert message["Subject"] == "Reset Your CompileX Password"
    link = re.search(r"https://app\.example\.com/reset-password\?token=([\w-]+)", message.get_body(preferencelist=("plain",)).get_content())
    assert link, "the mail has no reset link"
    ok = site.post("/auth/reset-password", {"reset_token": link.group(1), "new_password": "brand-new-pass"})
    assert ok.status_code == 200 and login(site, "pat", "brand-new-pass").status_code == 200
    reused = site.post("/auth/reset-password", {"reset_token": link.group(1), "new_password": "again-again"})
    assert reused.status_code == 400
