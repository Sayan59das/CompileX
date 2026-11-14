"""The socket handlers over lobbies in shared state (Phase 1 of docs/scaling-plan.md): the events a game sends are the ones it always sent.

The handlers are registered on a fake socket server that records every emit, and a whole game is played through them. The one behaviour that
had to change is checked explicitly: the lobby a joining player is sent must include that player (it used to be a live object that did).

Run from the backend folder:  python -m pytest tests/test_socket_handlers.py -q
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import question_history, shared_state as ss
from app.services.lobby_manager import lobby_manager
from app.services.websocket_handler import register_socket_events


class FakeSio:
    def __init__(self):
        self.handlers, self.emitted, self.rooms = {}, [], {}

    def on(self, event):
        def register(fn):
            self.handlers[event] = fn
            return fn
        return register

    async def emit(self, event, data=None, to=None, room=None, skip_sid=None):
        self.emitted.append({"event": event, "data": data, "to": to, "room": room, "skip_sid": skip_sid})

    async def enter_room(self, sid, room):
        self.rooms.setdefault(room, set()).add(sid)

    async def leave_room(self, sid, room):
        self.rooms.get(room, set()).discard(sid)

    def events(self, name=None):
        return [e for e in self.emitted if name is None or e["event"] == name]

    async def fire(self, event, sid, data=None):
        self.emitted.clear()
        if event == "disconnect":                     # Socket.IO calls this one with the socket id alone
            await self.handlers[event](sid)
        else:
            await self.handlers[event](sid, data or {})
        return list(self.emitted)


@pytest.fixture
def game(monkeypatch):
    """A fresh in-process shared state, a fake socket server with the real handlers, and the history writes captured."""
    ss.set_redis(ss.MemoryRedis())
    seen = []

    async def record_seen(db, user_ids, title, topic, difficulty):
        seen.append((sorted(user_ids), title, topic, difficulty))

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    import app.db.database as database

    monkeypatch.setattr(database, "session_factory", lambda: Session())
    monkeypatch.setattr(question_history, "record_seen", record_seen)
    sio = FakeSio()
    register_socket_events(sio)
    sio.history = seen
    yield sio
    ss.set_redis(None)


def play(scenario):
    asyncio.run(scenario())


async def open_lobby(max_players=3, **kw):
    return await lobby_manager.create_lobby(5, "HHH111", "Room", 1, "host", max_players=max_players, time_per_question=300, **kw)


async def join(sio, sid, player_id, name):
    return await sio.fire("join_lobby", sid, {"lobby_id": 5, "player_id": player_id, "user_id": player_id * 10, "username": name})


def test_the_player_who_joins_is_sent_a_lobby_that_includes_them(game):
    async def scenario():
        await open_lobby()
        first = await join(game, "s1", 1, "ann")
        state = next(e for e in first if e["event"] == "lobby_state")
        assert state["to"] == "s1" and state["data"]["player_count"] == 1 and [p["username"] for p in state["data"]["players"]] == ["ann"]
        second = await join(game, "s2", 2, "bob")
        state = next(e for e in second if e["event"] == "lobby_state")
        assert state["data"]["player_count"] == 2 and [p["username"] for p in state["data"]["players"]] == ["ann", "bob"]
        joined = next(e for e in second if e["event"] == "player_joined")
        assert joined["data"] == {"player_id": 2, "username": "bob"} and joined["room"] == "5" and joined["skip_sid"] == "s2"
        assert game.rooms["5"] == {"s1", "s2"}

    play(scenario)


def test_joining_a_lobby_that_does_not_exist_or_is_full_is_refused(game):
    async def scenario():
        none = await game.fire("join_lobby", "s1", {"lobby_id": 404, "player_id": 1})
        assert [(e["event"], e["data"]["message"], e["to"]) for e in none] == [("error", "Lobby not found", "s1")]
        await open_lobby(max_players=1)
        await join(game, "s1", 1, "ann")
        full = await join(game, "s2", 2, "bob")
        assert [(e["event"], e["data"]["message"]) for e in full] == [("error", "Lobby is full")]
        assert "s2" not in game.rooms.get("5", set()) and await lobby_manager.player_for_sid("s2") is None

    play(scenario)


def test_a_whole_game_sends_the_events_it_always_sent(game):
    async def scenario():
        await open_lobby(num_rounds=1, questions_per_round=2)
        await join(game, "s1", 1, "ann")
        await join(game, "s2", 2, "bob")

        started = await game.fire("start_game", "s1", {"lobby_id": 5})
        data = started[0]["data"]
        assert [e["event"] for e in started] == ["game_started"] and started[0]["room"] == "5"
        assert set(data) == {"started_at", "time_limit", "num_rounds", "questions_per_round", "time_per_question", "game_mode"}
        assert data["time_per_question"] == 300 and data["game_mode"] == "multiplayer" and data["num_rounds"] == 1

        question = {"title": "Two Sum", "base_title": "Two Sum", "topic": "arrays", "difficulty": "easy"}
        sent = await game.fire("broadcast_question", "s1", {"lobby_id": 5, "question": question, "question_index": 0})
        assert [(e["event"], e["room"]) for e in sent] == [("new_question", "5")]
        assert sent[0]["data"] == {"question": question, "question_index": 0, "time_per_question": 300}
        assert game.history == [([10, 20], "Two Sum", "arrays", "easy")]            # every player in the lobby saw it, not only the host
        assert await lobby_manager.get_shared_question(5, 0) == question

        scores = await game.fire("score_update", "s1", {"lobby_id": 5, "player_id": 1, "score": 80})
        assert [(e["event"], e["data"]["leaderboard"][0]["username"], e["data"]["leaderboard"][0]["score"]) for e in scores] == [("leaderboard_update", "ann", 80)]
        await game.fire("score_update", "s2", {"lobby_id": 5, "player_id": 2, "score": 50})

        one = await game.fire("question_submitted", "s1", {"lobby_id": 5, "player_id": 1, "question_index": 0})
        assert [(e["event"], e["data"]) for e in one] == [("question_submission_update", {"question_index": 0, "submitted_count": 1, "total_count": 2})]
        both = await game.fire("question_submitted", "s2", {"lobby_id": 5, "player_id": 2, "question_index": 0})
        assert [e["event"] for e in both] == ["question_submission_update", "all_submitted"] and both[1]["data"] == {"question_index": 0}

        board = await game.fire("get_leaderboard", "s2", {"lobby_id": 5})
        assert board[0]["event"] == "leaderboard" and board[0]["to"] == "s2" and [e["rank"] for e in board[0]["data"]["leaderboard"]] == [1, 2]

        first_done = await game.fire("player_finished", "s1", {"lobby_id": 5, "player_id": 1})
        assert [e["event"] for e in first_done] == ["leaderboard_update", "player_finished"]
        assert first_done[1]["data"] == {"player_id": 1, "finished_count": 1, "total_count": 2}
        last_done = await game.fire("player_finished", "s2", {"lobby_id": 5, "player_id": 2})
        assert [e["event"] for e in last_done] == ["leaderboard_update", "player_finished", "game_ended"]    # everyone finished: the game ends by itself
        assert [(e["username"], e["score"]) for e in last_done[2]["data"]["leaderboard"]] == [("ann", 80), ("bob", 50)]

        late = await game.fire("score_update", "s1", {"lobby_id": 5, "player_id": 1, "score": 5})
        assert [(e["event"], e["data"]["message"]) for e in late] == [("error", "Game not active")]

    play(scenario)


def test_rounds_and_questions_advance_and_end(game):
    async def scenario():
        await open_lobby(num_rounds=2, questions_per_round=2)
        await join(game, "s1", 1, "ann")
        await game.fire("start_game", "s1", {"lobby_id": 5})
        questions = [{"title": "q1"}, {"title": "q2"}]
        begun = await game.fire("start_round", "s1", {"lobby_id": 5, "round_number": 1, "questions": questions})
        assert begun[0]["event"] == "round_started" and begun[0]["data"] == {"round_number": 1, "total_rounds": 2, "question": {"title": "q1"}, "time_per_question": 300}
        nxt = await game.fire("next_question", "s1", {"lobby_id": 5})
        assert nxt[0]["event"] == "new_question" and nxt[0]["data"] == {"question": {"title": "q2"}, "question_index": 1, "time_per_question": 300}
        over = await game.fire("next_question", "s1", {"lobby_id": 5})                 # no third question: the round ends
        assert over[0]["event"] == "round_ended" and over[0]["data"]["round_number"] == 1
        ended = await game.fire("end_round", "s1", {"lobby_id": 5, "round_number": 1})
        assert ended[0]["event"] == "round_ended" and ended[0]["data"]["round_number"] == 1
        refused = await game.fire("start_round", "s1", {"lobby_id": 404, "round_number": 1, "questions": []})
        assert [(e["event"], e["data"]["message"]) for e in refused] == [("error", "Cannot start round")]

    play(scenario)


def test_the_host_can_end_the_game_and_a_missing_lobby_is_an_error(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")
        await game.fire("start_game", "s1", {"lobby_id": 5})
        ended = await game.fire("end_game", "s1", {"lobby_id": 5})
        assert [e["event"] for e in ended] == ["game_ended"]
        again = await game.fire("end_game", "s1", {"lobby_id": 5})
        assert [(e["event"], e["data"]["message"]) for e in again] == [("error", "Cannot end game")]

    play(scenario)


def test_a_disconnect_tells_the_room_which_player_left(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")
        await join(game, "s2", 2, "bob")
        left = await game.fire("disconnect", "s2")
        assert [(e["event"], e["data"], e["room"]) for e in left] == [("player_left", {"player_id": 2}, "5")]
        assert "s2" not in game.rooms["5"]
        assert [p.username for p in (await lobby_manager.get_lobby(5)).players.values()] == ["ann"]
        assert await game.fire("disconnect", "never-joined") == []

    play(scenario)


def test_a_player_can_leave_on_purpose(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")
        left = await game.fire("leave_lobby", "s1", {"player_id": 1})
        assert [(e["event"], e["data"]) for e in left] == [("player_left", {"player_id": 1})]
        assert (await lobby_manager.get_lobby(5)).players == {}

    play(scenario)


def test_a_lobby_the_server_forgot_is_not_started(game):
    async def scenario():
        refused = await game.fire("start_game", "s1", {"lobby_id": 5})
        assert refused and refused[0]["event"] == "error"

    play(scenario)


def test_progress_events_are_relayed_to_the_others_in_the_room(game):
    async def scenario():
        typing = await game.fire("typing_progress", "s1", {"lobby_id": 5, "player_id": 1, "progress": 40})
        tests = await game.fire("test_progress", "s1", {"lobby_id": 5, "player_id": 1, "passed": 2, "total": 5})
        assert [(e["event"], e["data"], e["room"], e["skip_sid"]) for e in typing + tests] == [
            ("opponent_progress", {"player_id": 1, "progress": 40}, "5", "s1"),
            ("opponent_test_progress", {"player_id": 1, "passed": 2, "total": 5}, "5", "s1"),
        ]

    play(scenario)
