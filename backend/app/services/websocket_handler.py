import json

import socketio
from socketio.exceptions import ConnectionRefusedError as SocketRefused

from app.services import socket_auth
from app.services.lobby_manager import lobby_manager
from app.models.models import GameStatus

# A question the host sends to the room is shown to every player; it is public data, so a few hundred KB is already far more than a real one.
MAX_QUESTION_BYTES = 200_000


def _int(value):
    """An int from a message field, or None (True/False and floats are not ids)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _number(value, low, high):
    """A number from a message field, clamped into [low, high]; 0 when it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return 0
    return max(low, min(high, value))


def register_socket_events(sio: socketio.AsyncServer):
    """Every event below, apart from connect and disconnect, starts from `_identity` or `_seat`: who is this socket, and may it do this?

    The answer comes from the sign-in token given at connect and from the seat the socket joined, never from fields in the message.
    tests/test_socket_security.py fails if a handler skips both."""

    async def _deny(sid, message="Not allowed"):
        await sio.emit("error", {"message": message}, to=sid)

    async def _identity(sid):
        session = await sio.get_session(sid)
        return session if session and session.get("user_id") else None

    async def _seat(sid, lobby_id):
        """(identity, lobby, player_id) when this socket is signed in and sitting in this lobby; otherwise None."""
        identity = await _identity(sid)
        joined = await lobby_manager.session_for_sid(sid)
        if not identity or not joined or _int(lobby_id) is None or str(joined["lobby_id"]) != str(_int(lobby_id)):
            return None
        lobby = await lobby_manager.get_lobby(joined["lobby_id"])
        if not lobby:
            return None
        return identity, lobby, joined["player_id"]

    def _is_host(identity, lobby):
        return bool(lobby.created_by) and lobby.created_by == identity["user_id"]

    @sio.on("connect")
    async def on_connect(sid, environ, auth=None):
        token = auth.get("token") if isinstance(auth, dict) else None
        identity = await socket_auth.authenticate(token)
        if not identity:
            raise SocketRefused("Sign in first")
        await sio.save_session(sid, identity)
        print(f"[ws] connected: {sid} (user {identity['user_id']})")

    @sio.on("disconnect")
    async def on_disconnect(sid):
        # Capture player_id BEFORE leave_lobby pops it from _player_sessions
        player_id = await lobby_manager.player_for_sid(sid)
        lobby = await lobby_manager.leave_lobby(sid)
        if lobby:
            await sio.leave_room(sid, str(lobby.id))
            await sio.emit(
                "player_left",
                {"player_id": player_id},
                room=str(lobby.id),
            )
        print(f"[ws] disconnected: {sid}")

    @sio.on("join_lobby")
    async def on_join_lobby(sid, data):
        data = data if isinstance(data, dict) else {}
        identity = await _identity(sid)
        if not identity:
            return await _deny(sid, "Sign in first")
        lobby_id = _int(data.get("lobby_id"))
        player_id = _int(data.get("player_id"))

        lobby = await lobby_manager.get_lobby(lobby_id)
        if not lobby:
            await sio.emit("error", {"message": "Lobby not found"}, to=sid)
            return

        if len(lobby.players) >= lobby.max_players:
            await sio.emit("error", {"message": "Lobby is full"}, to=sid)
            return

        # The seat must be the one the join request gave this user: the name and the user id come from the token, not from the message.
        if player_id is None or not await socket_auth.player_belongs(player_id, lobby_id, identity["user_id"]):
            return await _deny(sid, "You are not a player of this lobby")

        # the snapshot join_lobby returns already includes this player (the lobby read above does not)
        joined = await lobby_manager.join_lobby(lobby_id, player_id, identity["user_id"], identity["username"], sid)
        if not joined:
            await sio.emit("error", {"message": "Lobby is full"}, to=sid)
            return
        await sio.enter_room(sid, str(lobby_id))

        await sio.emit("lobby_state", joined.to_dict(), to=sid)

        await sio.emit(
            "player_joined",
            {"player_id": player_id, "username": identity["username"]},
            room=str(lobby_id),
            skip_sid=sid,
        )

    @sio.on("leave_lobby")
    async def on_leave_lobby(sid, data):
        if not await _identity(sid):
            return await _deny(sid, "Sign in first")
        player_id = await lobby_manager.player_for_sid(sid)      # the seat this socket really holds, not the one the message names
        lobby = await lobby_manager.leave_lobby(sid)
        if lobby:
            await sio.leave_room(sid, str(lobby.id))
            await sio.emit(
                "player_left", {"player_id": player_id}, room=str(lobby.id)
            )

    @sio.on("start_game")
    async def on_start_game(sid, data):
        data = data if isinstance(data, dict) else {}
        identity = await _identity(sid)
        if not identity:
            return await _deny(sid, "Sign in first")
        lobby_id = _int(data.get("lobby_id"))

        # If lobby not in memory (e.g. server restarted), recreate from DB, but only for the host who made it
        if not await lobby_manager.get_lobby(lobby_id):
            try:
                from app.db.database import session_factory
                from app.models.models import Lobby as LobbyModel
                from sqlalchemy import select
                async with session_factory() as db:
                    result = await db.execute(select(LobbyModel).where(LobbyModel.id == lobby_id))
                    db_lobby = result.scalar_one_or_none()
                    if db_lobby and db_lobby.created_by == identity["user_id"]:
                        await lobby_manager.create_lobby(
                            lobby_id=db_lobby.id,
                            code=db_lobby.code,
                            name=db_lobby.name,
                            user_id=db_lobby.created_by,
                            username=identity["username"],
                            max_players=db_lobby.max_players,
                            time_limit=db_lobby.time_limit,
                            game_mode=db_lobby.game_mode,
                            is_public=db_lobby.is_public,
                            num_rounds=db_lobby.num_rounds,
                            questions_per_round=db_lobby.questions_per_round,
                            difficulty=db_lobby.difficulty.value if hasattr(db_lobby.difficulty, "value") else (db_lobby.difficulty or "medium"),
                            time_per_question=db_lobby.time_per_question,
                        )
                        # Re-add current player
                        await lobby_manager.join_lobby(db_lobby.id, sid, identity["user_id"], identity["username"], sid)
                        await sio.enter_room(sid, str(db_lobby.id))
            except Exception as e:
                print(f"[ws] Failed to recover lobby from DB: {e}")
                await sio.emit("error", {"message": "Failed to recover lobby"}, to=sid)
                return

        existing = await lobby_manager.get_lobby(lobby_id)
        if existing and not _is_host(identity, existing):
            return await _deny(sid, "Only the host can start the game")

        lobby = await lobby_manager.start_game(lobby_id)
        if not lobby:
            lb = await lobby_manager.get_lobby(lobby_id)
            if not lb:
                reason = "Lobby not found (recovery failed)."
            elif lb.status.name != "WAITING" if hasattr(lb.status, "name") else str(lb.status) != "WAITING":
                reason = f"Lobby in wrong state ({lb.status})."
            elif not lb.players:
                reason = "No players in lobby."
            else:
                reason = "Unknown error."
            await sio.emit("error", {"message": f"Cannot start game: {reason} — try refreshing the page"}, to=sid)
            return

        await sio.emit(
            "game_started",
            {
                "started_at": lobby.started_at.isoformat(),
                "time_limit": lobby.time_limit,
                "num_rounds": lobby.num_rounds,
                "questions_per_round": lobby.questions_per_round,
                "time_per_question": lobby.time_per_question,
                "game_mode": lobby.game_mode.value,
            },
            room=str(lobby_id),
        )

    @sio.on("broadcast_question")
    async def on_broadcast_question(sid, data):
        """
        Host sends a newly generated question to the server.
        Server stores it in the lobby question list and pushes it to ALL players.
        """
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat or not _is_host(seat[0], seat[1]):
            return await _deny(sid, "Only the host can send questions")
        lobby = seat[1]
        lobby_id = lobby.id
        question = data.get("question")
        question_index = _int(data.get("question_index", 0))

        if lobby.status != GameStatus.STARTED:
            return
        if not isinstance(question, dict) or question_index is None or question_index < 0:
            return await _deny(sid, "Invalid question")
        if len(json.dumps(question, default=str)) > MAX_QUESTION_BYTES:
            return await _deny(sid, "Question is too large")

        # Store question in lobby so late-joiners / reconnects can get it
        await lobby_manager.store_question(lobby_id, question, question_index)

        # Push to every player in the room (including the host)
        await sio.emit(
            "new_question",
            {
                "question": question,
                "question_index": question_index,
                "time_per_question": lobby.time_per_question,
            },
            room=str(lobby_id),
        )

        # Every player in the lobby has now seen this question, not only the host who generated it.
        try:
            from app.db.database import session_factory
            from app.services import question_history

            async with session_factory() as db:
                await question_history.record_seen(
                    db,
                    [p.user_id for p in lobby.players.values() if p.user_id],
                    question.get("base_title") or question.get("title"),
                    question.get("topic"),
                    question.get("difficulty"),
                )
        except Exception as e:
            print(f"[history] could not record question history: {e}")

    @sio.on("start_round")
    async def on_start_round(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat or not _is_host(seat[0], seat[1]):
            return await _deny(sid, "Only the host can start a round")
        lobby_id = seat[1].id
        round_number = _int(data.get("round_number", 1)) or 1
        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(json.dumps(questions, default=str)) > MAX_QUESTION_BYTES:
            return await _deny(sid, "Invalid questions")

        lobby = await lobby_manager.start_round(lobby_id, round_number, questions)
        if not lobby:
            await sio.emit("error", {"message": "Cannot start round"}, to=sid)
            return

        first_question = questions[0] if questions else None
        await sio.emit(
            "round_started",
            {
                "round_number": round_number,
                "total_rounds": lobby.num_rounds,
                "question": first_question,
                "time_per_question": lobby.time_per_question,
            },
            room=str(lobby_id),
        )

    @sio.on("next_question")
    async def on_next_question(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat or not _is_host(seat[0], seat[1]):
            return await _deny(sid, "Only the host can move to the next question")
        lobby_id = seat[1].id
        question = await lobby_manager.advance_question(lobby_id)
        lobby = await lobby_manager.get_lobby(lobby_id)

        if question and lobby:
            round_state = lobby.rounds.get(lobby.current_round)
            await sio.emit(
                "new_question",
                {
                    "question": question,
                    "question_index": round_state.current_question_index if round_state else 0,
                    "time_per_question": lobby.time_per_question,
                },
                room=str(lobby_id),
            )
        else:
            # No more questions in this round
            await sio.emit(
                "round_ended",
                {
                    "round_number": lobby.current_round if lobby else 0,
                    "leaderboard": await lobby_manager.get_leaderboard(lobby_id),
                },
                room=str(lobby_id),
            )

    @sio.on("end_round")
    async def on_end_round(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat or not _is_host(seat[0], seat[1]):
            return await _deny(sid, "Only the host can end a round")
        lobby_id = seat[1].id
        round_number = _int(data.get("round_number", 1)) or 1

        lobby = await lobby_manager.end_round(lobby_id, round_number)
        if lobby:
            leaderboard = await lobby_manager.get_leaderboard(lobby_id)
            await sio.emit(
                "round_ended",
                {"round_number": round_number, "leaderboard": leaderboard},
                room=str(lobby_id),
            )

    @sio.on("question_submitted")
    async def on_question_submitted(sid, data):
        """
        Emitted by every player when they submit their answer for the current question.
        When ALL players have submitted, the server notifies the room so the host
        can generate the next question. Until then, players see a waiting popup.
        """
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        lobby = seat[1]
        lobby_id = lobby.id
        player_id = seat[2]                      # this socket's own seat, whatever player_id the message names
        question_index = _int(data.get("question_index", 0))
        if question_index is None or question_index < 0:
            return

        if lobby.status != GameStatus.STARTED:
            return

        result = await lobby_manager.mark_question_submitted(lobby_id, player_id, question_index)

        # Broadcast updated waiting count to all players
        await sio.emit(
            "question_submission_update",
            {
                "question_index": question_index,
                "submitted_count": result["submitted_count"],
                "total_count": result["total_count"],
            },
            room=str(lobby_id),
        )

        if result["all_submitted"]:
            await lobby_manager.reset_question_submissions(lobby_id, question_index)
            # Tell the room everyone has submitted — host will generate next question
            await sio.emit(
                "all_submitted",
                {"question_index": question_index},
                room=str(lobby_id),
            )

    @sio.on("player_finished")
    async def on_player_finished(sid, data):
        """
        Emitted by a player when they have submitted all their questions.
        Tracks how many players are done. When all players finish, the server
        automatically ends the game and broadcasts game_ended to the room.
        """
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        lobby = seat[1]
        lobby_id = lobby.id
        player_id = seat[2]

        if lobby.status != GameStatus.STARTED:
            return

        result = await lobby_manager.mark_player_finished(lobby_id, player_id)

        # Broadcast updated leaderboard so the waiting popup stays live
        leaderboard = await lobby_manager.get_leaderboard(lobby_id)
        await sio.emit(
            "leaderboard_update",
            {"leaderboard": leaderboard},
            room=str(lobby_id),
        )

        # Notify all players how many have finished (for the waiting popup counter)
        await sio.emit(
            "player_finished",
            {
                "player_id": player_id,
                "finished_count": result["finished_count"],
                "total_count": result["total_count"],
            },
            room=str(lobby_id),
        )

        # When every player is done, end the game automatically
        if result["all_done"]:
            ended_lobby = await lobby_manager.end_game(lobby_id)
            if ended_lobby:
                final_leaderboard = await lobby_manager.get_leaderboard(lobby_id)
                await sio.emit(
                    "game_ended",
                    {"leaderboard": final_leaderboard},
                    room=str(lobby_id),
                )

    @sio.on("end_game")
    async def on_end_game(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat or not _is_host(seat[0], seat[1]):
            return await _deny(sid, "Only the host can end the game")
        lobby_id = seat[1].id
        lobby = await lobby_manager.end_game(lobby_id)
        if not lobby:
            await sio.emit("error", {"message": "Cannot end game"}, to=sid)
            return

        leaderboard = await lobby_manager.get_leaderboard(lobby_id)
        await sio.emit(
            "game_ended", {"leaderboard": leaderboard}, room=str(lobby_id)
        )

    @sio.on("score_update")
    async def on_score_update(sid, data):
        """The browser says it just submitted. The points are NOT taken from the message: the server applies the score it graded itself
        for this player's submission (recorded by the submit request), once per question, and only the best one counts."""
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        identity, lobby, player_id = seat

        if lobby.status != GameStatus.STARTED:
            await sio.emit("error", {"message": "Game not active"}, to=sid)
            return

        graded = await lobby_manager.take_graded_score(identity["user_id"])
        if graded is None:
            return                              # nothing was graded for this player, so there is nothing to add
        await lobby_manager.apply_graded_score(lobby.id, player_id, graded["q"], graded["s"])
        leaderboard = await lobby_manager.get_leaderboard(lobby.id)
        await sio.emit(
            "leaderboard_update",
            {"leaderboard": leaderboard},
            room=str(lobby.id),
        )

    @sio.on("get_leaderboard")
    async def on_get_leaderboard(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        leaderboard = await lobby_manager.get_leaderboard(seat[1].id)
        await sio.emit("leaderboard", {"leaderboard": leaderboard}, to=sid)

    @sio.on("typing_progress")
    async def on_typing_progress(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        await sio.emit(
            "opponent_progress",
            {"player_id": seat[2], "progress": _number(data.get("progress", 0), 0, 100)},
            room=str(seat[1].id),
            skip_sid=sid,
        )

    @sio.on("test_progress")
    async def on_test_progress(sid, data):
        data = data if isinstance(data, dict) else {}
        seat = await _seat(sid, data.get("lobby_id"))
        if not seat:
            return await _deny(sid)
        await sio.emit(
            "opponent_test_progress",
            {"player_id": seat[2], "passed": _number(data.get("passed", 0), 0, 1000), "total": _number(data.get("total", 0), 0, 1000)},
            room=str(seat[1].id),
            skip_sid=sid,
        )
