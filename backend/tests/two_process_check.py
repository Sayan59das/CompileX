"""Two backend processes, one game (Phase 1 of docs/scaling-plan.md).

Starts two real uvicorn processes that share one Redis and one database, plays a lobby across them, kills the process one player was connected to,
and carries on through the other. It is a script, not a pytest file: it starts servers.

    REDIS_URL=redis://localhost:6379/14 python tests/two_process_check.py        (from the backend folder)

It needs a Redis database it may empty: it clears the one in REDIS_URL before it starts (lobby and player numbers restart with
each run's fresh database, so keys left by an earlier run would be read as this run's), and it refuses database 0. Exit status 0
means every check passed.
"""

import asyncio
import json
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time

import redis
import requests
import socketio

REDIS_URL = os.environ.get("REDIS_URL", "")
if not REDIS_URL:
    sys.exit("REDIS_URL is not set (for example redis://localhost:6379/14)")

PORT_A, PORT_B = int(os.environ.get("PORT_A", "18001")), int(os.environ.get("PORT_B", "18002"))
A, B = f"http://127.0.0.1:{PORT_A}", f"http://127.0.0.1:{PORT_B}"
BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RUN = secrets.token_hex(3)
WORK = tempfile.mkdtemp(prefix="two_process_")
ENV = {
    **os.environ,
    "REDIS_URL": REDIS_URL,
    "DATABASE_URL": f"sqlite+aiosqlite:///{WORK}/shared.db",
    "SECRET_KEY": secrets.token_hex(32),          # the same in both processes, or a token made by one is refused by the other
    "AI_SERVICE_URL": "http://127.0.0.1:9",
    "FRONTEND_URL": "http://localhost:5173",
    "PYTHONDONTWRITEBYTECODE": "1",
}
procs = {}


def start(name, port):
    log = open(os.path.join(WORK, f"{name}.log"), "w")
    procs[name] = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                                   cwd=BACKEND, env=ENV, stdout=log, stderr=subprocess.STDOUT)


