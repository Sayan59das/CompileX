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
_sio_options = dict(
    async_mode="asgi",
    cors_allowed_origins=allowed_origins if allowed_origins != ["*"] else "*",
)
if settings.REDIS_URL.strip():
    # Several backend processes: a message sent to a room by one reaches the players connected to the others through Redis.
    # The browser connects by WebSocket first (frontend/src/services/socket.js); a client that falls back to long-polling needs the load
    # balancer to keep its requests on one process (sticky sessions).
    _sio_options["client_manager"] = socketio.AsyncRedisManager(settings.REDIS_URL.strip())
sio = socketio.AsyncServer(**_sio_options)

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
    if settings.REDIS_URL.strip():
        # Several processes starting together on a new database would all create its tables at once and collide: one at a time.
        from app.services.shared_state import locked

        async with locked("lock:init-db", timeout=120, wait=120):
            await init_db()
    else:
        await init_db()
    from app.services.websocket_handler import register_socket_events
    register_socket_events(sio)
    origins = settings.get_allowed_origins()
    print(f"[CORS] Allowed origins: {origins}")


@app_http.get("/")
async def root():
    return {"message": "CodeArena API", "status": "running"}


# GET and HEAD: uptime monitors (UptimeRobot's free plan) check with HEAD, and a 405 there reads as "down".
@app_http.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "healthy"}


# Wrap FastAPI inside the Socket.IO ASGI app so both share the same port.
# Socket.IO claims /socket.io/*, everything else falls through to FastAPI.
app = socketio.ASGIApp(sio, other_asgi_app=app_http)
