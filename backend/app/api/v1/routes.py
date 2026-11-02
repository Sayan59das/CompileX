import json
import requests
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import (
    Achievement,
    DifficultyLevel,
    GameMode,
    Lobby,
    Player,
    Question,
    Submission,
    Tournament,
    TournamentParticipant,
    TournamentStatus,
    User,
    UserAchievement,
)
from app.schemas.schemas import (
    AIPromptRequest,
    AIQuestionRequest,
    AIQuestionResponse,
    AchievementResponse,
    LobbyCreate,
    LobbyListResponse,
    LobbyResponse,
    MatchConfig,
    MatchHistoryEntry,
    MatchHistoryResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetOTPRequest,
    PasswordResetOTPVerify,
    QuestionCreate,
    QuestionResponse,
    SubmissionCreate,
    SubmissionResponse,
    Token,
    TournamentCreate,
    TournamentDetailResponse,
    TournamentResponse,
    UserCreate,
    UserResponse,
    UserStatsResponse,
    TopicStat,
    DailyProgress,
    UserProgressResponse,
)
from app.services import question_history
from app.services import starter_lock
from app.services.ai_generator import ai_generator
from app.services.code_executor import TestCase, code_executor
from app.services.lobby_manager import lobby_manager
from app.services.scoring_engine import scoring_engine

router = APIRouter()
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise exc
    except jwt.PyJWTError:
        raise exc

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise exc
    return user


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@router.post(
    "/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    if (
        await db.execute(select(User).where(User.username == user.username))
    ).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    if user.email:
        if (
            await db.execute(select(User).where(User.email == user.email))
        ).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        username=user.username,
        email=user.email if user.email else None,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login", response_model=Token)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user has a password (not OAuth-only user)
    if not user.hashed_password:
        raise HTTPException(
            status_code=401, 
            detail="This account uses OAuth sign-in. Please use Google, GitHub, or Apple to login."
        )
    
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {"sub": str(user.id)},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/forgot-password-otp")
async def forgot_password_otp(
    body: PasswordResetOTPRequest, db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset by sending OTP to email.
    Returns error if user has no email registered.
    """
    import secrets
    import random
    from datetime import datetime, timedelta
    from app.services.email_service import email_service
    
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    
    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Username not found. Please check your username and try again."
        )
    
    # Check if user has email registered
    if not user.email:
        raise HTTPException(
            status_code=400,
            detail="No email found for this account. Password reset requires an email address. Please contact support."
        )
    
    # Generate 6-digit OTP
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Set OTP expiration (10 minutes from now)
    user.reset_otp = otp
    user.reset_otp_expires = datetime.utcnow() + timedelta(minutes=10)
    user.reset_otp_attempts = 0
    await db.commit()
    
    # Send email with OTP
    email_sent = await email_service.send_otp_email(
        to_email=user.email,
        username=user.username,
        otp=otp
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please try again later."
        )
    
    return {
        "message": "OTP has been sent to your registered email address.",
        "success": True
    }



@router.post("/auth/verify-otp-reset-password")
async def verify_otp_reset_password(
    body: PasswordResetOTPVerify, db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and reset password.
    OTP must be valid and not expired.
    """
    from datetime import datetime
    
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid username or OTP"
        )
    
    # Check if OTP exists
    if not user.reset_otp:
        raise HTTPException(
            status_code=400, 
            detail="No OTP request found. Please request a new OTP."
        )
    
    # Check if OTP is expired
    if not user.reset_otp_expires or user.reset_otp_expires < datetime.utcnow():
        # Clear expired OTP
        user.reset_otp = None
        user.reset_otp_expires = None
        user.reset_otp_attempts = 0
        await db.commit()
        raise HTTPException(
            status_code=400, 
            detail="OTP has expired. Please request a new one."
        )
    
    # Check attempts (max 5 attempts)
    if user.reset_otp_attempts >= 5:
        # Clear OTP after too many attempts
        user.reset_otp = None
        user.reset_otp_expires = None
        user.reset_otp_attempts = 0
        await db.commit()
        raise HTTPException(
            status_code=400, 
            detail="Too many failed attempts. Please request a new OTP."
        )
    
    # Verify OTP
    if user.reset_otp != body.otp:
        # Increment attempts
        user.reset_otp_attempts += 1
        await db.commit()
        
        remaining = 5 - user.reset_otp_attempts
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid OTP. {remaining} attempts remaining."
        )
    
    # OTP is valid - update password
    user.hashed_password = get_password_hash(body.new_password)
    
    # Clear OTP
    user.reset_otp = None
    user.reset_otp_expires = None
    user.reset_otp_attempts = 0
    
    await db.commit()
    
    return {
        "message": "Password reset successful. You can now login with your new password.",
        "success": True
    }


