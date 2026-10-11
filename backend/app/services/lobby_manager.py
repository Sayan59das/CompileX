import uuid
import json
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from app.models.models import GameStatus, GameMode, DifficultyLevel


class GameEvent(str, Enum):
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    ROUND_STARTED = "round_started"
    ROUND_ENDED = "round_ended"
    LEADERBOARD_UPDATE = "leaderboard_update"
    SUBMISSION_RESULT = "submission_result"
    TIMER_UPDATE = "timer_update"


@dataclass
class PlayerState:
    id: int
    user_id: int
    username: str
    sid: Optional[str] = None
    score: int = 0
    questions_solved: int = 0
    finished: bool = False  # True when player has submitted all questions

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "score": self.score,
            "questions_solved": self.questions_solved,
        }


@dataclass
class RoundState:
    round_number: int
    questions: list = field(default_factory=list)
    current_question_index: int = 0
    started_at: Optional[str] = None
    ended: bool = False

    def to_dict(self):
        return {
            "round_number": self.round_number,
            "questions": self.questions,
            "current_question_index": self.current_question_index,
            "started_at": self.started_at,
            "ended": self.ended,
        }


@dataclass
class LobbyState:
    id: int
    code: str
    name: str
    status: GameStatus = GameStatus.WAITING
    game_mode: GameMode = GameMode.MULTIPLAYER
    is_public: bool = False
    max_players: int = 10
    time_limit: int = 3600
    created_by: int = 0
    started_at: Optional[datetime] = None
    players: Dict[int, PlayerState] = field(default_factory=dict)
    questions: list = field(default_factory=list)
    leaderboard: Dict[int, int] = field(default_factory=dict)

    # Round system
    num_rounds: int = 1
    questions_per_round: int = 1
    difficulty: str = "medium"
    topics: list = field(default_factory=list)
    time_per_question: int = 600
    current_round: int = 0
    rounds: Dict[int, RoundState] = field(default_factory=dict)
    # Shared question list — same for all players
    shared_questions: list = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "status": self.status.value,
            "game_mode": self.game_mode.value,
            "is_public": self.is_public,
            "max_players": self.max_players,
            "time_limit": self.time_limit,
            "created_by": self.created_by,
            "player_count": len(self.players),
            "players": [p.to_dict() for p in self.players.values()],
            "questions_count": len(self.questions),
            "num_rounds": self.num_rounds,
            "questions_per_round": self.questions_per_round,
            "difficulty": self.difficulty,
            "topics": self.topics,
            "time_per_question": self.time_per_question,
            "current_round": self.current_round,
            "current_round_state": self.rounds[self.current_round].to_dict() if self.current_round in self.rounds else None,
        }


