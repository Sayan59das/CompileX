"""
Master test runner.
"""
import sys, io, json, time, asyncio
import socketio
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from http_client import http_post, http_get

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0

def check(label, ok, detail=""):
    global PASS, FAIL
    icon = "PASS" if ok else "FAIL"
    msg = f"  [{icon}] {label}" + (f"  ({detail})" if detail else "")
    print(msg)
    if ok:
        PASS += 1
    else:
        FAIL += 1

def post(path, data, token=None):
    return http_post(BASE, path, data, token)

def get(path, token=None):
    return http_get(BASE, path, token)

RUN_ID = str(int(time.time()))[-6:]

# ===========================================================================
print("=" * 60)
print("  SUITE 1: REST API")
print("=" * 60)

r, s = get("/health")
check("GET /health", s == 200 and r.get("status") == "healthy")

r, s = post("/api/v1/auth/register", {
    "username": f"u_{RUN_ID}", "email": f"u_{RUN_ID}@t.com", "password": "pass1234"
})
check("POST /auth/register", s == 201, f"id={r.get('id')}")

r, s = post("/api/v1/auth/register", {
    "username": f"u_{RUN_ID}", "email": f"u_{RUN_ID}@t.com", "password": "pass1234"
})
check("POST /auth/register duplicate -> 400", s == 400)

r, s = post("/api/v1/auth/login", {"username": f"u_{RUN_ID}", "password": "pass1234"})
check("POST /auth/login", s == 200, "token received" if "access_token" in r else str(r))
token = r.get("access_token", "")

r, s = post("/api/v1/auth/login", {"username": f"u_{RUN_ID}", "password": "wrong"})
check("POST /auth/login bad creds -> 401", s == 401)

r, s = post("/api/v1/lobbies", {"name": "Lobby1", "max_players": 4, "time_limit": 600}, token)
check("POST /lobbies (auth)", s == 201, f"code={r.get('code')}")
lobby_id = r.get("id")
lobby_code = r.get("code")

r, s = post("/api/v1/lobbies", {"name": "Lobby2", "max_players": 4, "time_limit": 600})
check("POST /lobbies (no auth) -> 401", s == 401)

r, s = get(f"/api/v1/lobbies/{lobby_code}")
check("GET /lobbies/{code}", s == 200, f"id={r.get('id')}")

r, s = get("/api/v1/lobbies/ZZZZZZ")
check("GET /lobbies/ZZZZZZ -> 404", s == 404)

r, s = post(f"/api/v1/lobbies/{lobby_id}/join", {}, token)
check("POST /lobbies/{id}/join", s == 200, f"player_id={r.get('player_id')}")
player_id = r.get("player_id")

r, s = get(f"/api/v1/lobbies/{lobby_id}/leaderboard")
check("GET /lobbies/{id}/leaderboard", s == 200)

r, s = post("/api/v1/submissions", {"code": "x", "language": "python", "question_id": 9999}, token)
check("POST /submissions bad question -> 404", s == 404)

# ===========================================================================
print()
print("=" * 60)
print("  SUITE 2: CODE EXECUTION")
print("=" * 60)

test_cases = json.dumps([
    {"input": "1 2",   "output": "3"},
    {"input": "10 20", "output": "30"},
    {"input": "-5 5",  "output": "0"},
])
r, s = post("/api/v1/questions", {
    "title": "Add Two Numbers", "description": "Print sum of two ints.",
    "difficulty": "easy", "topic": "math",
    "starter_code": "pass", "base_points": 100, "time_bonus": 50,
    "max_execution_time_ms": 3000, "test_cases": test_cases,
}, token)
check("POST /questions", s == 201, f"id={r.get('id')}")
qid = r.get("id")

correct = "a, b = map(int, input().split())\nprint(a + b)"
r, s = post("/api/v1/submissions", {"code": correct, "language": "python", "question_id": qid}, token)
check("Submit correct Python -> passed 3/3", s == 201 and r.get("passed_tests") == 3,
      f"passed={r.get('passed_tests')} score={r.get('score')}")

wrong = "print(999)"
r, s = post("/api/v1/submissions", {"code": wrong, "language": "python", "question_id": qid}, token)
check("Submit wrong Python -> passed 0/3", s == 201 and r.get("passed_tests") == 0,
      f"passed={r.get('passed_tests')} score={r.get('score')}")

# ===========================================================================
print()
print("=" * 60)
print("  SUITE 3: WEBSOCKET / SOCKET.IO")
print("=" * 60)

r2, s2 = post("/api/v1/auth/register", {"username": f"g_{RUN_ID}", "email": f"g_{RUN_ID}@t.com", "password": "pass1234"})
r2, _ = post("/api/v1/auth/login", {"username": f"g_{RUN_ID}", "password": "pass1234"})
token_g = r2["access_token"]

r, s = post("/api/v1/lobbies", {"name": "WS Lobby", "max_players": 4, "time_limit": 600}, token)
ws_lobby_id = r["id"]
ws_lobby_code = r["code"]
print(f"  lobby_id={ws_lobby_id} code={ws_lobby_code}")

rh, _ = post(f"/api/v1/lobbies/{ws_lobby_id}/join", {}, token)
rg, _ = post(f"/api/v1/lobbies/{ws_lobby_id}/join", {}, token_g)
pid_h = rh["player_id"]
pid_g = rg["player_id"]

async def ws_tests():
    sio1 = socketio.AsyncSimpleClient()
    sio2 = socketio.AsyncSimpleClient()

    await sio1.connect(BASE, wait_timeout=5)
    await sio2.connect(BASE, wait_timeout=5)
    check("Host connected", sio1.connected)
    check("Guest connected", sio2.connected)

    await sio1.emit("join_lobby", {"lobby_id": ws_lobby_id, "player_id": pid_h,
                                   "user_id": pid_h, "username": f"u_{RUN_ID}"})
    e = await sio1.receive(timeout=3)
    check("Host receives lobby_state", e[0] == "lobby_state", e[0])

    await sio2.emit("join_lobby", {"lobby_id": ws_lobby_id, "player_id": pid_g,
                                   "user_id": pid_g, "username": f"g_{RUN_ID}"})
    e = await sio2.receive(timeout=3)
    check("Guest receives lobby_state", e[0] == "lobby_state", e[0])
    e = await sio1.receive(timeout=3)
    check("Host receives player_joined", e[0] == "player_joined", e[0])

    await sio1.emit("start_game", {"lobby_id": ws_lobby_id})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Both receive game_started",
          e1[0] == "game_started" and e2[0] == "game_started", f"{e1[0]}, {e2[0]}")

    await sio1.emit("score_update", {"lobby_id": ws_lobby_id, "player_id": pid_h, "score": 150})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Both receive leaderboard_update",
          e1[0] == "leaderboard_update" and e2[0] == "leaderboard_update", f"{e1[0]}, {e2[0]}")
    lb = e1[1]["leaderboard"]
    check("Leaderboard: 2 players, host rank 1 score 150",
          len(lb) == 2 and lb[0]["score"] == 150, str(lb[0]))

    await sio1.emit("end_game", {"lobby_id": ws_lobby_id})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Both receive game_ended",
          e1[0] == "game_ended" and e2[0] == "game_ended", f"{e1[0]}, {e2[0]}")

    await sio1.disconnect()
    await sio2.disconnect()

asyncio.run(ws_tests())

# ===========================================================================
print()
print("=" * 60)
total = PASS + FAIL
print(f"  RESULTS: {PASS}/{total} passed  |  {FAIL} failed")
print("=" * 60)

if FAIL > 0:
    sys.exit(1)
