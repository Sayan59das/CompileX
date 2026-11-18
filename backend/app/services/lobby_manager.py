"""Live lobbies: who is in them, the round, the questions, the scores.

A lobby used to live in a dict of this process, so a second backend process could not see it and a restart ended every game. Now each lobby is
one JSON value in the shared state (see shared_state.py: Redis when REDIS_URL is set, this process otherwise), and every change is a
read-modify-write under a per-lobby lock, so two processes updating scores at the same moment cannot lose an update.

Every method that reads or changes a lobby is a coroutine and hands back a SNAPSHOT of the lobby: reading its fields is fine, but changing them
does nothing; change a lobby only through the methods here.
"""

import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from app.models.models import GameStatus, GameMode, DifficultyLevel  # noqa: F401  (DifficultyLevel kept importable from here)
from app.services.shared_state import get_redis, locked

# A lobby is forgotten this long after its last change, and so is a socket's record of which lobby it joined.
LOBBY_TTL_SECONDS = 12 * 3600
LOCK_SECONDS = 10.0


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

    def to_stored(self):
        return {"id": self.id, "user_id": self.user_id, "username": self.username, "sid": self.sid, "score": self.score,
                "questions_solved": self.questions_solved, "finished": self.finished}


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
    # question index -> the players who have submitted for it
    question_submissions: Dict[int, List] = field(default_factory=dict)

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

    # ── what is kept in the shared state ──
    def to_json(self) -> str:
        return json.dumps({
            "id": self.id, "code": self.code, "name": self.name, "status": self.status.value, "game_mode": self.game_mode.value,
            "is_public": self.is_public, "max_players": self.max_players, "time_limit": self.time_limit, "created_by": self.created_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            # lists of records, not dicts keyed by id: JSON turns every key into text and a player's id can be a number or a socket id
            "players": [p.to_stored() for p in self.players.values()],
            "questions": self.questions,
            "leaderboard": [[player_id, score] for player_id, score in self.leaderboard.items()],
            "num_rounds": self.num_rounds, "questions_per_round": self.questions_per_round, "difficulty": self.difficulty,
            "topics": self.topics, "time_per_question": self.time_per_question, "current_round": self.current_round,
            "rounds": [r.to_dict() for r in self.rounds.values()],
            "shared_questions": self.shared_questions,
            "question_submissions": [[index, ids] for index, ids in self.question_submissions.items()],
        }, separators=(",", ":"), default=str)

    @classmethod
    def from_json(cls, text: str) -> "LobbyState":
        raw = json.loads(text)
        players = {p["id"]: PlayerState(**p) for p in raw["players"]}
        rounds = {r["round_number"]: RoundState(**r) for r in raw["rounds"]}
        return cls(
            id=raw["id"], code=raw["code"], name=raw["name"], status=GameStatus(raw["status"]), game_mode=GameMode(raw["game_mode"]),
            is_public=raw["is_public"], max_players=raw["max_players"], time_limit=raw["time_limit"], created_by=raw["created_by"],
            started_at=datetime.fromisoformat(raw["started_at"]) if raw["started_at"] else None,
            players=players, questions=raw["questions"], leaderboard={player_id: score for player_id, score in raw["leaderboard"]},
            num_rounds=raw["num_rounds"], questions_per_round=raw["questions_per_round"], difficulty=raw["difficulty"],
            topics=raw["topics"], time_per_question=raw["time_per_question"], current_round=raw["current_round"], rounds=rounds,
            shared_questions=raw["shared_questions"],
            question_submissions={index: ids for index, ids in raw["question_submissions"]},
        )


