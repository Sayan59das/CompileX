"""Lobbies in shared state (Phase 1 of docs/scaling-plan.md): the manager behaves as it did when it was a dict, and two processes share it.

Every scenario runs against MemoryRedis and, when COMPILEX_TEST_REDIS_URL is set (CI always sets it), against a real Redis.

Run from the backend folder:  python -m pytest tests/test_lobby_manager.py -q
"""

import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.models import GameMode, GameStatus
from app.services import lobby_manager as lm
from app.services.lobby_manager import LobbyManager, LobbyState, PlayerState, RoundState
from state_helpers import KINDS, run


async def make(manager, lobby_id=7, code="ABC123", **kw):
    return await manager.create_lobby(lobby_id, code, "Room", 1, "host", **kw)


# ── the stored form ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_a_lobby_survives_being_stored_and_read_back_exactly():
    lobby = LobbyState(id=3, code="ZZ9", name="n", status=GameStatus.STARTED, game_mode=GameMode.ONE_V_ONE, is_public=True, max_players=2,
                       started_at=datetime(2026, 11, 14, 10, 30, 5, 123456), topics=["arrays", "graphs"], current_round=2)
    lobby.players = {5: PlayerState(5, 50, "ann", "sid1", 30, 2, True), "sock-9": PlayerState("sock-9", 0, "host", "sock-9")}
    lobby.rounds = {1: RoundState(1, [{"title": "q1"}], 0, "2026-11-14T10:30:05", True), 2: RoundState(2, [{"title": "q2"}, {"title": "q3"}], 1)}
    lobby.leaderboard = {5: 30, "sock-9": 0}
    lobby.shared_questions = [None, {"title": "shared", "test_cases": [{"input": "1", "output": "2"}]}]
    lobby.question_submissions = {0: [5, "sock-9"], 3: [5]}
    back = LobbyState.from_json(lobby.to_json())
    assert back == lobby
    assert list(back.players) == [5, "sock-9"]                   # ids keep their type: a number and a socket id
    assert back.to_dict() == lobby.to_dict()


def test_a_lobby_nobody_has_changed_is_not_written_again():
    from app.services.shared_state import MemoryRedis

    class Writes(MemoryRedis):
        sets = 0

        async def set(self, *a, **k):
            type(self).sets += 1
            return await super().set(*a, **k)

    async def main():
        r = Writes()
        manager = LobbyManager(redis=r)
        await make(manager)
        after_create = Writes.sets
        await manager.start_game(7)                 # no players: nothing changes
        await manager.advance_question(7)           # no round: nothing changes
        await manager.mark_player_finished(7, 99)   # unknown player: nothing changes
        assert Writes.sets == after_create

    asyncio.run(main())


