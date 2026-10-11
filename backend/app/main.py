import secrets
import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.v1.routes import router as api_router

settings = get_settings()

# ── Startup validation ────────────────────────────────────────────────────────
def _validate_settings():
    warnings = []
    if not settings.SECRET_KEY:
        # Auto-generate for dev so the server doesn't crash; log a loud warning
        settings.__dict__["SECRET_KEY"] = secrets.token_hex(32)
        warnings.append(
            "SECRET_KEY is not set — generated a random one for this session. "
            "Set SECRET_KEY in your .env file to persist sessions across restarts."
        )
    if settings.SECRET_KEY in (
        "codearena-super-secret-key-change-in-production",
        "changeme",
        "secret",
    ):
        warnings.append(
            "SECRET_KEY is using an insecure default. "
            "Set a strong random value in production."
        )
    for w in warnings:
        print(f"[CONFIG WARNING] {w}")

_validate_settings()

# ── Socket.IO ─────────────────────────────────────────────────────────────────
allowed_origins = settings.get_allowed_origins()
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=allowed_origins if allowed_origins != ["*"] else "*",
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app_http = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app_http.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fix for Python 3.14 urllib compatibility — force Connection: close
class ConnectionCloseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Connection"] = "close"
        return response


app_http.add_middleware(ConnectionCloseMiddleware)
app_http.include_router(api_router, prefix="/api/v1")


@app_http.on_event("startup")
async def on_startup():
    await init_db()
    from app.services.websocket_handler import register_socket_events
    register_socket_events(sio)
    origins = settings.get_allowed_origins()
    print(f"[CORS] Allowed origins: {origins}")


@app_http.get("/")
async def root():
    return {"message": "CodeArena API", "status": "running"}


@app_http.get("/health")
async def health():
    return {"status": "healthy"}


# Wrap FastAPI inside the Socket.IO ASGI app so both share the same port.
# Socket.IO claims /socket.io/*, everything else falls through to FastAPI.
app = socketio.ASGIApp(sio, other_asgi_app=app_http)