@router.post("/auth/forgot-password")
async def forgot_password(
    body: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset by sending email with reset token.
    Returns error if user has no email registered.
    """
    import secrets
    from datetime import datetime, timedelta
    from app.services.email_service import email_service
    
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    
    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Username not found. Please check your username and try again."
        )
    
    # Check if user has email registered
    if not user.email:
        raise HTTPException(
            status_code=400,
            detail="No email found for this account. Password reset requires an email address. Please contact support."
        )
    
    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Set token expiration (1 hour from now)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    await db.commit()
    
    # Send email with reset link
    email_sent = await email_service.send_password_reset_email(
        to_email=user.email,
        username=user.username,
        reset_token=reset_token
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send password reset email. Please try again later."
        )
    
    return {
        "message": "A password reset link has been sent to your registered email address.",
        "success": True
    }


@router.post("/auth/reset-password")
async def reset_password(
    body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """
    Reset password using valid reset token.
    Token must exist and not be expired.
    """
    from datetime import datetime
    
    # Find user by reset token
    result = await db.execute(
        select(User).where(User.reset_token == body.reset_token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        # Clear expired token
        user.reset_token = None
        user.reset_token_expires = None
        await db.commit()
        raise HTTPException(
            status_code=400, 
            detail="Reset token has expired. Please request a new one."
        )
    
    # Update password
    user.hashed_password = get_password_hash(body.new_password)
    
    # Clear reset token
    user.reset_token = None
    user.reset_token_expires = None
    
    await db.commit()
    
    return {
        "message": "Password reset successful. You can now login with your new password.",
        "success": True
    }


# ---------------------------------------------------------------------------
# OAuth routes (Google, GitHub, Apple)
# These redirect to the provider. To enable, set credentials in .env:
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
#   GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
#   APPLE_CLIENT_ID, APPLE_TEAM_ID, APPLE_KEY_ID, APPLE_PRIVATE_KEY
# ---------------------------------------------------------------------------

from fastapi.responses import RedirectResponse

OAUTH_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "scope": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "client_id_env": "GITHUB_CLIENT_ID",
        "scope": "read:user user:email",
    },
    "apple": {
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "client_id_env": "APPLE_CLIENT_ID",
        "scope": "name email",
    },
}


@router.get("/auth/{provider}")
async def oauth_redirect(provider: str):
    """Redirect user to OAuth provider login page."""
    import urllib.parse
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown OAuth provider")

    cfg = OAUTH_PROVIDERS[provider]
    
    # Get client ID from settings (not os.getenv)
    if provider == "google":
        client_id = settings.GOOGLE_CLIENT_ID
    elif provider == "github":
        client_id = settings.GITHUB_CLIENT_ID
    elif provider == "apple":
        client_id = settings.APPLE_CLIENT_ID
    else:
        client_id = ""

    if not client_id:
        raise HTTPException(
            status_code=501,
            detail=f"{provider.title()} OAuth is not configured. "
                   f"Set {cfg['client_id_env']} in your .env file."
        )

    # Use OAUTH_REDIRECT_URI from settings, or construct from request
    redirect_uri = settings.OAUTH_REDIRECT_URI
    if not redirect_uri or redirect_uri == "http://localhost:8000/api/v1/auth/oauth/callback":
        # Fallback: construct from settings or use localhost
        redirect_uri = f"http://localhost:8000/api/v1/auth/{provider}/callback"
    else:
        # Replace 'oauth' with actual provider name
        redirect_uri = redirect_uri.replace("/oauth/callback", f"/{provider}/callback")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": cfg["scope"],
        "response_type": "code",
        "state": provider,
    }
    if provider == "apple":
        params["response_mode"] = "form_post"

    url = cfg["auth_url"] + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/auth/{provider}/callback")
async def oauth_callback(
    provider: str, 
    code: str = None, 
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """OAuth callback — exchange code for token and create/login user"""
    from app.services.oauth_service import oauth_service
    
    frontend_url = settings.FRONTEND_URL or "http://localhost:5173"
    
    if error:
        return RedirectResponse(f"{frontend_url}/?oauth_error={error}")
    
    if not code:
        return RedirectResponse(f"{frontend_url}/?oauth_error=no_code")
    
    if not oauth_service.is_provider_configured(provider):
        return RedirectResponse(
            f"{frontend_url}/?oauth_error={provider}_not_configured"
        )
    
    # Exchange code for access token
    # Use OAUTH_REDIRECT_URI from settings, or construct
    redirect_uri = settings.OAUTH_REDIRECT_URI
    if not redirect_uri or redirect_uri == "http://localhost:8000/api/v1/auth/oauth/callback":
        redirect_uri = f"http://localhost:8000/api/v1/auth/{provider}/callback"
    else:
        redirect_uri = redirect_uri.replace("/oauth/callback", f"/{provider}/callback")
    
    access_token = await oauth_service.exchange_code_for_token(
        provider, code, redirect_uri
    )
    
    if not access_token:
        return RedirectResponse(
            f"{frontend_url}/?oauth_error=token_exchange_failed"
        )
    
    # Get user info from provider
    user_info = await oauth_service.get_user_info(provider, access_token)
    
    if not user_info or not user_info.get("email"):
        return RedirectResponse(
            f"{frontend_url}/?oauth_error=no_email"
        )
    
    # Find or create user
    email = user_info["email"]
    provider_id = user_info["provider_id"]
    
    # Check if user exists with this OAuth provider
    result = await db.execute(
        select(User).where(
            User.oauth_provider == provider,
            User.oauth_provider_id == provider_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Check if user exists with this email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            # Link OAuth to existing account
            user.oauth_provider = provider
            user.oauth_provider_id = provider_id
            if user_info.get("picture"):
                user.profile_picture = user_info["picture"]
        else:
            # Create new user
            # Generate unique username from email or name
            base_username = email.split("@")[0]
            username = base_username
            counter = 1
            
            while True:
                result = await db.execute(
                    select(User).where(User.username == username)
                )
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                hashed_password=None,  # No password for OAuth users
                oauth_provider=provider,
                oauth_provider_id=provider_id,
                profile_picture=user_info.get("picture"),
            )
            db.add(user)
        
        await db.commit()
        await db.refresh(user)
    
    # Create JWT token for our app
    jwt_token = create_access_token(
        {"sub": str(user.id)},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    # Redirect to frontend with token
    return RedirectResponse(
        f"{frontend_url}/?oauth_success=true&token={jwt_token}&username={user.username}"
    )


@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res_players = await db.execute(
        select(Player).where(Player.user_id == current_user.id)
    )
    players = res_players.scalars().all()

    total_score = 0
    total_matches = len(set(p.lobby_id for p in players))

    player_ids = [p.id for p in players]
    if not player_ids:
        return UserStatsResponse(
            total_matches=0,
            questions_solved=0,
            total_score=0,
            accuracy=0.0,
            average_speed_ms=0.0,
            rating=current_user.rating,
        )

    res_subs = await db.execute(
        select(Submission).where(Submission.player_id.in_(player_ids))
    )
    submissions = res_subs.scalars().all()

    questions_solved = 0
    total_tests_passed = 0
    total_tests_attempted = 0
    execution_times = []

    for sub in submissions:
        if sub.status == "passed":
            questions_solved += 1
            if sub.execution_time_ms:
                execution_times.append(sub.execution_time_ms)
        total_tests_passed += sub.passed_tests
        total_tests_attempted += sub.total_tests
        total_score += sub.score

    avg_speed = sum(execution_times) / len(execution_times) if execution_times else 0.0
    accuracy = (
        (total_tests_passed / total_tests_attempted * 100)
        if total_tests_attempted > 0
        else 0.0
    )

    # Win rate: count lobbies where user had the highest score
    wins = 0
    lobby_ids = set(p.lobby_id for p in players)
    for lid in lobby_ids:
        lb = lobby_manager.get_leaderboard(lid)
        if lb and lb[0].get("user_id") == current_user.id:
            wins += 1
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0

    return UserStatsResponse(
        total_matches=total_matches,
        questions_solved=questions_solved,
        total_score=total_score,
        accuracy=accuracy,
        average_speed_ms=avg_speed,
        rating=current_user.rating,
        win_rate=win_rate,
    )


# ---------------------------------------------------------------------------
# Progress and Learning Curve
# ---------------------------------------------------------------------------

@router.get("/users/me/progress", response_model=UserProgressResponse)
async def get_user_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    res_players = await db.execute(
        select(Player).where(Player.user_id == current_user.id)
    )
    player_ids = [p.id for p in res_players.scalars().all()]
    if not player_ids:
        return UserProgressResponse(learning_curve=[], topic_stats=[])

    res_subs = await db.execute(
        select(Submission)
        .options(selectinload(Submission.question))
        .where(Submission.player_id.in_(player_ids))
    )
    submissions = res_subs.scalars().all()

    from collections import defaultdict
    
    # Pre-load core topics so radar chart never collapses
    core_topics = ["arrays", "strings", "trees", "dynamic programming", "graphs", "sorting", "hashing", "greedy"]
    topic_data = defaultdict(lambda: {"attempts": 0, "passed": 0, "times": []})
    for t in core_topics:
        topic_data[t] = {"attempts": 0, "passed": 0, "times": []}

    daily_data = defaultdict(int)

    for sub in submissions:
        topic = sub.question.topic if sub.question and sub.question.topic else "general"
        topic_data[topic]["attempts"] += 1
        
        if sub.status == "passed":
            topic_data[topic]["passed"] += 1
            if sub.execution_time_ms:
                topic_data[topic]["times"].append(sub.execution_time_ms)
            
            # daily tracking
            date_str = sub.submitted_at.strftime("%Y-%m-%d")
            daily_data[date_str] += 1

    topic_stats = []
    for t, d in topic_data.items():
        acc = (d["passed"] / d["attempts"] * 100) if d["attempts"] > 0 else 0.0
        avg_time = sum(d["times"]) / len(d["times"]) if d["times"] else 0.0
        topic_stats.append(TopicStat(
            topic=t,
            total_attempts=d["attempts"],
            passed=d["passed"],
            accuracy=acc,
            avg_execution_ms=avg_time
        ))

    learning_curve = []
    for date_str, solved in sorted(daily_data.items()):
        learning_curve.append(DailyProgress(date=date_str, solved=solved))

    return UserProgressResponse(
        learning_curve=learning_curve,
        topic_stats=topic_stats
    )


# ---------------------------------------------------------------------------
# Match history
# ---------------------------------------------------------------------------


@router.get("/users/me/history", response_model=MatchHistoryResponse)
async def get_match_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    res_players = await db.execute(
        select(Player).where(Player.user_id == current_user.id)
    )
    players = res_players.scalars().all()

    if not players:
        return MatchHistoryResponse(matches=[], total=0)

    player_map = {p.id: p for p in players}
    lobby_ids = list(set(p.lobby_id for p in players))

    res_lobbies = await db.execute(
        select(Lobby).where(Lobby.id.in_(lobby_ids)).order_by(desc(Lobby.created_at))
    )
    lobbies = res_lobbies.scalars().all()

    matches = []
    for lob in lobbies:
        player = next((p for p in players if p.lobby_id == lob.id), None)
        if not player:
            continue

        res_subs = await db.execute(
            select(Submission).where(Submission.player_id == player.id)
        )
        subs = res_subs.scalars().all()
        player_score = sum(s.score for s in subs)
        questions_solved = sum(1 for s in subs if s.status == "passed")

        # Get total players
        res_count = await db.execute(
            select(sa_func.count(Player.id)).where(Player.lobby_id == lob.id)
        )
        total_players = res_count.scalar() or 1

        # Rank
        lb = lobby_manager.get_leaderboard(lob.id)
        player_rank = total_players
        for entry in lb:
            if entry.get("user_id") == current_user.id:
                player_rank = entry["rank"]
                break

        matches.append(
            MatchHistoryEntry(
                lobby_id=lob.id,
                lobby_name=lob.name,
                game_mode=lob.game_mode.value if lob.game_mode else "multiplayer",
                status=lob.status.value if lob.status else "ended",
                player_score=player_score,
                player_rank=player_rank,
                total_players=total_players,
                questions_solved=questions_solved,
                played_at=lob.created_at,
            )
        )

    total = len(matches)
    matches = matches[offset : offset + limit]
    return MatchHistoryResponse(matches=matches, total=total)


# ---------------------------------------------------------------------------
# Lobby routes
# ---------------------------------------------------------------------------


@router.post(
    "/lobbies", response_model=LobbyResponse, status_code=status.HTTP_201_CREATED
)
async def create_lobby(
    lobby: LobbyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = lobby_manager.generate_code()
    mc = lobby.match_config or MatchConfig()

    # For 1v1, enforce max_players=2
    max_p = 2 if lobby.game_mode == GameMode.ONE_V_ONE else lobby.max_players

    topics_json = json.dumps(mc.topics) if mc.topics else None

    db_lobby = Lobby(
        name=lobby.name,
        code=code,
        max_players=max_p,
        time_limit=lobby.time_limit,
        game_mode=lobby.game_mode,
        is_public=lobby.is_public,
        num_rounds=mc.num_rounds,
        questions_per_round=mc.questions_per_round,
        difficulty=mc.difficulty,
        topics=topics_json,
        time_per_question=mc.time_per_question,
        created_by=current_user.id,
    )
    db.add(db_lobby)
    await db.commit()
    await db.refresh(db_lobby)

    lobby_manager.create_lobby(
        lobby_id=db_lobby.id,
        code=db_lobby.code,
        name=db_lobby.name,
        user_id=current_user.id,
        username=current_user.username,
        max_players=max_p,
        time_limit=db_lobby.time_limit,
        game_mode=lobby.game_mode,
        is_public=lobby.is_public,
        num_rounds=mc.num_rounds,
        questions_per_round=mc.questions_per_round,
        difficulty=mc.difficulty.value,
        topics=mc.topics,
        time_per_question=mc.time_per_question,
    )

    return _lobby_to_response(db_lobby, 0)


@router.get("/lobbies/public", response_model=list[LobbyListResponse])
async def list_public_lobbies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    public = lobby_manager.get_public_lobbies()
    results = []
    for lob in public:
        # Get host username
        res = await db.execute(select(User.username).where(User.id == lob.created_by))
        host_name = res.scalar() or "Unknown"
        results.append(
            LobbyListResponse(
                id=lob.id,
                code=lob.code,
                name=lob.name,
                status=lob.status,
                game_mode=lob.game_mode,
                max_players=lob.max_players,
                player_count=len(lob.players),
                difficulty=lob.difficulty,
                created_by=lob.created_by,
                host_username=host_name,
            )
        )
    return results


@router.get("/lobbies/{code}", response_model=LobbyResponse)
async def get_lobby(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lobby).where(Lobby.code == code.upper()))
    lobby = result.scalar_one_or_none()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    mem_lobby = lobby_manager.get_lobby_by_code(code.upper())
    player_count = len(mem_lobby.players) if mem_lobby else 0
    return _lobby_to_response(lobby, player_count)


@router.post("/lobbies/{lobby_id}/join")
async def join_lobby(
    lobby_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lobby).where(Lobby.id == lobby_id))
    lobby = result.scalar_one_or_none()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    result = await db.execute(
        select(Player).where(
            Player.lobby_id == lobby_id, Player.user_id == current_user.id
        )
    )
    existing = result.scalar_one_or_none()
    if not existing:
        player = Player(lobby_id=lobby_id, user_id=current_user.id)
        db.add(player)
        await db.commit()
        await db.refresh(player)
    else:
        player = existing

    return {"player_id": player.id, "lobby_code": lobby.code}


@router.get("/leaderboard")
async def global_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The top players by rating, for the dashboard's "Top Players" panel (which reads `username` and `score`)."""
    result = await db.execute(select(User).order_by(User.rating.desc(), User.id).limit(limit))
    return [
        {"username": u.username, "rating": u.rating, "score": u.rating, "games_played": u.games_played or 0, "wins": u.wins or 0}
        for u in result.scalars().all()
    ]


@router.get("/lobbies/{lobby_id}/leaderboard")
async def get_lobby_leaderboard(lobby_id: int):
    return {"leaderboard": lobby_manager.get_leaderboard(lobby_id)}


def _lobby_to_response(lobby: Lobby, player_count: int) -> LobbyResponse:
    return LobbyResponse(
        id=lobby.id,
        code=lobby.code,
        name=lobby.name,
        status=lobby.status,
        game_mode=lobby.game_mode,
        is_public=lobby.is_public,
        max_players=lobby.max_players,
        time_limit=lobby.time_limit,
        num_rounds=lobby.num_rounds,
        questions_per_round=lobby.questions_per_round,
        difficulty=lobby.difficulty,
        topics=lobby.topics,
        time_per_question=lobby.time_per_question,
        current_round=lobby.current_round,
        created_by=lobby.created_by,
        created_at=lobby.created_at,
        started_at=lobby.started_at,
        player_count=player_count,
    )


# ---------------------------------------------------------------------------
# Question routes
# ---------------------------------------------------------------------------

from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

_request_counts_minute = defaultdict(list)
_request_counts_daily = defaultdict(list)
_generation_locks = defaultdict(asyncio.Lock)

DAILY_LIMIT = 100  # Max questions per day per user


def _check_rate_limit(user_id: int, limit_per_minute: int = 10) -> tuple[bool, str]:
    """Check if user is within rate limits. Returns (allowed, message)."""
    now = datetime.utcnow()
    minute_cutoff = now - timedelta(minutes=1)
    day_cutoff = now - timedelta(days=1)

    # Clean old minute entries
    _request_counts_minute[user_id] = [
        t for t in _request_counts_minute[user_id] if t > minute_cutoff
    ]

    # Check daily limit
    _request_counts_daily[user_id] = [
        t for t in _request_counts_daily[user_id] if t > day_cutoff
    ]

    if len(_request_counts_daily[user_id]) >= DAILY_LIMIT:
        return False, f"Daily limit reached ({DAILY_LIMIT}/day). Try again tomorrow."

    if len(_request_counts_minute[user_id]) >= limit_per_minute:
        wait_seconds = 60 - (now - _request_counts_minute[user_id][0]).total_seconds()
        return False, f"Rate limit exceeded. Try again in {int(wait_seconds)} seconds."

    _request_counts_minute[user_id].append(now)
    _request_counts_daily[user_id].append(now)
    return True, ""


async def _lobby_audience(db: AsyncSession, current_user: User, lobby_id: Optional[int]) -> list[int]:
    """Users who will see a generated question: the whole lobby if the caller is in it, else just the caller."""
    if lobby_id:
        player_ids = (
            await db.execute(select(Player.user_id).where(Player.lobby_id == lobby_id))
        ).scalars().all()
        if current_user.id in player_ids:
            return list(set(player_ids))
    return [current_user.id]


@router.post("/questions/generate", response_model=AIQuestionResponse)
async def generate_question(
    request: AIQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed, msg = _check_rate_limit(current_user.id, settings.AI_RATE_LIMIT_PER_MINUTE)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    audience = await _lobby_audience(db, current_user, request.lobby_id)
    seen = await question_history.seen_titles(db, audience, request.topic)
    exclude = list(set(seen) | {t.lower().strip() for t in (request.exclude_titles or []) if t})

    # Prevent duplicate concurrent requests from same user
    async with _generation_locks[current_user.id]:
        data = await ai_generator.generate_question(
            request.difficulty,
            request.topic,
            request.num_test_cases,
            request.description,
            exclude_titles=exclude,
        )

    # In a lobby the host generates but everyone sees it, so it is recorded when broadcast.
    if not request.lobby_id:
        await question_history.record_seen(
            db, [current_user.id], data.get("base_title") or data.get("title"),
            data.get("topic"), data.get("difficulty"),
        )
    return data


@router.post("/questions/prompt", response_model=AIQuestionResponse)
async def generate_from_prompt(
    request: AIPromptRequest,
    current_user: User = Depends(get_current_user),
):
    allowed, msg = _check_rate_limit(current_user.id, settings.AI_RATE_LIMIT_PER_MINUTE)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    async with _generation_locks[current_user.id]:
        data = await ai_generator.generate_from_prompt(
            request.prompt, request.difficulty
        )
    return data


@router.get("/questions/topics")
async def get_available_topics():
    """Return all topics available for question generation."""
    # Hardcoded list — avoids a blocking HTTP call to the AI service on every request.
    # The AI service topic list is static; no need to fetch it at runtime.
    topics = [
        "arrays", "strings", "graphs", "trees", "dynamic programming",
        "sorting", "hashing", "stacks", "queues", "greedy",
        "backtracking", "recursion", "linked lists", "searching",
        "bit manipulation", "math", "two pointers", "sliding window",
    ]
    return {"topics": topics, "details": [{"topic": t, "total": 0} for t in topics]}


@router.get("/questions/limits")
async def get_limits(current_user: User = Depends(get_current_user)):
    """Get remaining question generation limits for current user."""
    now = datetime.utcnow()
    day_cutoff = now - timedelta(days=1)

    daily_count = len(
        [t for t in _request_counts_daily[current_user.id] if t > day_cutoff]
    )
    minute_count = len(
        [
            t
            for t in _request_counts_minute[current_user.id]
            if t > now - timedelta(minutes=1)
        ]
    )

    return {
        "daily_used": daily_count,
        "daily_limit": DAILY_LIMIT,
        "daily_remaining": max(0, DAILY_LIMIT - daily_count),
        "minute_used": minute_count,
        "minute_limit": settings.AI_RATE_LIMIT_PER_MINUTE,
        "resets_daily_at": (
            now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        ).isoformat(),
    }


@router.post("/questions/parse_syllabus", response_model=list[AIQuestionResponse])
async def parse_syllabus(
    file: UploadFile = File(...),
    num_questions: int = 1,
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    data = await ai_generator.parse_syllabus_and_generate(
        content, file.filename, num_questions
    )
    return data


@router.post(
    "/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED
)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_question = Question(**question.model_dump())
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    return db_question


# ---------------------------------------------------------------------------
# Submission & Execution routes
# ---------------------------------------------------------------------------

from app.schemas.schemas import (
    CustomRunRequest,
    CustomRunResponse,
    ExecutionResultSchema,
)


def _locked_code(code: str, language: str, question) -> str:
    """The code to grade: the player's part plus the harness the server holds (see services/starter_lock.py)."""
    try:
        return starter_lock.enforce(code, language, getattr(question, "starter_code", None))
    except starter_lock.LockedHarnessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute", response_model=CustomRunResponse)
async def execute_custom_run(
    req: CustomRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    test_cases = [TestCase(input_data=inp, expected_output="") for inp in req.inputs]
    
    function_signature = None
    run_code = req.code
    if req.question_id:
        result = await db.execute(select(Question).where(Question.id == req.question_id))
        question = result.scalar_one_or_none()
        if question:
            run_code = _locked_code(req.code, req.language.value, question)
        if question and question.parameters:
            try:
                params = json.loads(question.parameters) if isinstance(question.parameters, str) else question.parameters
                function_signature = {
                    "function_name": question.function_name or "solve",
                    "parameters": params,
                    "return_type": question.return_type or "int"
                }
            except Exception as e:
                print(f"[Execute] Could not parse function signature: {e}")

    execution_result = await code_executor.execute_code(
        run_code,
        req.language.value,
        test_cases,
        time_limit_ms=3000,
        function_signature=function_signature,
    )

    results = []
    for i, res in enumerate(execution_result.results):
        results.append(
            ExecutionResultSchema(
                input=req.inputs[i],
                output=res.output,
                error=res.error,
            )
        )

    return CustomRunResponse(results=results)


class DebugHintRequest(BaseModel):
    problem_statement: str
    code: str
    language: str
    test_input: str
    expected_output: str
    actual_output: str


class DebugHintResponse(BaseModel):
    status: str
    line: Optional[str]
    message: str
    hint: str


@router.post("/debug/hint", response_model=DebugHintResponse)
async def get_debug_hint(
    req: DebugHintRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a debugging hint for failed test cases using the smart analyser."""
    try:
        response = requests.post(
            f"{settings.AI_SERVICE_URL.rstrip('/')}/smart-debug",
            json={
                "problem_statement": req.problem_statement or "",
                "user_code": req.code,
                "language": req.language.lower(),
                "failed_test_input": req.test_input or "",
                "expected_output": req.expected_output or "",
                "actual_output": req.actual_output or "",
            },
            timeout=10,
        )
        if response.ok:
            data = response.json()
            return DebugHintResponse(
                status=data.get("status", "No clear logic issue detected"),
                line=str(data.get("line", "")),
                message=data.get("message", ""),
                hint=data.get("hint", ""),
            )
    except Exception:
        pass

    # Inline fallback if AI service is unreachable
    from app.services.inline_debugger import inline_debug_hint
    result = inline_debug_hint(
        problem_statement=req.problem_statement or "",
        user_code=req.code,
        language=req.language.lower(),
        failed_test_input=req.test_input or "",
        expected_output=req.expected_output or "",
        actual_output=req.actual_output or "",
    )
    return DebugHintResponse(
        status=result["status"],
        line=result["line"],
        message=result["message"],
        hint=result["hint"],
    )


@router.post(
    "/run-tests",
    response_model=dict,
)
async def run_tests(
    submission: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question).where(Question.id == submission.question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        raw_tcs = json.loads(question.test_cases)
        test_cases = [
            TestCase(input_data=str(tc.get("input", "")), expected_output=str(tc.get("output", tc.get("expected_output", ""))))
            for tc in raw_tcs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid test case format: {e}")

    if not test_cases:
        raise HTTPException(status_code=500, detail="No test cases found for this question")

    function_signature = None
    try:
        if question.parameters:
            params = json.loads(question.parameters) if isinstance(question.parameters, str) else question.parameters
            function_signature = {
                "function_name": question.function_name or "solve",
                "parameters": params,
                "return_type": question.return_type or "int"
            }
    except Exception as e:
        print(f"[RunTests] Could not parse function signature: {e}")

    execution_result = await code_executor.execute_code(
        _locked_code(submission.code, submission.language.value, question),
        submission.language.value,
        test_cases,
        question.max_execution_time_ms,
        function_signature,
    )

    test_case_details = []
    for i, (tc, res) in enumerate(zip(test_cases, execution_result.results)):
        test_case_details.append(
            {
                "index": i,
                "input": tc.input_data,
                "expected_output": tc.expected_output,
                "actual_output": res.output.strip() if res.output else "",
                "passed": res.passed,
                "error": res.error,
            }
        )

    passed = execution_result.passed_tests == execution_result.total_tests

    return {
        "status": "passed" if passed else "failed",
        "passed_tests": execution_result.passed_tests,
        "total_tests": execution_result.total_tests,
        "execution_time_ms": execution_result.execution_time_ms,
        "test_case_details": test_case_details,
    }


@router.post(
    "/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_code(
    submission: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question).where(Question.id == submission.question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    result = await db.execute(
        select(Player).where(Player.user_id == current_user.id).limit(1)
    )
    player = result.first()
    if not player:
        raise HTTPException(status_code=404, detail="Join a lobby before submitting")
    player = player[0]

    try:
        raw_tcs = json.loads(question.test_cases)
        test_cases = [
            TestCase(input_data=str(tc.get("input", "")), expected_output=str(tc.get("output", tc.get("expected_output", ""))))
            for tc in raw_tcs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid test case format: {e}")

    if not test_cases:
        raise HTTPException(status_code=500, detail="No test cases found for this question")

    # Parse function signature for function-based execution
    function_signature = None
    try:
        if question.parameters:
            params = json.loads(question.parameters) if isinstance(question.parameters, str) else question.parameters
            function_signature = {
                "function_name": question.function_name or "solve",
                "parameters": params,
                "return_type": question.return_type or "int"
            }
            print(f"[Submit] Using function signature: {function_signature['function_name']}({len(params)} params)")
    except Exception as e:
        print(f"[Submit] Could not parse function signature: {e}")

    execution_result = await code_executor.execute_code(
        _locked_code(submission.code, submission.language.value, question),
        submission.language.value,
        test_cases,
        question.max_execution_time_ms,
        function_signature,
    )

    # Build per-test-case detail for frontend
    test_case_details = []
    for i, (tc, res) in enumerate(zip(test_cases, execution_result.results)):
        test_case_details.append(
            {
                "index": i,
                "input": tc.input_data,
                "expected_output": tc.expected_output,
                "actual_output": res.output.strip() if res.output else "",
                "passed": res.passed,
                "error": res.error,
            }
        )

    # AI Logic Analysis - analyze code logic and provide partial credit
    from app.services.logic_analyzer import logic_analyzer
    
    problem_statement = f"{question.title}\n\n{question.description or question.problem_statement or ''}"
    
    logic_analysis = await logic_analyzer.analyze_logic(
        code=submission.code,
        language=submission.language.value,
        problem_statement=problem_statement,
        test_results=test_case_details,
        passed_tests=execution_result.passed_tests,
        total_tests=execution_result.total_tests
    )
    
    # Calculate final score with partial credit
    # If all tests pass, use full score
    # Otherwise, use logic correctness percentage for partial credit
    if execution_result.passed_tests == execution_result.total_tests:
        final_score = execution_result.score
    else:
        # Award partial score based on logic correctness
        # Base score from passed tests + bonus from logic analysis
        test_pass_percentage = (execution_result.passed_tests / execution_result.total_tests) * 100
        logic_percentage = logic_analysis["logic_correctness"]
        
        # Weighted average: 60% test results, 40% logic analysis
        combined_percentage = (test_pass_percentage * 0.6) + (logic_percentage * 0.4)
        
        # Scale to max score (usually 100 points per question)
        final_score = int(combined_percentage)

    passed = execution_result.passed_tests == execution_result.total_tests
    db_submission = Submission(
        player_id=player.id,
        question_id=submission.question_id,
        code=submission.code,
        language=submission.language,
        status="passed" if passed else "partial" if final_score > 0 else "failed",
        passed_tests=execution_result.passed_tests,
        total_tests=execution_result.total_tests,
        execution_time_ms=execution_result.execution_time_ms,
        score=final_score,
    )
    db.add(db_submission)
    await db.commit()
    await db.refresh(db_submission)

    # Check achievements asynchronously
    await _check_achievements(db, current_user)

    return {
        "id": db_submission.id,
        "player_id": db_submission.player_id,
        "question_id": db_submission.question_id,
        "code": db_submission.code,
        "language": db_submission.language,
        "status": db_submission.status,
        "passed_tests": db_submission.passed_tests,
        "total_tests": db_submission.total_tests,
        "execution_time_ms": db_submission.execution_time_ms,
        "score": db_submission.score,
        "submitted_at": db_submission.submitted_at,
        "test_case_details": test_case_details,
        "logic_analysis": logic_analysis,  # Include AI analysis in response
    }


# ---------------------------------------------------------------------------
# Real-time Code Analysis (before submission)
# ---------------------------------------------------------------------------

class CodeAnalysisRequest(BaseModel):
    code: str
    language: str
    problem_statement: str
    question_id: Optional[int] = None
    # Optional: pass actual test results so hints are based on real failures
    test_results: Optional[list] = None
    passed_tests: Optional[int] = None
    total_tests: Optional[int] = None


@router.post("/analyze-code")
async def analyze_code_realtime(
    request: CodeAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze code and provide hints.
    When test_results are provided (after running tests), hints are based on
    actual failures. Without test_results, performs pre-submission analysis.
    """
    from app.services.logic_analyzer import logic_analyzer

    test_results = request.test_results or []
    passed_tests = request.passed_tests if request.passed_tests is not None else 0
    total_tests  = request.total_tests  if request.total_tests  is not None else 0

    # If caller passed test_results but not the counts, derive them
    if test_results and total_tests == 0:
        total_tests  = len(test_results)
        passed_tests = sum(1 for t in test_results if t.get("passed", False))

    analysis = await logic_analyzer.analyze_logic(
        code=request.code,
        language=request.language,
        problem_statement=request.problem_statement,
        test_results=test_results,
        passed_tests=passed_tests,
        total_tests=total_tests,
    )

    return {
        "logic_correctness": analysis["logic_correctness"],
        "analysis": analysis["analysis"],
        "predicted_score": analysis["partial_score"],
        "suggestions": analysis["suggestions"],
        "breakdown": analysis.get("breakdown", {}),
        "is_pre_submission": analysis.get("is_pre_submission", False),
    }


class ComplexityAnalysisRequest(BaseModel):
    code: str
    language: str
    problem_statement: str
    # Optional execution stats from the last test run
    execution_time_ms: Optional[float] = None
    memory_kb: Optional[float] = None
    passed_tests: Optional[int] = None
    total_tests: Optional[int] = None


@router.post("/analyze-complexity")
async def analyze_complexity(
    request: ComplexityAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze time and space complexity of code.
    Optionally accepts execution stats from the last test run.
    """
    from app.services.complexity_analyzer import complexity_analyzer
    
    try:
        analysis = await complexity_analyzer.analyze(
            code=request.code,
            language=request.language,
            problem_statement=request.problem_statement,
            execution_time_ms=request.execution_time_ms,
            memory_kb=request.memory_kb,
            passed_tests=request.passed_tests,
            total_tests=request.total_tests,
        )
        
        return analysis
    except Exception as e:
        print(f"[Complexity] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "time_complexity": {
                "best": "N/A",
                "average": "N/A",
                "worst": "N/A"
            },
            "space_complexity": {
                "best": "N/A",
                "average": "N/A",
                "worst": "N/A"
            },
            "analysis": "Analysis failed. Try again.",
            "suggestions": [],
            "structured_suggestions": [],
            "verdict": "unknown",
            "verdict_explanation": "Analysis failed.",
            "is_optimal": False,
            "detected_patterns": [],
            "execution_stats": None,
        }


# ---------------------------------------------------------------------------
# AI Feedback Chat
# ---------------------------------------------------------------------------

class GrokChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class GrokFeedbackRequest(BaseModel):
    message: str                                    # current user message
    code: str = ""                                  # current editor code
    language: str = "python"
    problem_statement: str = ""
    history: list[GrokChatMessage] = []             # previous turns (oldest first)


@router.post("/ai-feedback")
async def ai_feedback(
    request: GrokFeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the AI Code Coach with the user's code + problem context.
    Returns the assistant's reply as plain text.
    """
    from app.services.grok_feedback import get_grok_service

    grok = get_grok_service()
    history = [{"role": m.role, "content": m.content} for m in request.history]

    reply = await grok.chat(
        user_message=request.message,
        code=request.code,
        language=request.language,
        problem_statement=request.problem_statement,
        conversation_history=history,
    )
    return {"reply": reply}


# ---------------------------------------------------------------------------
# Tournaments
# ---------------------------------------------------------------------------


@router.post(
    "/tournaments",
    response_model=TournamentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tournament(
    body: TournamentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = lobby_manager.generate_code()
    topics_json = json.dumps(body.topics) if body.topics else None

    tourney = Tournament(
        name=body.name,
        code=code,
        max_participants=body.max_participants,
        difficulty=body.difficulty,
        topics=topics_json,
        rounds_per_match=body.rounds_per_match,
        questions_per_round=body.questions_per_round,
        time_per_question=body.time_per_question,
        created_by=current_user.id,
    )
    db.add(tourney)
    await db.commit()
    await db.refresh(tourney)

    # Creator auto-joins
    participant = TournamentParticipant(
        tournament_id=tourney.id, user_id=current_user.id, seed=1
    )
    db.add(participant)
    await db.commit()

    return _tournament_to_response(tourney, 1)


@router.get("/tournaments", response_model=list[TournamentResponse])
async def list_tournaments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Tournament).order_by(desc(Tournament.created_at)).limit(50)
    )
    tournaments = result.scalars().all()

    responses = []
    for t in tournaments:
        res_count = await db.execute(
            select(sa_func.count(TournamentParticipant.id)).where(
                TournamentParticipant.tournament_id == t.id
            )
        )
        count = res_count.scalar() or 0
        responses.append(_tournament_to_response(t, count))
    return responses


@router.get("/tournaments/{code}", response_model=TournamentDetailResponse)
async def get_tournament(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Tournament).where(Tournament.code == code.upper()))
    tourney = result.scalar_one_or_none()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found")

    res_parts = await db.execute(
        select(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tourney.id
        )
    )
    parts = res_parts.scalars().all()

    participants = []
    for p in parts:
        res_user = await db.execute(select(User.username).where(User.id == p.user_id))
        username = res_user.scalar() or "Unknown"
        participants.append(
            {
                "user_id": p.user_id,
                "username": username,
                "seed": p.seed,
                "eliminated": p.eliminated,
                "final_rank": p.final_rank,
            }
        )

    base = _tournament_to_response(tourney, len(parts))
    return TournamentDetailResponse(
        **base.model_dump(),
        participants=participants,
        bracket=[],  # bracket generation can be added later
    )


@router.post("/tournaments/{code}/start")
async def start_tournament(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Tournament).where(Tournament.code == code.upper()))
    tourney = result.scalar_one_or_none()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tourney.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the tournament creator can start it")
    if tourney.status != TournamentStatus.REGISTRATION:
        raise HTTPException(status_code=400, detail="Tournament has already started or is completed")

    res_parts = await db.execute(
        select(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tourney.id
        )
    )
    parts = res_parts.scalars().all()
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 participants to start")

    # Assign seeds if not already set
    for i, p in enumerate(parts):
        if p.seed is None:
            p.seed = i + 1

    # Create round-1 bracket matches (pair up by seed: 1v2, 3v4, …)
    # Odd participant out gets a bye (seed them into round 2 automatically)
    import random as _random
    shuffled = list(parts)
    _random.shuffle(shuffled)

    matches_created = []
    topics_list = json.loads(tourney.topics) if tourney.topics else None

    for i in range(0, len(shuffled) - 1, 2):
        p1 = shuffled[i]
        p2 = shuffled[i + 1]

        lobby_code = lobby_manager.generate_code()
        match_lobby = Lobby(
            name=f"{tourney.name} — Match {i // 2 + 1}",
            code=lobby_code,
            max_players=2,
            time_limit=tourney.time_per_question * tourney.questions_per_round,
            game_mode=GameMode.TOURNAMENT,
            is_public=False,
            num_rounds=tourney.rounds_per_match,
            questions_per_round=tourney.questions_per_round,
            difficulty=tourney.difficulty,
            topics=tourney.topics,
            time_per_question=tourney.time_per_question,
            created_by=tourney.created_by,
            tournament_id=tourney.id,
        )
        db.add(match_lobby)
        await db.flush()  # get match_lobby.id

        # Add both players to the lobby
        for participant in (p1, p2):
            player = Player(lobby_id=match_lobby.id, user_id=participant.user_id)
            db.add(player)

        # Register lobby in memory manager
        lobby_manager.create_lobby(
            lobby_id=match_lobby.id,
            code=lobby_code,
            name=match_lobby.name,
            user_id=tourney.created_by,
            username="tournament",
            max_players=2,
            time_limit=match_lobby.time_limit,
            game_mode=GameMode.TOURNAMENT,
            is_public=False,
            num_rounds=tourney.rounds_per_match,
            questions_per_round=tourney.questions_per_round,
            difficulty=tourney.difficulty.value,
            topics=topics_list,
            time_per_question=tourney.time_per_question,
        )

        matches_created.append({
            "match": i // 2 + 1,
            "lobby_code": lobby_code,
            "player1_user_id": p1.user_id,
            "player2_user_id": p2.user_id,
        })

    # Handle bye if odd number of participants
    bye_user_id = None
    if len(shuffled) % 2 == 1:
        bye_user_id = shuffled[-1].user_id

    tourney.status = TournamentStatus.IN_PROGRESS
    tourney.current_bracket_round = 1
    from datetime import datetime as _dt
    tourney.started_at = _dt.utcnow()
    await db.commit()

    return {
        "message": "Tournament started",
        "status": "in_progress",
        "matches": matches_created,
        "bye_user_id": bye_user_id,
    }


@router.get("/tournaments/{code}/my-match")
async def get_my_match(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the lobby code for the current user's active match in this tournament."""
    result = await db.execute(select(Tournament).where(Tournament.code == code.upper()))
    tourney = result.scalar_one_or_none()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tourney.status == TournamentStatus.REGISTRATION:
        return {"lobby_code": None, "status": "registration"}

    # Find a lobby in this tournament that contains the current user
    res = await db.execute(
        select(Lobby).where(
            Lobby.tournament_id == tourney.id,
            Lobby.status != "ended",
        )
    )
    lobbies = res.scalars().all()

    for lobby in lobbies:
        res_player = await db.execute(
            select(Player).where(
                Player.lobby_id == lobby.id,
                Player.user_id == current_user.id,
            )
        )
        if res_player.scalar_one_or_none():
            return {"lobby_code": lobby.code, "status": tourney.status.value}

    return {"lobby_code": None, "status": tourney.status.value}


@router.post("/tournaments/{code}/join")
async def join_tournament(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Tournament).where(Tournament.code == code.upper()))
    tourney = result.scalar_one_or_none()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tourney.status != TournamentStatus.REGISTRATION:
        raise HTTPException(status_code=400, detail="Tournament registration is closed")

    existing = await db.execute(
        select(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tourney.id,
            TournamentParticipant.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already registered")

    count_res = await db.execute(
        select(sa_func.count(TournamentParticipant.id)).where(
            TournamentParticipant.tournament_id == tourney.id
        )
    )
    count = count_res.scalar() or 0
    if count >= tourney.max_participants:
        raise HTTPException(status_code=400, detail="Tournament is full")

    participant = TournamentParticipant(
        tournament_id=tourney.id, user_id=current_user.id, seed=count + 1
    )
    db.add(participant)
    await db.commit()

    return {"message": "Joined tournament", "seed": count + 1}


def _tournament_to_response(
    t: Tournament, participant_count: int
) -> TournamentResponse:
    return TournamentResponse(
        id=t.id,
        name=t.name,
        code=t.code,
        status=t.status.value,
        max_participants=t.max_participants,
        participant_count=participant_count,
        difficulty=t.difficulty,
        current_bracket_round=t.current_bracket_round,
        created_by=t.created_by,
        created_at=t.created_at,
    )


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

ACHIEVEMENT_DEFS = [
    {
        "key": "first_blood",
        "name": "First Blood",
        "description": "Solve your first problem",
        "icon": "sword",
        "tier": "bronze",
        "threshold": 1,
    },
    {
        "key": "sharpshooter",
        "name": "Sharpshooter",
        "description": "Solve 10 problems",
        "icon": "target",
        "tier": "silver",
        "threshold": 10,
    },
    {
        "key": "centurion",
        "name": "Centurion",
        "description": "Solve 100 problems",
        "icon": "shield",
        "tier": "gold",
        "threshold": 100,
    },
    {
        "key": "speed_demon",
        "name": "Speed Demon",
        "description": "Solve a problem in under 1 second",
        "icon": "zap",
        "tier": "silver",
        "threshold": 1,
    },
    {
        "key": "perfectionist",
        "name": "Perfectionist",
        "description": "Pass all test cases 10 times in a row",
        "icon": "check",
        "tier": "gold",
        "threshold": 10,
    },
    {
        "key": "arena_veteran",
        "name": "Arena Veteran",
        "description": "Compete in 10 matches",
        "icon": "trophy",
        "tier": "silver",
        "threshold": 10,
    },
    {
        "key": "tournament_winner",
        "name": "Tournament Winner",
        "description": "Win a tournament",
        "icon": "crown",
        "tier": "platinum",
        "threshold": 1,
    },
    {
        "key": "polyglot",
        "name": "Polyglot",
        "description": "Submit solutions in all 5 languages",
        "icon": "globe",
        "tier": "gold",
        "threshold": 5,
    },
]


@router.post("/achievements/seed")
async def seed_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for defn in ACHIEVEMENT_DEFS:
        existing = await db.execute(
            select(Achievement).where(Achievement.key == defn["key"])
        )
        if not existing.scalar_one_or_none():
            db.add(Achievement(**defn))
    await db.commit()
    return {"message": "Achievements seeded"}


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res_all = await db.execute(select(Achievement))
    all_achievements = res_all.scalars().all()

    res_user = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == current_user.id)
    )
    user_achievements = {ua.achievement_id: ua for ua in res_user.scalars().all()}

    results = []
    for a in all_achievements:
        ua = user_achievements.get(a.id)
        results.append(
            AchievementResponse(
                id=a.id,
                key=a.key,
                name=a.name,
                description=a.description,
                icon=a.icon,
                tier=a.tier,
                unlocked=ua is not None,
                unlocked_at=ua.unlocked_at if ua else None,
            )
        )
    return results


async def _check_achievements(db: AsyncSession, user: User):
    """Check and unlock achievements for the user."""
    res_all = await db.execute(select(Achievement))
    all_achievements = res_all.scalars().all()

    res_unlocked = await db.execute(
        select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)
    )
    unlocked_ids = set(res_unlocked.scalars().all())

    # Get user submissions
    res_players = await db.execute(select(Player.id).where(Player.user_id == user.id))
    player_ids = list(res_players.scalars().all())

    if not player_ids:
        return

    res_subs = await db.execute(
        select(Submission).where(Submission.player_id.in_(player_ids))
    )
    submissions = res_subs.scalars().all()

    passed_count = sum(1 for s in submissions if s.status == "passed")
    # Correctly count distinct lobbies from actual player records
    res_players_full = await db.execute(select(Player).where(Player.user_id == user.id))
    players_full = res_players_full.scalars().all()
    match_count = len(set(p.lobby_id for p in players_full))
    languages_used = set(s.language for s in submissions if s.status == "passed")
    fast_solves = any(
        s.execution_time_ms and s.execution_time_ms < 1000 and s.status == "passed"
        for s in submissions
    )

    for ach in all_achievements:
        if ach.id in unlocked_ids:
            continue

        unlocked = False
        if ach.key == "first_blood" and passed_count >= 1:
            unlocked = True
        elif ach.key == "sharpshooter" and passed_count >= 10:
            unlocked = True
        elif ach.key == "centurion" and passed_count >= 100:
            unlocked = True
        elif ach.key == "speed_demon" and fast_solves:
            unlocked = True
        elif ach.key == "polyglot" and len(languages_used) >= 5:
            unlocked = True

        if unlocked:
            db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))

    await db.commit()

# ---------------------------------------------------------------------------
# Skill Assessment & ELO
# ---------------------------------------------------------------------------

from app.services.elo_service import (
    calculate_initial_rating,
    calculate_elo_change,
    get_tier,
    get_difficulty_for_rating,
)

# ── Assessment question generation ──────────────────────────────────────────

# Maps each assessment slot to a topic + difficulty that tests a specific skill
ASSESSMENT_PLAN = [
    # slot 0 — warm-up: basic logic (always easy)
    {"difficulty": DifficultyLevel.EASY,   "topic": "arrays",               "skill": "logic"},
    # slot 1 — strings (easy/medium depending on adaptive)
    {"difficulty": DifficultyLevel.EASY,   "topic": "strings",              "skill": "strings"},
    # slot 2 — problem solving (medium)
    {"difficulty": DifficultyLevel.MEDIUM, "topic": "hashing",              "skill": "problem_solving"},
    # slot 3 — algorithms (medium/hard)
    {"difficulty": DifficultyLevel.MEDIUM, "topic": "sorting",              "skill": "algorithms"},
    # slot 4 — advanced (hard)
    {"difficulty": DifficultyLevel.HARD,   "topic": "dynamic programming",  "skill": "advanced"},
]

ADAPTIVE_DIFFICULTY_MAP = {
    # (current_slot_difficulty, passed) -> next_slot_difficulty
    (DifficultyLevel.EASY,   True):  DifficultyLevel.MEDIUM,
    (DifficultyLevel.EASY,   False): DifficultyLevel.EASY,
    (DifficultyLevel.MEDIUM, True):  DifficultyLevel.HARD,
    (DifficultyLevel.MEDIUM, False): DifficultyLevel.EASY,
    (DifficultyLevel.HARD,   True):  DifficultyLevel.HARD,
    (DifficultyLevel.HARD,   False): DifficultyLevel.MEDIUM,
}


@router.post("/skill-assessment/generate-question")
async def generate_assessment_question(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a unique AI question for the skill assessment.
    Each user gets different questions because the AI generator is seeded
    with the user_id and tracks recently seen titles.

    Body: { slot: int, difficulty_override: str|null, exclude_titles: list[str] }
    """
    slot = int(body.get("slot", 0))
    difficulty_override = body.get("difficulty_override")
    exclude_titles = body.get("exclude_titles", [])

    plan = ASSESSMENT_PLAN[min(slot, len(ASSESSMENT_PLAN) - 1)]

    # Apply adaptive difficulty override
    if difficulty_override:
        diff_map = {
            "easy":   DifficultyLevel.EASY,
            "medium": DifficultyLevel.MEDIUM,
            "hard":   DifficultyLevel.HARD,
        }
        difficulty = diff_map.get(difficulty_override, plan["difficulty"])
    else:
        difficulty = plan["difficulty"]

    topic = plan["topic"]
    skill = plan["skill"]

    # Rate limit check
    allowed, msg = _check_rate_limit(current_user.id, settings.AI_RATE_LIMIT_PER_MINUTE)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    seen = await question_history.seen_titles(db, [current_user.id], topic)
    exclude = list(set(seen) | {t.lower().strip() for t in exclude_titles if t})

    async with _generation_locks[current_user.id]:
        data = await ai_generator.generate_question(
            difficulty=difficulty,
            topic=topic,
            num_test_cases=5,
            exclude_titles=exclude,
        )

    await question_history.record_seen(
        db, [current_user.id], data.get("base_title") or data.get("title"),
        data.get("topic"), difficulty,
    )

    return {
        **data,
        "slot": slot,
        "skill_dimension": skill,
        "difficulty": difficulty.value,
        "topic": topic,
    }


class QuizResult(BaseModel):
    difficulty: str
    solved: bool
    time_taken_seconds: int
    points_earned: int = 0
    topic: str = ""
    passed_tests: int = 0
    total_tests: int = 0


class SkillAssessmentRequest(BaseModel):
    results: list[QuizResult]


@router.post("/skill-assessment")
async def submit_skill_assessment(
    body: SkillAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit skill assessment results and set the user's initial ELO rating.
    Can only be completed once per user.
    """
    if current_user.skill_quiz_completed:
        return {
            "rating": current_user.rating,
            "tier": get_tier(current_user.rating),
            "already_completed": True,
        }

    results_dicts = [r.model_dump() for r in body.results]
    new_rating = calculate_initial_rating(results_dicts)

    # Build topic skill breakdown
    topic_scores: dict[str, list[int]] = {}
    for r in results_dicts:
        topic = r.get("topic", "general")
        passed = r.get("passed_tests", 0)
        total  = r.get("total_tests", 1) or 1
        score  = int((passed / total) * 100)
        topic_scores.setdefault(topic, []).append(score)

    topic_averages = {t: int(sum(v) / len(v)) for t, v in topic_scores.items()}

    current_user.rating = new_rating
    current_user.peak_rating = new_rating
    current_user.skill_quiz_completed = True

    await db.commit()
    await db.refresh(current_user)

    return {
        "rating": new_rating,
        "tier": get_tier(new_rating),
        "topic_scores": topic_averages,
        "already_completed": False,
        "message": f"Assessment complete! Your starting rating is {new_rating}.",
    }


@router.get("/skill-assessment/status")
async def get_skill_assessment_status(
    current_user: User = Depends(get_current_user),
):
    """Check if the current user has completed the skill assessment quiz."""
    return {
        "completed": current_user.skill_quiz_completed,
        "rating": current_user.rating,
        "tier": get_tier(current_user.rating),
        "recommended_difficulty": get_difficulty_for_rating(current_user.rating),
    }


@router.get("/users/{user_id}/rating")
async def get_user_rating(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's current rating and tier (public endpoint)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.id,
        "username": user.username,
        "rating": user.rating,
        "peak_rating": user.peak_rating,
        "games_played": user.games_played,
        "wins": user.wins,
        "tier": get_tier(user.rating),
        "recommended_difficulty": get_difficulty_for_rating(user.rating),
    }


# ---------------------------------------------------------------------------
# Explainer videos (landing page "Learn More")
# ---------------------------------------------------------------------------
from fastapi import Request
from fastapi.responses import FileResponse

from app.services.video_generator import (
    VideogenUnavailable,
    find_video,
    video_generator,
)


class VideoRequest(BaseModel):
    topic: str


def _caller_key(request: Request) -> str:
    """Who to charge the generation quota to.

    The section is on the public landing page, so most callers are anonymous
    and the client IP is all there is. A signed-in visitor is keyed on their
    user id instead, which survives a changing IP. The token is only decoded —
    no database round trip — because an invalid one just falls back to the IP.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                auth[7:], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except jwt.PyJWTError:
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"


@router.post("/videos/generate")
async def generate_video(body: VideoRequest, request: Request):
    """Queue an explainer video for a topic and return its slug immediately.

    A render takes minutes, so this never waits for one: poll
    GET /videos/{slug} until the status is "ready". An already-rendered topic
    comes back ready on the first call.
    """
    try:
        return video_generator.start(body.topic, _caller_key(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except VideogenUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/videos")
async def list_videos():
    """Topics that already have a playable video."""
    return {"videos": video_generator.list_ready()}


@router.get("/videos/{slug}")
async def get_video_status(slug: str):
    state = video_generator.get(slug)
    if not state:
        raise HTTPException(
            status_code=404,
            detail="No video for that topic. POST /videos/generate first.",
        )
    return state


@router.get("/videos/{slug}/file")
async def get_video_file(slug: str):
    """Stream the rendered mp4."""
    # Rebuild the path from a re-slugified slug so a crafted value cannot walk
    # out of the media directory.
    from app.services.video_generator import slugify as _slugify

    path = find_video(_slugify(slug))
    if not path:
        raise HTTPException(status_code=404, detail="That video is not rendered yet.")
    return FileResponse(
        path,
        media_type="video/mp4",
        # Named after the topic so a download is recognisable, but inline so the
        # browser plays it in the page.
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )
