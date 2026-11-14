import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Index, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameStatus(str, enum.Enum):
    WAITING = "waiting"
    STARTED = "started"
    ENDED = "ended"


class GameMode(str, enum.Enum):
    MULTIPLAYER = "multiplayer"
    ONE_V_ONE = "1v1"
    TOURNAMENT = "tournament"
    SOLO = "solo"


class Language(str, enum.Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    C = "c"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    is_admin = Column(Boolean, default=False)
    rating = Column(Integer, default=1000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Password reset fields
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # OTP fields for password reset
    reset_otp = Column(String(10), nullable=True, index=True)
    reset_otp_expires = Column(DateTime(timezone=True), nullable=True)
    reset_otp_attempts = Column(Integer, default=0)
    
    # OAuth fields
    oauth_provider = Column(String(20), nullable=True)  # google, github, apple
    oauth_provider_id = Column(String(255), nullable=True, index=True)
    profile_picture = Column(String(500), nullable=True)

    # Skill assessment & ELO fields
    skill_quiz_completed = Column(Boolean, default=False)
    peak_rating = Column(Integer, default=1000)
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)

    players = relationship("Player", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False)
    topic = Column(String(100), nullable=True)
    starter_code = Column(Text, nullable=True)
    base_points = Column(Integer, default=100)
    time_bonus = Column(Integer, default=50)
    max_execution_time_ms = Column(Integer, default=2000)
    test_cases = Column(Text, nullable=False)  # stored as JSON string
    function_name = Column(String(100), default="solve")
    parameters = Column(Text, default="[]")  # stored as JSON string
    return_type = Column(String(100), default="void")
    return_description = Column(String(255), default="The result")
    diagram = Column(Text, nullable=True)  # Base64 encoded diagram image
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lobbies = relationship("LobbyQuestion", back_populates="question")


class Lobby(Base):
    __tablename__ = "lobbies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(SQLEnum(GameStatus), default=GameStatus.WAITING)
    game_mode = Column(SQLEnum(GameMode), default=GameMode.MULTIPLAYER)
    is_public = Column(Boolean, default=False)
    max_players = Column(Integer, default=10)
    time_limit = Column(Integer, default=3600)  # seconds total

    # Match configuration
    num_rounds = Column(Integer, default=1)
    questions_per_round = Column(Integer, default=1)
    difficulty = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    topics = Column(Text, nullable=True)  # JSON array of topic strings
    time_per_question = Column(Integer, default=600)  # seconds per question
    current_round = Column(Integer, default=0)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    players = relationship("Player", back_populates="lobby", cascade="all, delete-orphan")
    questions = relationship("LobbyQuestion", back_populates="lobby", cascade="all, delete-orphan")
    tournament = relationship("Tournament", back_populates="matches")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    lobby_id = Column(Integer, ForeignKey("lobbies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    lobby = relationship("Lobby", back_populates="players")
    user = relationship("User", back_populates="players")
    submissions = relationship("Submission", back_populates="player")


class LobbyQuestion(Base):
    __tablename__ = "lobby_questions"

    id = Column(Integer, primary_key=True, index=True)
    lobby_id = Column(Integer, ForeignKey("lobbies.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    round_number = Column(Integer, default=1)
    order = Column(Integer, nullable=False)

    lobby = relationship("Lobby", back_populates="questions")
    question = relationship("Question", back_populates="lobbies")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(SQLEnum(Language), nullable=False)
    status = Column(String(20), default="pending")
    passed_tests = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    execution_time_ms = Column(Float, nullable=True)
    memory_used_kb = Column(Float, nullable=True)
    score = Column(Integer, default=0)
    round_number = Column(Integer, default=1)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    player = relationship("Player", back_populates="submissions")
    question = relationship("Question")



class UserQuestionHistory(Base):
    __tablename__ = "user_question_history"
    __table_args__ = (
        UniqueConstraint("user_id", "question_key", name="uq_user_question"),
        Index("ix_uqh_user_topic", "user_id", "topic"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # sha1 of the normalized title: the same problem keeps one key across regenerated rows
    question_key = Column(String(40), nullable=False)
    title = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=True)
    difficulty = Column(String(10), nullable=True)
    seen_at = Column(DateTime(timezone=True), server_default=func.now())


class AssessmentItem(Base):
    """One question of a player's Skill Assessment, held and graded by the server.

    The full question (with every test case) stays here; the player only ever gets the sample tests. The clock starts when
    the question is issued, and the result is filled in once, when the server has run the player's code on all tests."""
    __tablename__ = "assessment_items"
    __table_args__ = (Index("ix_assessment_user_slot", "user_id", "slot"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot = Column(Integer, nullable=False)
    difficulty = Column(String(10), nullable=False)
    skill = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    question_json = Column(Text, nullable=False)   # the generator's question, test cases included
    issued_at = Column(Float, nullable=False)      # epoch seconds
    time_limit_seconds = Column(Integer, nullable=False)

    graded_at = Column(Float, nullable=True)       # None until the player submits
    language = Column(String(20), nullable=True)
    passed_tests = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    solved = Column(Boolean, default=False)
    points_earned = Column(Integer, default=0)
    time_taken_seconds = Column(Integer, nullable=True)
    timed_out = Column(Boolean, default=False)


class IssuedQuestion(Base):
    """A generated question the server keeps in full while the browser holds the public copy (see services/hidden_tests.py)."""
    __tablename__ = "issued_questions"
    # issued_at is indexed because every generation first deletes the expired rows (WHERE issued_at < ...), which scanned the whole table
    __table_args__ = (Index("ix_issued_user", "user_id"), Index("ix_issued_at", "issued_at"))

    ref = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_json = Column(Text, nullable=False)   # the generator's question, every test case included
    issued_at = Column(Float, nullable=False)      # epoch seconds


class TournamentStatus(str, enum.Enum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(10), unique=True, index=True, nullable=False)
    status = Column(SQLEnum(TournamentStatus), default=TournamentStatus.REGISTRATION)
    max_participants = Column(Integer, default=32)
    difficulty = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    topics = Column(Text, nullable=True)
    rounds_per_match = Column(Integer, default=3)
    questions_per_round = Column(Integer, default=1)
    time_per_question = Column(Integer, default=600)
    current_bracket_round = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    participants = relationship("TournamentParticipant", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("Lobby", back_populates="tournament")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seed = Column(Integer, nullable=True)
    eliminated = Column(Boolean, default=False)
    final_rank = Column(Integer, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(10), default="star")
    tier = Column(String(20), default="bronze")  # bronze, silver, gold, platinum
    threshold = Column(Integer, default=1)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")
