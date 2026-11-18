"""The live-match sockets trust nobody (security review, problem 1).

Before: any browser could connect without a token, send any user id, set any player's score, start or end any lobby, or push a question into a room.
Now: a socket needs a valid sign-in token, who it is comes from the token, what it may do comes from the seat it joined, and scores are the ones
the server graded. Each test below is one of those attacks, played through the real handlers.

Run from the backend folder:  python -m pytest tests/test_socket_security.py -q
"""

import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from socketio.exceptions import ConnectionRefusedError as SocketRefused

from app.services.lobby_manager import lobby_manager
from test_socket_handlers import game, play, open_lobby, join, sign_in      # noqa: F401  (the fake socket server, fixtures and helpers)

QUESTION = {"title": "Two Sum", "topic": "arrays", "difficulty": "easy"}


def errors(events):
    return [e["data"]["message"] for e in events if e["event"] == "error"]


def room_events(events):
    return [e for e in events if e["room"] is not None]


# ── who is connecting ───────────────────────────────────────────────────────


def test_a_socket_without_a_valid_token_is_refused_and_a_good_one_is_remembered(game):
    async def scenario():
        for bad in (None, {}, {"token": ""}, {"token": "tok999"}, {"token": 12345}, "tok1"):
            with pytest.raises(SocketRefused):
                await game.fire("connect", "s1", bad)
        assert game.sessions == {}
        await sign_in(game, "s1", 1)
        assert game.sessions["s1"] == {"user_id": 1, "username": "ann"}

    play(scenario)


def test_every_event_is_refused_for_a_socket_that_never_signed_in(game):
    async def scenario():
        await open_lobby()
        for event in ("join_lobby", "leave_lobby", "start_game"):
            assert errors(await game.fire(event, "ghost", {"lobby_id": 5, "player_id": 1})) == ["Sign in first"]
        for event in ("broadcast_question", "start_round", "next_question", "end_round", "question_submitted", "player_finished",
                      "end_game", "score_update", "get_leaderboard", "typing_progress", "test_progress"):
            sent = await game.fire(event, "ghost", {"lobby_id": 5, "player_id": 1, "score": 99, "question": QUESTION})
            assert len(errors(sent)) == 1 and not room_events(sent), event

    play(scenario)


