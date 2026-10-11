import socketio
from app.services.lobby_manager import lobby_manager
from app.models.models import GameStatus


def register_socket_events(sio: socketio.AsyncServer):

    @sio.on("connect")
    async def on_connect(sid, environ):
        print(f"[ws] connected: {sid}")

    @sio.on("disconnect")
    async def on_disconnect(sid):
        # Capture player_id BEFORE leave_lobby pops it from _player_sessions
        player_id = lobby_manager._player_sessions.get(sid)
        lobby = lobby_manager.leave_lobby(sid)
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
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")
        user_id = data.get("user_id", 0)
        username = data.get("username", "Anonymous")

        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby:
            await sio.emit("error", {"message": "Lobby not found"}, to=sid)
            return

        if len(lobby.players) >= lobby.max_players:
            await sio.emit("error", {"message": "Lobby is full"}, to=sid)
            return

        lobby_manager.join_lobby(lobby_id, player_id, user_id, username, sid)
        await sio.enter_room(sid, str(lobby_id))

        await sio.emit("lobby_state", lobby.to_dict(), to=sid)

        await sio.emit(
            "player_joined",
            {"player_id": player_id, "username": username},
            room=str(lobby_id),
            skip_sid=sid,
        )

    @sio.on("leave_lobby")
    async def on_leave_lobby(sid, data):
        player_id = data.get("player_id")
        lobby = lobby_manager.leave_lobby(sid)
        if lobby:
            await sio.leave_room(sid, str(lobby.id))
            await sio.emit(
                "player_left", {"player_id": player_id}, room=str(lobby.id)
            )

    @sio.on("start_game")
    async def on_start_game(sid, data):
        lobby_id = data.get("lobby_id")
        if lobby_id is not None:
            try:
                lobby_id = int(lobby_id)
            except ValueError:
                pass

        # If lobby not in memory (e.g. server restarted), recreate from DB
        if not lobby_manager.get_lobby(lobby_id):
            try:
                from app.db.database import session_factory
                from app.models.models import Lobby as LobbyModel
                from sqlalchemy import select
                async with session_factory() as db:
                    result = await db.execute(select(LobbyModel).where(LobbyModel.id == lobby_id))
                    db_lobby = result.scalar_one_or_none()
                    if db_lobby:
                        lobby_manager.create_lobby(
                            lobby_id=db_lobby.id,
                            code=db_lobby.code,
                            name=db_lobby.name,
                            user_id=db_lobby.created_by,
                            username="host",
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
                        lobby_manager.join_lobby(db_lobby.id, sid, 0, "host", sid)
                        await sio.enter_room(sid, str(db_lobby.id))
            except Exception as e:
                print(f"[ws] Failed to recover lobby from DB: {e}")
                await sio.emit("error", {"message": f"Failed to recover lobby: {e}"}, to=sid)
                return

        lobby = lobby_manager.start_game(lobby_id)
        if not lobby:
            lb = lobby_manager.get_lobby(lobby_id)
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
        lobby_id = data.get("lobby_id")
        question = data.get("question")
        question_index = data.get("question_index", 0)

        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            return

        # Store question in lobby so late-joiners / reconnects can get it
        lobby_manager.store_question(lobby_id, question, question_index)

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
        lobby_id = data.get("lobby_id")
        round_number = data.get("round_number", 1)
        questions = data.get("questions", [])

        lobby = lobby_manager.start_round(lobby_id, round_number, questions)
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
        lobby_id = data.get("lobby_id")
        question = lobby_manager.advance_question(lobby_id)
        lobby = lobby_manager.get_lobby(lobby_id)

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
                    "leaderboard": lobby_manager.get_leaderboard(lobby_id),
                },
                room=str(lobby_id),
            )

    @sio.on("end_round")
    async def on_end_round(sid, data):
        lobby_id = data.get("lobby_id")
        round_number = data.get("round_number", 1)

        lobby = lobby_manager.end_round(lobby_id, round_number)
        if lobby:
            leaderboard = lobby_manager.get_leaderboard(lobby_id)
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
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")
        question_index = data.get("question_index", 0)

        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            return

        result = lobby_manager.mark_question_submitted(lobby_id, player_id, question_index)

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
            lobby_manager.reset_question_submissions(lobby_id, question_index)
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
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")

        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            return

        result = lobby_manager.mark_player_finished(lobby_id, player_id)

        # Broadcast updated leaderboard so the waiting popup stays live
        leaderboard = lobby_manager.get_leaderboard(lobby_id)
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
            ended_lobby = lobby_manager.end_game(lobby_id)
            if ended_lobby:
                final_leaderboard = lobby_manager.get_leaderboard(lobby_id)
                await sio.emit(
                    "game_ended",
                    {"leaderboard": final_leaderboard},
                    room=str(lobby_id),
                )

    @sio.on("end_game")
    async def on_end_game(sid, data):
        lobby_id = data.get("lobby_id")
        lobby = lobby_manager.end_game(lobby_id)
        if not lobby:
            await sio.emit("error", {"message": "Cannot end game"}, to=sid)
            return

        leaderboard = lobby_manager.get_leaderboard(lobby_id)
        await sio.emit(
            "game_ended", {"leaderboard": leaderboard}, room=str(lobby_id)
        )

    @sio.on("new_question")
    async def on_new_question(sid, data):
        lobby_id = data.get("lobby_id")
        question = data.get("question")
        await sio.emit(
            "new_question",
            {"question": question},
            room=str(lobby_id),
            skip_sid=sid,
        )

    @sio.on("score_update")
    async def on_score_update(sid, data):
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")
        score = data.get("score", 0)

        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            await sio.emit("error", {"message": "Game not active"}, to=sid)
            return

        lobby_manager.update_score(lobby_id, player_id, score)
        leaderboard = lobby_manager.get_leaderboard(lobby_id)
        await sio.emit(
            "leaderboard_update",
            {"leaderboard": leaderboard},
            room=str(lobby_id),
        )

    @sio.on("get_leaderboard")
    async def on_get_leaderboard(sid, data):
        lobby_id = data.get("lobby_id")
        leaderboard = lobby_manager.get_leaderboard(lobby_id)
        await sio.emit("leaderboard", {"leaderboard": leaderboard}, to=sid)

    @sio.on("typing_progress")
    async def on_typing_progress(sid, data):
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")
        progress = data.get("progress", 0)
        await sio.emit(
            "opponent_progress",
            {"player_id": player_id, "progress": progress},
            room=str(lobby_id),
            skip_sid=sid,
        )

    @sio.on("test_progress")
    async def on_test_progress(sid, data):
        lobby_id = data.get("lobby_id")
        player_id = data.get("player_id")
        passed = data.get("passed", 0)
        total = data.get("total", 0)
        await sio.emit(
            "opponent_test_progress",
            {"player_id": player_id, "passed": passed, "total": total},
            room=str(lobby_id),
            skip_sid=sid,
        )
