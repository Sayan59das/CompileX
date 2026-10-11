"""
WebSocket / Socket.IO tests.
Run with: python tests/test_websocket.py
"""
import asyncio, time
import requests
import socketio

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


def check(label, ok, detail=""):
    icon = "✓" if ok else "✗"
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""), flush=True)
    if not ok:
        raise SystemExit(f"FAILED: {label}")


def register_and_login(username, email, password):
    post("/api/v1/auth/register", {"username": username, "email": email, "password": password})
    r, _ = post("/api/v1/auth/login", {"username": username, "password": password})
    return r["access_token"]


print("\n=== WebSocket / Socket.IO Tests ===\n", flush=True)

token1 = register_and_login(f"ws_host_{RUN_ID}", f"wshost_{RUN_ID}@test.com", "password123")
token2 = register_and_login(f"ws_guest_{RUN_ID}", f"wsguest_{RUN_ID}@test.com", "password123")

r, s = post("/api/v1/lobbies", {"name": "WS Test Lobby", "max_players": 4, "time_limit": 600}, token1)
check("Create lobby", s == 201)
lobby_id = r["id"]
print(f"      lobby_id={lobby_id} code={r['code']}", flush=True)

r1, s1 = post(f"/api/v1/lobbies/{lobby_id}/join", {}, token1)
r2, s2 = post(f"/api/v1/lobbies/{lobby_id}/join", {}, token2)
check("Host joins lobby (HTTP)", s1 == 200)
check("Guest joins lobby (HTTP)", s2 == 200)
player1_id = r1["player_id"]
player2_id = r2["player_id"]


async def main():
    sio1 = socketio.AsyncSimpleClient()
    sio2 = socketio.AsyncSimpleClient()

    await sio1.connect(BASE, wait_timeout=5)
    await sio2.connect(BASE, wait_timeout=5)
    check("Host connected", sio1.connected)
    check("Guest connected", sio2.connected)

    await sio1.emit("join_lobby", {
        "lobby_id": lobby_id, "player_id": player1_id,
        "user_id": player1_id, "username": f"ws_host_{RUN_ID}",
    })
    e = await sio1.receive(timeout=3)
    check("Host receives lobby_state", e[0] == "lobby_state", e[0])

    await sio2.emit("join_lobby", {
        "lobby_id": lobby_id, "player_id": player2_id,
        "user_id": player2_id, "username": f"ws_guest_{RUN_ID}",
    })
    e = await sio2.receive(timeout=3)
    check("Guest receives lobby_state", e[0] == "lobby_state", e[0])
    e = await sio1.receive(timeout=3)
    check("Host receives player_joined", e[0] == "player_joined", e[0])

    await sio1.emit("start_game", {"lobby_id": lobby_id})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Host receives game_started",  e1[0] == "game_started", e1[0])
    check("Guest receives game_started", e2[0] == "game_started", e2[0])

    await sio1.emit("score_update", {"lobby_id": lobby_id, "player_id": player1_id, "score": 120})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Host receives leaderboard_update",  e1[0] == "leaderboard_update", e1[0])
    check("Guest receives leaderboard_update", e2[0] == "leaderboard_update", e2[0])
    lb = e1[1]["leaderboard"]
    check("Leaderboard has 2 players",       len(lb) == 2,          str(len(lb)))
    check("Host is rank 1 with score 120",   lb[0]["score"] == 120, str(lb[0]))

    await sio1.emit("end_game", {"lobby_id": lobby_id})
    e1 = await sio1.receive(timeout=3)
    e2 = await sio2.receive(timeout=3)
    check("Host receives game_ended",  e1[0] == "game_ended", e1[0])
    check("Guest receives game_ended", e2[0] == "game_ended", e2[0])

    await sio1.disconnect()
    await sio2.disconnect()
    print("\n=== All WebSocket tests passed ===\n", flush=True)


asyncio.run(main())