# ── the manager, as before ──────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_create_find_by_code_and_list_public_lobbies(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        code = await m.generate_code()
        assert len(code) == 6 and code == code.upper()
        await make(m, 1, "AAA111", is_public=True)
        await make(m, 2, "BBB222", is_public=False)
        await make(m, 10, "CCC333", is_public=True)
        assert (await m.get_lobby_by_code("aaa111")).id == 1          # codes are case-insensitive
        assert await m.get_lobby_by_code("NOPE00") is None and await m.get_lobby(99) is None
        assert [l.id for l in await m.get_public_lobbies()] == [1, 10]   # public and waiting, in creation order (numeric, not text)
        await m.join_lobby(1, 5, 50, "ann", "s1")
        await m.start_game(1)
        assert [l.id for l in await m.get_public_lobbies()] == [10]      # a started lobby is no longer listed

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_join_leave_and_the_limit_on_players(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m, max_players=2)
        a = await m.join_lobby(7, 1, 10, "ann", "s1")
        assert list(a.players) == [1] and a.players[1].sid == "s1"
        assert await m.player_for_sid("s1") == 1
        await m.join_lobby(7, 2, 20, "bob", "s2")
        assert await m.join_lobby(7, 3, 30, "cy", "s3") is None              # full
        assert await m.player_for_sid("s3") is None
        again = await m.join_lobby(7, 1, 10, "ann", "s1b")                    # old behaviour: a reconnect is refused while the lobby is full
        assert again is None
        assert await m.join_lobby(99, 1, 10, "ann", "sx") is None             # no such lobby
        left = await m.leave_lobby("s1")
        assert list(left.players) == [2] and await m.player_for_sid("s1") is None
        assert await m.leave_lobby("s1") is None and await m.leave_lobby("never-seen") is None
        rejoin = await m.join_lobby(7, 1, 10, "ann", "s1c")
        assert sorted(rejoin.players) == [1, 2]

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_a_player_who_joins_again_keeps_their_score_and_gets_the_new_socket(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m)
        await m.join_lobby(7, 1, 10, "ann", "s1")
        await m.start_game(7)
        await m.update_score(7, 1, 40)
        back = await m.join_lobby(7, 1, 10, "ann", "s1-new")
        assert back.players[1].score == 40 and back.players[1].sid == "s1-new"

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_a_game_from_start_to_end(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m, num_rounds=2, questions_per_round=2)
        assert await m.start_game(7) is None                                      # nobody is in it yet
        await m.join_lobby(7, 1, 10, "ann", "s1")
        await m.join_lobby(7, 2, 20, "bob", "s2")
        started = await m.start_game(7)
        assert started.status == GameStatus.STARTED and started.started_at and started.current_round == 0
        assert await m.start_game(7) is None                                      # already started

        assert await m.start_round(99, 1, []) is None
        qs = [{"title": "q1"}, {"title": "q2"}, {"title": "q3"}]
        rnd = await m.start_round(7, 1, qs)
        assert rnd.current_round == 1 and rnd.rounds[1].questions == qs and rnd.rounds[1].started_at
        assert await m.advance_question(7) == {"title": "q2"}
        assert await m.advance_question(7) == {"title": "q3"}
        assert await m.advance_question(7) is None                                # past the last question
        assert (await m.end_round(7, 1)).rounds[1].ended is True
        assert await m.end_round(99, 1) is None

        await m.store_question(7, {"title": "shared-2"}, 2)
        assert await m.get_shared_question(7, 2) == {"title": "shared-2"}
        assert await m.get_shared_question(7, 0) is None and await m.get_shared_question(7, 5) is None

        await m.update_score(7, 1, 100)
        await m.update_score(7, 2, 60)
        await m.update_score(7, 2, 60)
        assert await m.update_score(7, 99, 5) is None
        board = await m.get_leaderboard(7)
        assert [(e["rank"], e["id"], e["score"], e["questions_solved"]) for e in board] == [(1, 2, 120, 2), (2, 1, 100, 1)]

        assert (await m.mark_player_finished(7, 1)) == {"finished_count": 1, "total_count": 2, "all_done": False}
        assert (await m.mark_player_finished(7, 2))["all_done"] is True
        assert (await m.mark_player_finished(7, 99)) == {"finished_count": 0, "total_count": 0, "all_done": False}

        ended = await m.end_game(7)
        assert ended.status == GameStatus.ENDED and ended.leaderboard == {1: 100, 2: 120}
        assert await m.end_game(7) is None                                        # only a started game ends
        assert await m.get_leaderboard(99) == []

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_question_submissions_count_each_player_once_and_reset(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m)
        for pid in (1, 2, 3):
            await m.join_lobby(7, pid, pid * 10, f"p{pid}", f"s{pid}")
        await m.start_game(7)
        assert (await m.mark_question_submitted(7, 1, 0)) == {"submitted_count": 1, "total_count": 3, "all_submitted": False}
        assert (await m.mark_question_submitted(7, 1, 0))["submitted_count"] == 1            # the same player twice counts once
        await m.mark_question_submitted(7, 2, 0)
        assert (await m.mark_question_submitted(7, 3, 0))["all_submitted"] is True
        assert (await m.mark_question_submitted(7, 1, 1))["submitted_count"] == 1            # another question has its own count
        await m.reset_question_submissions(7, 0)
        assert (await m.mark_question_submitted(7, 1, 0))["submitted_count"] == 1
        assert (await m.mark_question_submitted(99, 1, 0)) == {"submitted_count": 0, "total_count": 0, "all_submitted": False}

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_an_ended_game_cannot_be_started_again(kind):
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m)
        await m.join_lobby(7, 1, 10, "ann", "s1")
        await m.start_game(7)
        await m.end_game(7)
        assert (await m.get_lobby(7)).status == GameStatus.ENDED
        assert await m.start_game(7) is None

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_starting_a_game_clears_whatever_a_waiting_lobby_still_holds(kind):
    """Defensive: a lobby that is waiting but carries old scores, questions or submissions starts from nothing."""
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m)
        await m.join_lobby(7, 1, 10, "ann", "s1")
        stale = await m.get_lobby(7)
        stale.players[1].score, stale.players[1].questions_solved, stale.players[1].finished = 50, 3, True
        stale.leaderboard, stale.shared_questions, stale.question_submissions = {1: 50}, [{"x": 1}], {0: [1]}
        await r.set("lobby:7", stale.to_json())
        started = await m.start_game(7)
        p = started.players[1]
        assert (p.score, p.questions_solved, p.finished) == (0, 0, False)
        assert started.leaderboard == {} and started.shared_questions == [] and started.question_submissions == {}

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_a_lobby_with_a_socket_id_as_player_id_works(kind):
    """The recovery path in the socket handler joins the host with the socket id as the player id."""
    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m)
        joined = await m.join_lobby(7, "sock-1", 0, "host", "sock-1")
        assert list(joined.players) == ["sock-1"]
        assert (await m.start_game(7)).status == GameStatus.STARTED
        assert (await m.get_lobby(7)).players["sock-1"].username == "host"

    run(kind, scenario)


