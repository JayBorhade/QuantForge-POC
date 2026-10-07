"""QuantForge FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.core.config import get_settings
from app.core.csrf import CSRF_COOKIE, is_csrf_exempt, set_csrf_cookie, validate_csrf
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.api.routes.websocket import init_websocket_manager

    init_websocket_manager()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="QuantForge — Build, Backtest, Automate, Scale",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        set(settings.cors_origins + [settings.frontend_url, "http://127.0.0.1:3000"])
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    validate_csrf(request)
    response = await call_next(request)
    if (
        request.method == "GET"
        and request.url.path.startswith(settings.api_v1_prefix)
        and not is_csrf_exempt(request.url.path)
        and not request.cookies.get(CSRF_COOKIE)
    ):
        set_csrf_cookie(response)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request):
    return {"status": "healthy", "app": settings.app_name, "env": settings.app_env}


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "tagline": "Build, Backtest, Automate, Scale",
        "docs": f"{settings.backend_url}/api/docs",
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.debug:
        raise exc
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