def wait_healthy(url, seconds=60):
    end = time.time() + seconds
    while time.time() < end:
        try:
            if requests.get(url + "/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.3)
    raise SystemExit(f"{url} did not become healthy")


def check(label, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {label}" + (f"  ({detail})" if detail else ""), flush=True)
    if not ok:
        raise AssertionError(label)


def post(base, path, data, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(base + path, json=data, headers=headers, timeout=20)
    return r.json(), r.status_code


def get(base, path):
    r = requests.get(base + path, timeout=20)
    return r.json(), r.status_code


def sign_in(base, name):
    post(base, "/api/v1/auth/register", {"username": name, "email": f"{name}@test.com", "password": "password123"})
    body, _ = post(base, "/api/v1/auth/login", {"username": name, "password": "password123"})
    return body["access_token"]


def user_id(base, token):
    r = requests.get(base + "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return r.json()["id"]


def grade(uid, question_id, score):
    """Record a graded score the way /submissions does after it grades a solution. A socket's score_update takes the points from
    this record, never from the message (lobby_manager.record_graded_score), and this check runs no judge, so it writes the
    record itself, into the same Redis both processes use."""
    store = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    key = f"pendingscore:{uid}"
    items = json.loads(store.get(key) or "[]")
    items.append({"q": question_id, "s": int(score)})
    store.set(key, json.dumps(items), ex=3600)


async def next_event(client, wanted, timeout=5):
    """The next event of this name (other events that arrive first are skipped)."""
    end = time.time() + timeout
    while time.time() < end:
        event = await client.receive(timeout=max(0.1, end - time.time()))
        if event[0] == wanted:
            return event[1] if len(event) > 1 else None
    raise AssertionError(f"no {wanted} event within {timeout} seconds")


def empty_the_test_database():
    store = redis.Redis.from_url(REDIS_URL)
    if int(store.connection_pool.connection_kwargs.get("db", 0)) == 0:
        sys.exit("REDIS_URL names database 0: give this check a spare database it may empty, for example redis://localhost:6379/14")
    store.flushdb()


async def play():
    print("\n  -- accounts and the lobby: made on process A, joined on process B")
    host, guest = f"host_{RUN}", f"guest_{RUN}"
    host_token = sign_in(A, host)
    guest_token = sign_in(B, guest)                                  # a token and an account made through B work on A too
    lobby, status = post(A, "/api/v1/lobbies", {"name": "Two processes", "max_players": 4, "time_limit": 600}, host_token)
    check("lobby created on A", status == 201, f"id {lobby['id']} code {lobby['code']}")
    lobby_id, code = lobby["id"], lobby["code"]
    host_player, _ = post(A, f"/api/v1/lobbies/{lobby_id}/join", {}, host_token)
    guest_player, status = post(B, f"/api/v1/lobbies/{lobby_id}/join", {}, guest_token)
    check("guest joins over HTTP on B", status == 200)
    seen_by_b, status = get(B, f"/api/v1/lobbies/{code}")
    check("process B finds the lobby A created, by its code", status == 200 and seen_by_b["code"] == code)

    print("\n  -- one socket on each process")
    host_id, guest_id = user_id(A, host_token), user_id(B, guest_token)
    on_a, on_b = socketio.AsyncSimpleClient(), socketio.AsyncSimpleClient()
    # a socket must carry its sign-in token when it connects (services/socket_auth.py)
    await on_a.connect(A, auth={"token": host_token}, transports=["websocket"], wait_timeout=10)
    await on_b.connect(B, auth={"token": guest_token}, transports=["websocket"], wait_timeout=10)
    check("host is connected to A and guest to B", on_a.connected and on_b.connected)

    join = lambda player, name: {"lobby_id": lobby_id, "player_id": player["player_id"], "user_id": player["player_id"], "username": name}
    await on_a.emit("join_lobby", join(host_player, host))
    state = await next_event(on_a, "lobby_state")
    check("host receives the lobby", state["player_count"] == 1)
    await on_b.emit("join_lobby", join(guest_player, guest))
    state = await next_event(on_b, "lobby_state")
    check("guest, on B, receives a lobby that already includes the host who joined on A", state["player_count"] == 2, str([p["username"] for p in state["players"]]))
    joined = await next_event(on_a, "player_joined")
    check("host, on A, is told the guest joined (the event crossed processes through Redis)", joined["username"] == guest)

    print("\n  -- a game across both")
    await on_a.emit("start_game", {"lobby_id": lobby_id})
    check("host receives game_started", (await next_event(on_a, "game_started"))["time_limit"] == 600)
    check("guest, on B, receives game_started that A sent", (await next_event(on_b, "game_started"))["time_limit"] == 600)

    grade(guest_id, 1, 70)
    await on_b.emit("score_update", {"lobby_id": lobby_id})
    board_on_a = (await next_event(on_a, "leaderboard_update"))["leaderboard"]
    check("host, on A, sees the score graded for the guest's submission through B", board_on_a[0]["username"] == guest and board_on_a[0]["score"] == 70, str(board_on_a[0]))
    await next_event(on_b, "leaderboard_update")
    grade(host_id, 1, 30)
    await on_a.emit("score_update", {"lobby_id": lobby_id})
    await next_event(on_a, "leaderboard_update")
    http_board, _ = get(A, f"/api/v1/lobbies/{lobby_id}/leaderboard")
    check("the HTTP leaderboard on A shows both scores, one sent through each process", [e["score"] for e in http_board["leaderboard"]] == [70, 30])
    http_board_b, _ = get(B, f"/api/v1/lobbies/{lobby_id}/leaderboard")
    check("and B gives the same one", http_board_b == http_board)

    print("\n  -- process A is killed in the middle of the game")
    procs["A"].send_signal(signal.SIGKILL)
    procs["A"].wait(timeout=10)
    try:
        requests.get(A + "/health", timeout=2)
        check("A is down", False)
    except requests.RequestException:
        check("A is down", True)
    still_there, status = get(B, f"/api/v1/lobbies/{lobby_id}/leaderboard")
    check("the game state is still there, served by B", status == 200 and [e["score"] for e in still_there["leaderboard"]] == [70, 30])
    await on_b.emit("question_submitted", {"lobby_id": lobby_id, "player_id": guest_player["player_id"], "question_index": 0})
    update = await next_event(on_b, "question_submission_update")
    check("the guest, still on B, keeps playing", update["submitted_count"] == 1 and update["total_count"] == 2)
    await on_a.disconnect()

    print("\n  -- the host reconnects, to B, and the game goes on")
    on_a2 = socketio.AsyncSimpleClient()
    await on_a2.connect(B, auth={"token": host_token}, transports=["websocket"], wait_timeout=10)
    await on_a2.emit("join_lobby", join(host_player, host))
    state = await next_event(on_a2, "lobby_state")
    mine = next(p for p in state["players"] if p["username"] == host)
    check("the host's score survived the crash of the process they were on", mine["score"] == 30 and state["player_count"] == 2)
    grade(guest_id, 2, 5)                                            # a second question: its 5 points add to the 70
    await on_b.emit("score_update", {"lobby_id": lobby_id})
    board = (await next_event(on_a2, "leaderboard_update"))["leaderboard"]
    check("an update from the guest reaches the host's new socket", board[0]["score"] == 75)
    await on_a2.emit("end_game", {"lobby_id": lobby_id})
    final_host, final_guest = await next_event(on_a2, "game_ended"), await next_event(on_b, "game_ended")
    check("both receive the final leaderboard", [e["score"] for e in final_host["leaderboard"]] == [75, 30] == [e["score"] for e in final_guest["leaderboard"]])

    await on_a2.disconnect()
    await on_b.disconnect()


def main():
    empty_the_test_database()
    start("A", PORT_A)
    start("B", PORT_B)
    try:
        wait_healthy(A)
        wait_healthy(B)
        print(f"\n=== two backend processes, one Redis ({REDIS_URL}) ===")
        asyncio.run(play())
        print("\n=== All checks passed ===\n")
        return 0
    except BaseException as exc:
        print(f"\nFAILED: {type(exc).__name__}: {exc}\n")
        for name in ("A", "B"):
            path = os.path.join(WORK, f"{name}.log")
            if os.path.exists(path):
                print(f"--- last lines of process {name}'s log ---")
                print("".join(open(path, errors="replace").readlines()[-25:]))
        return 1
    finally:
        for process in procs.values():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    sys.exit(main())
