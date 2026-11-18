from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    APP_NAME: str = "CompileX"
    DEBUG: bool = True

    # sqlite for local dev, swap to postgres in prod
    DATABASE_URL: str = "sqlite+aiosqlite:///./CompileX.db"

    # PostgreSQL credentials (for Docker)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "CompileX"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # redis://host:6379/0. When set, lobbies, rate limits, generation locks and socket rooms are shared between every backend process, so
    # more than one can run. Empty (the default) keeps all of that in this one process, exactly as before.
    REDIS_URL: str = ""

    # change this before going to production
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # AI Service
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: int = 15  # reduced from 30s — fail fast and use local fallback
    AI_RATE_LIMIT_PER_MINUTE: int = 10
    AI_BACKEND: str = "ai_service"
    
    # Google Gemini API (no longer used - kept for backward compatibility)
    GOOGLE_API_KEY: str = ""

    # NVIDIA NIM API (for AI feedback chat)
    NVIDIA_API_KEY: str = ""

    # Anthropic (explainer-video generation — see videogen/)
    ANTHROPIC_API_KEY: str = ""

    # Explainer videos. The renderer is the repo's videogen/ CLI, driven as a
    # child process. It needs manim, manim-voiceover and ffmpeg, which the API
    # server itself does not, so VIDEOGEN_PYTHON points at the interpreter that
    # has them (e.g. videogen/.venv/Scripts/python.exe). Left empty, the API
    # server's own interpreter is used and generation reports what is missing.
    VIDEOGEN_DIR: str = ""
    VIDEOGEN_PYTHON: str = ""
    VIDEOGEN_QUALITY: str = "m"   # l=480p m=720p h=1080p k=4K
    VIDEOGEN_FPS: int = 30
    VIDEOGEN_MINUTES: float = 4.0
    VIDEOGEN_EFFORT: str = "high"
    VIDEOGEN_RATE_LIMIT_PER_HOUR: int = 3  # cold renders per caller; 0 disables

    # NVIDIA NIM API specifically for complexity analyzer
    COMPLEXITY_NVIDIA_API_KEY: str = ""

    # Docker for code execution
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    CODE_EXECUTION_TIMEOUT: int = 10
    MAX_MEMORY_MB: int = 256
    # How many submissions may be running in sandboxes at once on this machine. Each one is a container of up to MAX_MEMORY_MB, so
    # the default keeps the worst case near 2 GB. The rest wait their turn instead of all starting together.
    MAX_CONCURRENT_EXECUTIONS: int = 8
    # In front of that line (app/services/execution_gate.py, shared by every backend process): how many submissions one player may have
    # running or waiting, and how many may be running or waiting in all before the next one is refused with 429 instead of queued.
    MAX_EXECUTIONS_PER_USER: int = 2
    MAX_EXECUTION_BACKLOG: int = 200
    # The judge service (judge/): when JUDGE_URL is set, players' code runs there, not on this machine, and this process needs no Docker.
    JUDGE_URL: str = ""
    JUDGE_TOKEN: str = ""
    JUDGE_TIMEOUT_SECONDS: int = 90
    # "process": this process (the judge) runs players' code itself as unprivileged throwaway users, with limits and no internet sockets,
    # for machines that cannot run Docker (see services/process_sandbox.py). Empty: use Docker.
    SANDBOX_MODE: str = ""
    # Worker threads that draw graph and tree diagrams (CPU work, kept off the event loop and off the code-execution threads).
    DIAGRAM_WORKERS: int = 2

    # CORS — comma-separated list of allowed frontend origins.
    # In production set this to your Vercel URL, e.g.:
    #   ALLOWED_ORIGINS=https://CompileX.vercel.app,https://your-domain.com
    # Leave empty to allow all origins (dev only).
    ALLOWED_ORIGINS: str = ""
    
    # Email Configuration (for password reset)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "CompileX"
    FRONTEND_URL: str = "http://localhost:5173"
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""
    
    # OAuth Redirect URIs
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/callback"

    # Supabase (optional — set DATABASE_URL to Supabase connection string to use it)
    # Get from: https://supabase.com/dashboard → project → Settings → Database
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    def get_allowed_origins(self) -> List[str]:
        """Return parsed list of allowed origins, or ['*'] if not set."""
        if not self.ALLOWED_ORIGINS.strip():
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


# cached so we don't re-read the env file on every request
@lru_cache()
def get_settings() -> Settings:
    return Settings()