class LobbyManager:
    def __init__(self):
        self._lobbies: Dict[int, LobbyState] = {}
        self._lobby_codes: Dict[str, int] = {}
        self._player_sessions: Dict[str, int] = {}  # sid -> player_id
        self._sid_to_lobby: Dict[str, int] = {}  # sid -> lobby_id

    def generate_code(self) -> str:
        while True:
            code = uuid.uuid4().hex[:6].upper()
            if code not in self._lobby_codes:
                return code

    def create_lobby(
        self,
        lobby_id,
        code,
        name,
        user_id,
        username,
        max_players=10,
        time_limit=3600,
        game_mode=GameMode.MULTIPLAYER,
        is_public=False,
        num_rounds=1,
        questions_per_round=1,
        difficulty="medium",
        topics=None,
        time_per_question=600,
    ):
        lobby = LobbyState(
            id=lobby_id,
            code=code,
            name=name,
            max_players=max_players,
            time_limit=time_limit,
            created_by=user_id,
            game_mode=game_mode,
            is_public=is_public,
            num_rounds=num_rounds,
            questions_per_round=questions_per_round,
            difficulty=difficulty,
            topics=topics or [],
            time_per_question=time_per_question,
        )
        self._lobbies[lobby_id] = lobby
        self._lobby_codes[code] = lobby_id
        return lobby

    def get_lobby(self, lobby_id: int) -> Optional[LobbyState]:
        return self._lobbies.get(lobby_id)

    def get_lobby_by_code(self, code: str) -> Optional[LobbyState]:
        lid = self._lobby_codes.get(code.upper())
        return self._lobbies.get(lid) if lid else None

    def get_public_lobbies(self) -> List[LobbyState]:
        return [
            lobby
            for lobby in self._lobbies.values()
            if lobby.is_public and lobby.status == GameStatus.WAITING
        ]

    def join_lobby(self, lobby_id, player_id, user_id, username, sid) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or len(lobby.players) >= lobby.max_players:
            return None

        if player_id in lobby.players:
            lobby.players[player_id].sid = sid
        else:
            lobby.players[player_id] = PlayerState(
                id=player_id, user_id=user_id, username=username, sid=sid
            )

        self._player_sessions[sid] = player_id
        self._sid_to_lobby[sid] = lobby_id
        return lobby

    def leave_lobby(self, sid: str) -> Optional[LobbyState]:
        player_id = self._player_sessions.pop(sid, None)
        if not player_id:
            return None

        lobby_id = self._sid_to_lobby.pop(sid, None)
        if lobby_id:
            lobby = self._lobbies.get(lobby_id)
            if lobby and player_id in lobby.players:
                del lobby.players[player_id]
                return lobby
        return None

    def start_game(self, lobby_id: int) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or lobby.status != GameStatus.WAITING or not lobby.players:
            return None

        lobby.status = GameStatus.STARTED
        lobby.started_at = datetime.utcnow()
        lobby.current_round = 0

        for p in lobby.players.values():
            p.score = 0
            p.questions_solved = 0
            p.finished = False
        lobby.leaderboard = {}
        lobby.shared_questions = []
        return lobby

    def start_round(self, lobby_id: int, round_number: int, questions: list) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            return None

        lobby.current_round = round_number
        lobby.rounds[round_number] = RoundState(
            round_number=round_number,
            questions=questions,
            started_at=datetime.utcnow().isoformat(),
        )
        return lobby

    def end_round(self, lobby_id: int, round_number: int) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby:
            return None

        round_state = lobby.rounds.get(round_number)
        if round_state:
            round_state.ended = True
        return lobby

    def advance_question(self, lobby_id: int) -> Optional[dict]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby:
            return None

        round_state = lobby.rounds.get(lobby.current_round)
        if not round_state:
            return None

        round_state.current_question_index += 1
        if round_state.current_question_index < len(round_state.questions):
            return round_state.questions[round_state.current_question_index]
        return None

    def end_game(self, lobby_id: int) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or lobby.status != GameStatus.STARTED:
            return None

        lobby.status = GameStatus.ENDED
        for p in lobby.players.values():
            lobby.leaderboard[p.id] = p.score
        return lobby

    def store_question(self, lobby_id: int, question: dict, index: int) -> None:
        """Store a shared question so all players get the same one."""
        lobby = self._lobbies.get(lobby_id)
        if not lobby:
            return
        # Extend list if needed
        while len(lobby.shared_questions) <= index:
            lobby.shared_questions.append(None)
        lobby.shared_questions[index] = question

    def get_shared_question(self, lobby_id: int, index: int) -> Optional[dict]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or index >= len(lobby.shared_questions):
            return None
        return lobby.shared_questions[index]

    def mark_player_finished(self, lobby_id: int, player_id: int) -> dict:
        """
        Mark a player as having completed all their questions.
        Returns a dict with:
          - finished_count: how many players have finished
          - total_count: total players in the lobby
          - all_done: True when every player has finished
        """
        lobby = self._lobbies.get(lobby_id)
        if not lobby or player_id not in lobby.players:
            return {"finished_count": 0, "total_count": 0, "all_done": False}

        lobby.players[player_id].finished = True
        finished_count = sum(1 for p in lobby.players.values() if p.finished)
        total_count = len(lobby.players)
        return {
            "finished_count": finished_count,
            "total_count": total_count,
            "all_done": finished_count >= total_count,
        }

    def mark_question_submitted(self, lobby_id: int, player_id: int, question_index: int) -> dict:
        """
        Track per-question submissions. Returns all_submitted=True when every
        active player has submitted for this question_index.
        """
        lobby = self._lobbies.get(lobby_id)
        if not lobby:
            return {"submitted_count": 0, "total_count": 0, "all_submitted": False}

        # Lazy-init the per-question submission set
        if not hasattr(lobby, "_question_submissions"):
            lobby._question_submissions = {}
        submitted_set = lobby._question_submissions.setdefault(question_index, set())
        submitted_set.add(player_id)

        total_count = len(lobby.players)
        submitted_count = len(submitted_set)
        return {
            "submitted_count": submitted_count,
            "total_count": total_count,
            "all_submitted": submitted_count >= total_count,
        }

    def reset_question_submissions(self, lobby_id: int, question_index: int) -> None:
        """Clear submission tracking for a question index (called when moving to next question)."""
        lobby = self._lobbies.get(lobby_id)
        if lobby and hasattr(lobby, "_question_submissions"):
            lobby._question_submissions.pop(question_index, None)

    def update_score(self, lobby_id, player_id, score) -> Optional[LobbyState]:
        lobby = self._lobbies.get(lobby_id)
        if not lobby or player_id not in lobby.players:
            return None

        lobby.players[player_id].score += score
        lobby.players[player_id].questions_solved += 1
        lobby.leaderboard[player_id] = lobby.players[player_id].score
        return lobby

    def get_leaderboard(self, lobby_id: int) -> list:
        lobby = self._lobbies.get(lobby_id)
        if not lobby:
            return []

        ranked = sorted(
            lobby.players.values(), key=lambda p: (-p.score, p.questions_solved)
        )
        return [{"rank": i + 1, **p.to_dict()} for i, p in enumerate(ranked)]


lobby_manager = LobbyManager()