# ── two backend processes ───────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_a_lobby_made_by_one_process_is_joined_and_played_through_another(kind):
    async def scenario(ra, rb):
        a, b = LobbyManager(redis=ra), LobbyManager(redis=rb)
        await make(a)
        assert (await b.get_lobby_by_code("ABC123")).id == 7
        await b.join_lobby(7, 1, 10, "ann", "sa")
        await a.join_lobby(7, 2, 20, "bob", "sb")
        assert sorted((await a.get_lobby(7)).players) == [1, 2] == sorted((await b.get_lobby(7)).players)
        await a.start_game(7)
        await b.update_score(7, 1, 30)
        await a.update_score(7, 2, 20)
        assert [e["id"] for e in await b.get_leaderboard(7)] == [1, 2]
        assert await b.player_for_sid("sa") == 1 and await a.player_for_sid("sb") == 2   # which lobby a socket joined is shared too
        left = await b.leave_lobby("sb")                                                 # process B handles the disconnect of a socket A served
        assert list(left.players) == [1]

    run(kind, scenario, clients=2)


@pytest.mark.parametrize("kind", KINDS)
def test_concurrent_score_updates_from_two_processes_lose_nothing(kind):
    async def scenario(ra, rb):
        a, b = LobbyManager(redis=ra), LobbyManager(redis=rb)
        await make(a)
        for pid in (1, 2):
            await a.join_lobby(7, pid, pid * 10, f"p{pid}", f"s{pid}")
        await a.start_game(7)
        await asyncio.gather(*([a.update_score(7, 1, 5) for _ in range(25)] + [b.update_score(7, 1, 5) for _ in range(25)]
                               + [a.update_score(7, 2, 1) for _ in range(20)] + [b.update_score(7, 2, 1) for _ in range(20)]))
        players = (await a.get_lobby(7)).players
        return players[1].score, players[1].questions_solved, players[2].score, players[2].questions_solved

    assert run(kind, scenario, clients=2) == (250, 50, 40, 40)


@pytest.mark.parametrize("kind", KINDS)
def test_two_processes_joining_at_once_never_exceed_the_limit(kind):
    async def scenario(ra, rb):
        a, b = LobbyManager(redis=ra), LobbyManager(redis=rb)
        await make(a, max_players=3)
        results = await asyncio.gather(*[(a if i % 2 else b).join_lobby(7, i, i, f"p{i}", f"s{i}") for i in range(10)])
        return sum(r is not None for r in results), len((await a.get_lobby(7)).players)

    assert run(kind, scenario, clients=2) == (3, 3)


@pytest.mark.parametrize("kind", KINDS)
def test_the_last_two_submitters_on_two_processes_trigger_all_submitted_once(kind):
    async def scenario(ra, rb):
        a, b = LobbyManager(redis=ra), LobbyManager(redis=rb)
        await make(a)
        for pid in (1, 2, 3, 4):
            await a.join_lobby(7, pid, pid, f"p{pid}", f"s{pid}")
        await a.start_game(7)
        results = await asyncio.gather(*[(a if pid % 2 else b).mark_question_submitted(7, pid, 0) for pid in (1, 2, 3, 4)])
        return sum(r["all_submitted"] for r in results), sorted(r["submitted_count"] for r in results)

    assert run(kind, scenario, clients=2) == (1, [1, 2, 3, 4])


# ── forgetting ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_an_expired_lobby_is_gone_and_leaves_the_public_list(kind, monkeypatch):
    monkeypatch.setattr(lm, "LOBBY_TTL_SECONDS", 1)

    async def scenario(r):
        m = LobbyManager(redis=r)
        await make(m, is_public=True)
        assert [l.id for l in await m.get_public_lobbies()] == [7]
        await asyncio.sleep(1.2)
        assert await m.get_lobby(7) is None and await m.get_lobby_by_code("ABC123") is None
        assert await m.get_public_lobbies() == []
        assert await r.smembers("lobbies") == set()           # and its id was dropped from the index

    run(kind, scenario)


def test_the_default_manager_uses_the_process_state(monkeypatch):
    from app.services import shared_state as ss

    store = ss.MemoryRedis()
    ss.set_redis(store)
    try:
        async def main():
            await make(lm.lobby_manager, 42, "DEF456")
            return await store.get("lobby:42") is not None, (await lm.lobby_manager.get_lobby(42)).code

        assert asyncio.run(main()) == (True, "DEF456")
    finally:
        ss.set_redis(None)