def test_who_you_are_comes_from_the_token_not_from_the_message(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")            # the message says user 999 / "mallory"
        lobby = await lobby_manager.get_lobby(5)
        assert [(p.user_id, p.username) for p in lobby.players.values()] == [(1, "ann")]

    play(scenario)


def test_a_player_cannot_take_someone_elses_seat(game):
    async def scenario():
        await open_lobby()
        await sign_in(game, "s1", 1)
        stolen = await game.fire("join_lobby", "s1", {"lobby_id": 5, "player_id": 2})        # bob's seat
        assert errors(stolen) == ["You are not a player of this lobby"]
        assert (await lobby_manager.get_lobby(5)).players == {} and "s1" not in game.rooms.get("5", set())
        assert await lobby_manager.player_for_sid("s1") is None
        for junk in (None, "x", 1.5, True, [1]):
            assert errors(await game.fire("join_lobby", "s1", {"lobby_id": 5, "player_id": junk}))

    play(scenario)


# ── who may do what ─────────────────────────────────────────────────────────


def test_someone_outside_the_lobby_can_do_nothing_in_it(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")
        await game.fire("start_game", "s1", {"lobby_id": 5})
        await sign_in(game, "outsider", 3)                       # signed in, but never joined lobby 5
        before = (await lobby_manager.get_lobby(5)).to_json()
        for event, body in (
            ("broadcast_question", {"question": QUESTION, "question_index": 0}), ("start_round", {"round_number": 1, "questions": [QUESTION]}),
            ("next_question", {}), ("end_round", {"round_number": 1}), ("question_submitted", {"question_index": 0}), ("player_finished", {}),
            ("end_game", {}), ("score_update", {"score": 100}), ("get_leaderboard", {}), ("typing_progress", {"progress": 50}),
            ("test_progress", {"passed": 1, "total": 1}), ("start_game", {}),
        ):
            sent = await game.fire(event, "outsider", dict(body, lobby_id=5))
            assert len(errors(sent)) == 1 and not room_events(sent), event
        assert (await lobby_manager.get_lobby(5)).to_json() == before            # not one thing changed

    play(scenario)


def test_only_the_host_can_start_or_end_the_game_or_send_questions_and_rounds(game):
    async def scenario():
        await open_lobby()                                       # created by user 1 (ann)
        await join(game, "s1", 1, "ann")
        await join(game, "s2", 2, "bob")
        assert errors(await game.fire("start_game", "s2", {"lobby_id": 5})) == ["Only the host can start the game"]
        assert (await lobby_manager.get_lobby(5)).status.name == "WAITING"
        await game.fire("start_game", "s1", {"lobby_id": 5})
        for event, body, message in (
            ("broadcast_question", {"question": QUESTION, "question_index": 0}, "Only the host can send questions"),
            ("start_round", {"round_number": 1, "questions": [QUESTION]}, "Only the host can start a round"),
            ("next_question", {}, "Only the host can move to the next question"),
            ("end_round", {"round_number": 1}, "Only the host can end a round"),
            ("end_game", {}, "Only the host can end the game"),
        ):
            sent = await game.fire(event, "s2", dict(body, lobby_id=5))
            assert errors(sent) == [message] and not room_events(sent), event
        assert (await lobby_manager.get_lobby(5)).status.name == "STARTED"
        assert [e["event"] for e in await game.fire("end_game", "s1", {"lobby_id": 5})] == ["game_ended"]

    play(scenario)


def test_the_host_cannot_send_junk_or_huge_questions(game):
    async def scenario():
        await open_lobby()
        await join(game, "s1", 1, "ann")
        await game.fire("start_game", "s1", {"lobby_id": 5})
        for bad in (None, "a string", [1], 5):
            assert errors(await game.fire("broadcast_question", "s1", {"lobby_id": 5, "question": bad, "question_index": 0})) == ["Invalid question"]
        assert errors(await game.fire("broadcast_question", "s1", {"lobby_id": 5, "question": QUESTION, "question_index": -1})) == ["Invalid question"]
        huge = dict(QUESTION, description="x" * 300_000)
        assert errors(await game.fire("broadcast_question", "s1", {"lobby_id": 5, "question": huge, "question_index": 0})) == ["Question is too large"]
        assert await lobby_manager.get_shared_question(5, 0) is None

    play(scenario)


def test_a_client_can_no_longer_push_a_question_to_a_room_by_itself(game):
    assert "new_question" not in game.handlers                   # the server sends it; there is no handler that relays one from a browser


# ── scores ──────────────────────────────────────────────────────────────────


async def started_pair(game):
    await open_lobby()
    await join(game, "s1", 1, "ann")
    await join(game, "s2", 2, "bob")
    await game.fire("start_game", "s1", {"lobby_id": 5})


def score_of(lobby, player_id):
    return lobby.players[player_id].score


def test_the_score_is_the_one_the_server_graded_not_the_one_the_browser_sends(game):
    async def scenario():
        await started_pair(game)
        await lobby_manager.record_graded_score(1, 101, 80)
        await game.fire("score_update", "s1", {"lobby_id": 5, "player_id": 1, "score": 1_000_000})
        assert score_of(await lobby_manager.get_lobby(5), 1) == 80

    play(scenario)


def test_a_score_update_with_nothing_graded_adds_nothing(game):
    async def scenario():
        await started_pair(game)
        for claimed in (100, -50, "lots", None):
            await game.fire("score_update", "s1", {"lobby_id": 5, "player_id": 1, "score": claimed})
        assert score_of(await lobby_manager.get_lobby(5), 1) == 0

    play(scenario)


def test_you_cannot_score_for_someone_else_or_use_someone_elses_graded_score(game):
    async def scenario():
        await started_pair(game)
        await lobby_manager.record_graded_score(2, 101, 90)          # graded for bob
        await game.fire("score_update", "s1", {"lobby_id": 5, "player_id": 2, "score": 90})       # ann says "bob scored"
        lobby = await lobby_manager.get_lobby(5)
        assert score_of(lobby, 1) == 0 and score_of(lobby, 2) == 0   # nothing was ann's to apply, and bob's stays waiting for bob
        await game.fire("score_update", "s2", {"lobby_id": 5})
        assert score_of(await lobby_manager.get_lobby(5), 2) == 90

    play(scenario)


def test_the_same_question_cannot_be_scored_twice_and_a_better_answer_adds_only_the_difference(game):
    async def scenario():
        await started_pair(game)
        for question, score in ((101, 60), (101, 60), (101, 60), (101, 100), (101, 40), (102, 30)):
            await lobby_manager.record_graded_score(1, question, score)
            await game.fire("score_update", "s1", {"lobby_id": 5})
        lobby = await lobby_manager.get_lobby(5)
        assert score_of(lobby, 1) == 100 + 30 and lobby.players[1].questions_solved == 2

    play(scenario)


def test_graded_scores_are_applied_in_the_order_they_were_graded(game):
    async def scenario():
        await lobby_manager.record_graded_score(7, 1, 10)
        await lobby_manager.record_graded_score(7, 2, 20)
        assert await lobby_manager.take_graded_score(7) == {"q": 1, "s": 10}
        assert await lobby_manager.take_graded_score(7) == {"q": 2, "s": 20}
        assert await lobby_manager.take_graded_score(7) is None

    play(scenario)


def test_the_player_named_in_a_message_is_ignored_in_favour_of_the_seat_the_socket_holds(game):
    async def scenario():
        await started_pair(game)
        await game.fire("question_submitted", "s2", {"lobby_id": 5, "player_id": 1, "question_index": 0})    # bob claims to be ann
        assert (await lobby_manager.get_lobby(5)).question_submissions[0] == [2]
        done = await game.fire("player_finished", "s2", {"lobby_id": 5, "player_id": 1})
        assert next(e for e in done if e["event"] == "player_finished")["data"]["player_id"] == 2
        left = await game.fire("leave_lobby", "s2", {"player_id": 1})
        assert [(e["event"], e["data"]) for e in left] == [("player_left", {"player_id": 2})]
        assert list((await lobby_manager.get_lobby(5)).players) == [1]

    play(scenario)


def test_progress_numbers_are_clamped_and_attributed_to_the_real_seat(game):
    async def scenario():
        await started_pair(game)
        typing = await game.fire("typing_progress", "s1", {"lobby_id": 5, "player_id": 2, "progress": 10 ** 9})
        assert typing[0]["data"] == {"player_id": 1, "progress": 100}
        for junk in (-5, "40", None, float("nan"), True):
            sent = await game.fire("typing_progress", "s1", {"lobby_id": 5, "progress": junk})
            assert sent[0]["data"]["progress"] in (0,), junk
        tests = await game.fire("test_progress", "s1", {"lobby_id": 5, "passed": 10 ** 9, "total": -1})
        assert tests[0]["data"] == {"player_id": 1, "passed": 1000, "total": 0}

    play(scenario)


# ── the guard that keeps this true ──────────────────────────────────────────


def test_every_handler_checks_who_is_asking_before_it_does_anything():
    """A new event added later without a check would reopen the hole: this fails until it starts from _identity or _seat."""
    path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "websocket_handler.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    checked, skipped = [], {"connect", "disconnect"}
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and any(
            isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "on" for d in node.decorator_list
        ):
            event = node.decorator_list[0].args[0].value
            if event in skipped:
                continue
            calls = {c.func.id for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            assert calls & {"_identity", "_seat"}, f"the {event} handler never checks who is asking"
            checked.append(event)
    assert len(checked) >= 13


def test_the_submit_route_records_the_score_it_graded():
    src = open(os.path.join(os.path.dirname(__file__), "..", "app", "api", "v1", "routes.py"), encoding="utf-8").read()
    assert "lobby_manager.record_graded_score(current_user.id, submission.question_id, final_score)" in src


def test_the_browser_sends_its_token_when_it_connects():
    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "services", "socket.js"), encoding="utf-8").read()
    assert "auth:" in src and "localStorage.getItem('token')" in src
