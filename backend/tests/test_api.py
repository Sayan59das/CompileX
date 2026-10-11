"""
CodeArena API smoke tests.
Run with: python tests/test_api.py
"""
import json, time
import requests

BASE = "http://127.0.0.1:8000"
RUN_ID = str(int(time.time()))[-5:]


def post(path, data, token=None):
    headers = {"Content-Type": "application/json", "Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(BASE + path, json=data, headers=headers, timeout=15)
    try:
        return r.json(), r.status_code
    except Exception:
        return {"raw": r.text}, r.status_code


def get(path, token=None):
    headers = {"Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(BASE + path, headers=headers, timeout=15)
    try:
        return r.json(), r.status_code
    except Exception:
        return {"raw": r.text}, r.status_code


def check(label, status, expected_status):
    ok = status == expected_status
    icon = "✓" if ok else "✗"
    print(f"  {icon} [{status}] {label}")
    if not ok:
        raise SystemExit(f"FAILED: {label} — expected {expected_status}, got {status}")
    return ok


print("\n=== CodeArena API Smoke Tests ===\n")

# 1. Health
r, s = get("/health")
check("GET /health", s, 200)
assert r["status"] == "healthy"

# 2. Register
r, s = post("/api/v1/auth/register", {
    "username": f"smokeuser_{RUN_ID}",
    "email": f"smoke_{RUN_ID}@test.com",
    "password": "password123",
})
check("POST /auth/register", s, 201)
assert r["username"] == f"smokeuser_{RUN_ID}"

# 3. Duplicate register → 400
r, s = post("/api/v1/auth/register", {
    "username": f"smokeuser_{RUN_ID}",
    "email": f"smoke_{RUN_ID}@test.com",
    "password": "password123",
})
check("POST /auth/register (duplicate)", s, 400)

# 4. Login
r, s = post("/api/v1/auth/login", {"username": f"smokeuser_{RUN_ID}", "password": "password123"})
check("POST /auth/login", s, 200)
assert "access_token" in r
token = r["access_token"]

# 5. Bad login → 401
r, s = post("/api/v1/auth/login", {"username": f"smokeuser_{RUN_ID}", "password": "wrong"})
check("POST /auth/login (bad creds)", s, 401)

# 6. Create lobby (requires auth)
r, s = post("/api/v1/lobbies", {"name": "Smoke Lobby", "max_players": 4, "time_limit": 900}, token)
check("POST /lobbies", s, 201)
assert r["code"]
lobby_code = r["code"]
lobby_id = r["id"]

# 7. Create lobby without auth → 401
r, s = post("/api/v1/lobbies", {"name": "No Auth Lobby", "max_players": 4, "time_limit": 900})
check("POST /lobbies (no auth)", s, 401)

# 8. Get lobby by code
r, s = get(f"/api/v1/lobbies/{lobby_code}")
check("GET /lobbies/{code}", s, 200)
assert r["id"] == lobby_id

# 9. Get non-existent lobby → 404
r, s = get("/api/v1/lobbies/XXXXXX")
check("GET /lobbies/XXXXXX (not found)", s, 404)

# 10. Join lobby
r, s = post(f"/api/v1/lobbies/{lobby_id}/join", {}, token)
check("POST /lobbies/{id}/join", s, 200)
assert "player_id" in r

# 11. Leaderboard
r, s = get(f"/api/v1/lobbies/{lobby_id}/leaderboard")
check("GET /lobbies/{id}/leaderboard", s, 200)
assert "leaderboard" in r

# 12. Submit code with bad question_id → 404
r, s = post("/api/v1/submissions", {
    "code": "print(1)", "language": "python", "question_id": 999,
}, token)
check("POST /submissions (bad question_id)", s, 404)

print("\n=== All tests passed ===\n")
