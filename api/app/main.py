"""ObserveML API — v2.0.0

Security middleware stack (execution order, outermost → innermost):
  1. TrustedHostMiddleware  — rejects spoofed Host headers (if TRUSTED_HOSTS set)
  2. IPRateLimitMiddleware  — per-IP sliding window; blocks brute-force key guessing
  3. CORSMiddleware         — explicit allow-list; never wildcard
  4. Routers                — API key auth + per-org rate limit on every endpoint
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.db.clickhouse import ensure_table
from app.db.postgres import init_db
from app.routers import (
    alerts,
    billing,
    compare,
    ingest,
    intelligence,
    metrics,
    org,
    stream,
    teams,
)
from app.services.rate_limiter import is_ip_rate_limited


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    ensure_table()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ObserveML API",
    version="2.0.0",
    description="LLM observability ingest and metrics API — metadata only, never prompt content",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware stack
# add_middleware() prepends — last added = outermost (first executed).
# Order added: CORS (inner) → IPRateLimit (middle) → TrustedHost (outer)
# ---------------------------------------------------------------------------

# 3 — CORS: exact origin allow-list, never wildcard.
#     In production set CORS_ORIGINS env var to your actual frontend domain(s).
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key", "Authorization"],
    allow_credentials=False,  # never True with an explicit origin list this wide
    max_age=600,
)


# 2 — IP Rate Limit: pre-auth, global, protects all endpoints from DoS and
#     brute-force API-key enumeration.
class IPRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # /health is exempt so load-balancer probes never self-block
        if request.url.path == "/health":
            return await call_next(request)
        # Respect X-Forwarded-For set by a trusted reverse proxy (Caddy / Fly.io)
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )
        if is_ip_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Too many requests from this IP address. "
                        f"Limit: {settings.ip_rate_limit_per_minute} req/min. "
                        "Retry after 60 s."
                    )
                },
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


app.add_middleware(IPRateLimitMiddleware)

# 1 — Trusted Hosts: rejects requests with a spoofed Host header.
#     Only active when TRUSTED_HOSTS env var is set (non-empty).
#     Example: TRUSTED_HOSTS="api.observeml.io,api.yourdomain.com"
if settings.trusted_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in settings.trusted_hosts.split(",") if h.strip()],
    )

# ---------------------------------------------------------------------------
# Routers — every endpoint below requires x-api-key (see each router for impl)
# ---------------------------------------------------------------------------

app.include_router(ingest.router, prefix="/v1", tags=["ingest"])
app.include_router(metrics.router, prefix="/v1", tags=["metrics"])
app.include_router(alerts.router, prefix="/v1", tags=["alerts"])
app.include_router(compare.router, prefix="/v1", tags=["compare"])
app.include_router(stream.router, prefix="/v1", tags=["stream"])
app.include_router(teams.router, prefix="/v1", tags=["teams"])
app.include_router(billing.router, prefix="/v1", tags=["billing"])
app.include_router(org.router, prefix="/v1", tags=["org"])
app.include_router(intelligence.router, prefix="/v1", tags=["intelligence"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
