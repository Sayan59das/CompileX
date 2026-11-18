import re

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
from app.models.models import DifficultyLevel, GameStatus, GameMode, Language


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, min_length=5, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def _email_must_look_like_an_address(cls, value):
        if value is None or value == "":
            return None
        value = value.strip()
        if not re.fullmatch(r"[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[^@\s<>\"',;]+", value):
            raise ValueError("Enter a valid email address")
        return value


class UserResponse(UserBase):
    id: int
    is_admin: bool
    rating: int = 1000
    peak_rating: int = 1000
    games_played: int = 0
    wins: int = 0
    skill_quiz_completed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class QuestionBase(BaseModel):
    title: str
    description: str
    difficulty: DifficultyLevel
    topic: Optional[str] = None
    starter_code: Optional[str] = None
    base_points: int = 100
    time_bonus: int = 50
    max_execution_time_ms: int = 2000
    test_cases: str
    function_name: Optional[str] = "solve"
    parameters: Optional[str] = "[]"
    return_type: Optional[str] = "void"
    return_description: Optional[str] = "The result"
    diagram: Optional[str] = None  # Base64 encoded diagram image


class QuestionCreate(QuestionBase):
    # Set when the question came from the generator: the server then builds it from its own full copy
    ref: Optional[str] = None


class QuestionResponse(QuestionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MatchConfig(BaseModel):
    num_rounds: int = Field(1, ge=1, le=10)
    questions_per_round: int = Field(1, ge=1, le=20)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    topics: Optional[List[str]] = None
    time_per_question: int = Field(600, ge=30, le=3600)


class LobbyBase(BaseModel):
    name: str = Field(..., max_length=100)
    max_players: int = 10
    time_limit: int = 3600


class LobbyCreate(LobbyBase):
    game_mode: GameMode = GameMode.MULTIPLAYER
    is_public: bool = False
    match_config: Optional[MatchConfig] = None


class PlayerResponse(BaseModel):
    id: int
    user_id: int
    username: str = ""
    score: int = 0

    class Config:
        from_attributes = True


class LobbyResponse(LobbyBase):
    id: int
    code: str
    status: GameStatus
    game_mode: GameMode = GameMode.MULTIPLAYER
    is_public: bool = False
    num_rounds: int = 1
    questions_per_round: int = 1
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    topics: Optional[str] = None
    time_per_question: int = 600
    current_round: int = 0
    created_by: int
    created_at: datetime
    started_at: Optional[datetime] = None
    player_count: int = 0

    class Config:
        from_attributes = True


class LobbyListResponse(BaseModel):
    id: int
    code: str
    name: str
    status: GameStatus
    game_mode: GameMode
    max_players: int
    player_count: int
    difficulty: DifficultyLevel
    created_by: int
    host_username: str = ""

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    code: str
    language: Language
    question_id: int


class SubmissionResponse(BaseModel):
    id: int
    player_id: int
    question_id: int
    code: str
    language: Language
    status: str
    passed_tests: int
    total_tests: int
    execution_time_ms: Optional[float]
    score: int
    submitted_at: datetime
    test_case_details: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    username: str
    total_score: int
    questions_solved: int


class AIQuestionRequest(BaseModel):
    difficulty: DifficultyLevel
    topic: Optional[str] = None
    num_test_cases: Optional[int] = None  # Random 5-10 if not specified
    description: Optional[str] = None
    exclude_titles: Optional[list] = None  # Titles to avoid (client-side dedup)
    lobby_id: Optional[int] = None  # Avoid questions any player in this lobby has already seen


class AIPromptRequest(BaseModel):
    prompt: str
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


class AIQuestionResponse(BaseModel):
    title: str
    base_title: Optional[str] = None  # original problem title; the title shown may be reworded
    description: str
    starter_code: str
    test_cases: str
    difficulty: DifficultyLevel
    topic: Optional[str]
    function_name: Optional[str] = "solve"
    parameters: Optional[str] = "[]"
    return_type: Optional[str] = "void"
    return_description: Optional[str] = "The result"
    diagram: Optional[str] = None  # Base64 encoded image for tree/graph questions
    ref: Optional[str] = None  # hand it back to POST /questions; the tests here are the public copy


class TopicStat(BaseModel):
    topic: str
    total_attempts: int
    passed: int
    accuracy: float
    avg_execution_ms: float

class DailyProgress(BaseModel):
    date: str
    solved: int

class UserProgressResponse(BaseModel):
    learning_curve: list[DailyProgress]
    topic_stats: list[TopicStat]

class UserStatsResponse(BaseModel):
    total_matches: int
    questions_solved: int
    total_score: int
    accuracy: float
    average_speed_ms: float
    rating: int = 1000
    win_rate: float = 0.0


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=6)


class PasswordResetOTPRequest(BaseModel):
    username: str


class PasswordResetOTPVerify(BaseModel):
    username: str
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


class CustomRunRequest(BaseModel):
    code: str
    language: Language
    inputs: List[str]
    question_id: Optional[int] = None


class ExecutionResultSchema(BaseModel):
    input: str
    output: str
    error: Optional[str]


class CustomRunResponse(BaseModel):
    results: List[ExecutionResultSchema]


# Tournament schemas
class TournamentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    max_participants: int = Field(32, ge=2, le=128)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    topics: Optional[List[str]] = None
    rounds_per_match: int = Field(3, ge=1, le=5)
    questions_per_round: int = Field(1, ge=1, le=3)
    time_per_question: int = Field(600, ge=60, le=3600)


class TournamentResponse(BaseModel):
    id: int
    name: str
    code: str
    status: str
    max_participants: int
    participant_count: int = 0
    difficulty: DifficultyLevel
    current_bracket_round: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class TournamentDetailResponse(TournamentResponse):
    participants: List[dict] = []
    bracket: List[dict] = []


# Match history
class MatchHistoryEntry(BaseModel):
    lobby_id: int
    lobby_name: str
    game_mode: str
    status: str
    player_score: int
    player_rank: int
    total_players: int
    questions_solved: int
    played_at: datetime


class MatchHistoryResponse(BaseModel):
    matches: List[MatchHistoryEntry]
    total: int


# Achievements
class AchievementResponse(BaseModel):
    id: int
    key: str
    name: str
    description: str
    icon: str
    tier: str
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None

    class Config:
        from_attributes = True