class LobbyManager:
    def __init__(self, redis=None):
        self._fixed = redis   # tests give their own; otherwise the process's shared state

    @property
    def _r(self):
        return self._fixed if self._fixed is not None else get_redis()

    # ── keys ──
    @staticmethod
    def _key(lobby_id) -> str:
        return f"lobby:{lobby_id}"

    @staticmethod
    def _code_key(code: str) -> str:
        return f"lobbycode:{str(code).upper()}"

    @staticmethod
    def _sid_key(sid: str) -> str:
        return f"sid:{sid}"

    # ── reading and changing ──
    async def _load(self, lobby_id) -> Optional[LobbyState]:
        raw = await self._r.get(self._key(lobby_id))
        return LobbyState.from_json(raw) if raw else None

    @asynccontextmanager
    async def _edit(self, lobby_id):
        """The lobby (or None) for the body to change. Nobody else changes it meanwhile, and it is saved afterwards only if something changed."""
        async with locked(f"lock:lobby:{lobby_id}", timeout=LOCK_SECONDS, wait=LOCK_SECONDS, client=self._r):
            lobby = await self._load(lobby_id)
            before = lobby.to_json() if lobby else None
            yield lobby
            if lobby is not None:
                after = lobby.to_json()
                if after != before:
                    await self._r.set(self._key(lobby_id), after, ex=LOBBY_TTL_SECONDS)

    async def generate_code(self) -> str:
        while True:
            code = uuid.uuid4().hex[:6].upper()
            if not await self._r.exists(self._code_key(code)):
                return code

    async def create_lobby(
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
        await self._r.set(self._key(lobby_id), lobby.to_json(), ex=LOBBY_TTL_SECONDS)
        await self._r.set(self._code_key(code), str(lobby_id), ex=LOBBY_TTL_SECONDS)
        await self._r.sadd("lobbies", lobby_id)
        return lobby

    async def get_lobby(self, lobby_id) -> Optional[LobbyState]:
        return await self._load(lobby_id)

    async def get_lobby_by_code(self, code: str) -> Optional[LobbyState]:
        lobby_id = await self._r.get(self._code_key(code))
        return await self._load(lobby_id) if lobby_id else None

    async def get_public_lobbies(self) -> List[LobbyState]:
        ids = sorted(await self._r.smembers("lobbies"), key=lambda i: (0, int(i)) if str(i).isdigit() else (1, str(i)))
        if not ids:
            return []
        found = []
        for lobby_id, raw in zip(ids, await self._r.mget([self._key(i) for i in ids])):
            if raw is None:
                await self._r.srem("lobbies", lobby_id)   # it expired: stop listing it
                continue
            lobby = LobbyState.from_json(raw)
            if lobby.is_public and lobby.status == GameStatus.WAITING:
                found.append(lobby)
        return found

    # ── players ──
    async def join_lobby(self, lobby_id, player_id, user_id, username, sid) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
            if not lobby or len(lobby.players) >= lobby.max_players:
                return None

            if player_id in lobby.players:
                lobby.players[player_id].sid = sid
            else:
                lobby.players[player_id] = PlayerState(id=player_id, user_id=user_id, username=username, sid=sid)
        await self._r.set(self._sid_key(sid), json.dumps({"player_id": player_id, "lobby_id": lobby_id}), ex=LOBBY_TTL_SECONDS)
        return lobby

    async def player_for_sid(self, sid: str):
        """The player this socket joined as, or None."""
        raw = await self._r.get(self._sid_key(sid))
        return json.loads(raw)["player_id"] if raw else None

    async def session_for_sid(self, sid: str) -> Optional[dict]:
        """{"player_id", "lobby_id"} for the seat this socket joined, or None."""
        raw = await self._r.get(self._sid_key(sid))
        return json.loads(raw) if raw else None

    async def leave_lobby(self, sid: str) -> Optional[LobbyState]:
        raw = await self._r.get(self._sid_key(sid))
        if not raw:
            return None
        await self._r.delete(self._sid_key(sid))
        session = json.loads(raw)
        player_id, lobby_id = session["player_id"], session.get("lobby_id")
        if not player_id or not lobby_id:
            return None
        async with self._edit(lobby_id) as lobby:
            if lobby and player_id in lobby.players:
                del lobby.players[player_id]
                return lobby
        return None

    # ── the game ──
    async def start_game(self, lobby_id) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
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
            lobby.question_submissions = {}
            return lobby

    async def start_round(self, lobby_id, round_number: int, questions: list) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
            if not lobby or lobby.status != GameStatus.STARTED:
                return None

            lobby.current_round = round_number
            lobby.rounds[round_number] = RoundState(
                round_number=round_number,
                questions=questions,
                started_at=datetime.utcnow().isoformat(),
            )
            return lobby

    async def end_round(self, lobby_id, round_number: int) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
            if not lobby:
                return None

            round_state = lobby.rounds.get(round_number)
            if round_state:
                round_state.ended = True
            return lobby

    async def advance_question(self, lobby_id) -> Optional[dict]:
        async with self._edit(lobby_id) as lobby:
            if not lobby:
                return None

            round_state = lobby.rounds.get(lobby.current_round)
            if not round_state:
                return None

            round_state.current_question_index += 1
            if round_state.current_question_index < len(round_state.questions):
                return round_state.questions[round_state.current_question_index]
            return None

    async def end_game(self, lobby_id) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
            if not lobby or lobby.status != GameStatus.STARTED:
                return None

            lobby.status = GameStatus.ENDED
            for p in lobby.players.values():
                lobby.leaderboard[p.id] = p.score
            return lobby

    async def store_question(self, lobby_id, question: dict, index: int) -> None:
        """Store a shared question so all players get the same one."""
        async with self._edit(lobby_id) as lobby:
            if not lobby:
                return
            # Extend list if needed
            while len(lobby.shared_questions) <= index:
                lobby.shared_questions.append(None)
            lobby.shared_questions[index] = question

    async def get_shared_question(self, lobby_id, index: int) -> Optional[dict]:
        lobby = await self._load(lobby_id)
        if not lobby or index >= len(lobby.shared_questions):
            return None
        return lobby.shared_questions[index]

    async def mark_player_finished(self, lobby_id, player_id) -> dict:
        """
        Mark a player as having completed all their questions.
        Returns a dict with:
          - finished_count: how many players have finished
          - total_count: total players in the lobby
          - all_done: True when every player has finished
        """
        async with self._edit(lobby_id) as lobby:
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

    async def mark_question_submitted(self, lobby_id, player_id, question_index: int) -> dict:
        """
        Track per-question submissions. Returns all_submitted=True when every
        active player has submitted for this question_index.
        """
        async with self._edit(lobby_id) as lobby:
            if not lobby:
                return {"submitted_count": 0, "total_count": 0, "all_submitted": False}

            submitted = lobby.question_submissions.setdefault(question_index, [])
            if player_id not in submitted:
                submitted.append(player_id)

            total_count = len(lobby.players)
            submitted_count = len(submitted)
            return {
                "submitted_count": submitted_count,
                "total_count": total_count,
                "all_submitted": submitted_count >= total_count,
            }

    async def reset_question_submissions(self, lobby_id, question_index: int) -> None:
        """Clear submission tracking for a question index (called when moving to next question)."""
        async with self._edit(lobby_id) as lobby:
            if lobby:
                lobby.question_submissions.pop(question_index, None)

    async def update_score(self, lobby_id, player_id, score) -> Optional[LobbyState]:
        async with self._edit(lobby_id) as lobby:
            if not lobby or player_id not in lobby.players:
                return None

            lobby.players[player_id].score += score
            lobby.players[player_id].questions_solved += 1
            lobby.leaderboard[player_id] = lobby.players[player_id].score
            return lobby

    # ── scores the server graded itself ──
    # The browser used to tell the room how many points it had earned. Now the submit request records the score the server graded, and the
    # socket's `score_update` only asks the server to apply the oldest one it has not applied yet: the browser's own number is never read.
    async def record_graded_score(self, user_id, question_id, score) -> None:
        key = f"pendingscore:{user_id}"
        async with locked(f"lock:{key}", timeout=LOCK_SECONDS, wait=LOCK_SECONDS, client=self._r):
            raw = await self._r.get(key)
            items = json.loads(raw) if raw else []
            items.append({"q": question_id, "s": int(score)})
            await self._r.set(key, json.dumps(items[-50:]), ex=3600)

    async def take_graded_score(self, user_id) -> Optional[dict]:
        """The oldest recorded {"q": question id, "s": score} for this user, removed from the record; None if there is none."""
        key = f"pendingscore:{user_id}"
        async with locked(f"lock:{key}", timeout=LOCK_SECONDS, wait=LOCK_SECONDS, client=self._r):
            raw = await self._r.get(key)
            items = json.loads(raw) if raw else []
            if not items:
                return None
            first = items.pop(0)
            if items:
                await self._r.set(key, json.dumps(items), ex=3600)
            else:
                await self._r.delete(key)
            return first

    async def apply_graded_score(self, lobby_id, player_id, question_id, score) -> Optional[LobbyState]:
        """Add a graded score to the player's total. A question counts once: sending the same solution again adds nothing, and a better
        one adds only the difference."""
        async with self._edit(lobby_id) as lobby:
            if not lobby or player_id not in lobby.players:
                return None
            best_key = f"bestscore:{lobby_id}:{player_id}"
            raw = await self._r.get(best_key)
            best = json.loads(raw) if raw else {}
            previous = best.get(str(question_id))
            gain = max(0, int(score) - (previous or 0))
            if previous is None or score > previous:
                best[str(question_id)] = int(score)
                await self._r.set(best_key, json.dumps(best), ex=LOBBY_TTL_SECONDS)
            player = lobby.players[player_id]
            player.score += gain
            if previous is None:
                player.questions_solved += 1
            lobby.leaderboard[player_id] = player.score
            return lobby

    async def get_leaderboard(self, lobby_id) -> list:
        lobby = await self._load(lobby_id)
        if not lobby:
            return []

        ranked = sorted(
            lobby.players.values(), key=lambda p: (-p.score, p.questions_solved)
        )
        return [{"rank": i + 1, **p.to_dict()} for i, p in enumerate(ranked)]


lobby_manager = LobbyManager()
