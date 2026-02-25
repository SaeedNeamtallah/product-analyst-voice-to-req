"""
Main FastAPI Application.
Entry point for the Tawasul backend API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
import time
import uuid

try:
    from fastapi.responses import ORJSONResponse
    _default_response = ORJSONResponse
except ImportError:
    _default_response = None
# Configure logging
from backend.config import settings
import logging

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

    _metrics_enabled = True
    _request_counter = Counter(
        "tawasul_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    _request_latency = Histogram(
        "tawasul_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
except Exception:  # noqa: BLE001
    _metrics_enabled = False
    _request_counter = None
    _request_latency = None

from backend.database import init_db, close_db
from backend.routes import projects, documents, query, health, stats, bot_config, app_config, stt, srs, messages, interview, judge
from backend.routes import auth
from backend.routes import handoff


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Tawasul API...")
    settings.validate_startup_or_raise()
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    yield
    
    # Shutdown
    logger.info("Shutting down Tawasul API...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
_app_kwargs = {
    "title": settings.api_title,
    "version": settings.api_version,
    "description": """
    Tawasul - AI Requirements Engineering Platform
    
    A transcript-first requirements and Q&A API using:
    - Google Gemini 2.5 Flash for LLM capabilities
    - PostgreSQL for project data, chat history, and SRS drafts
    - Document transcript extraction (PDF, DOCX, TXT)
    
    ## Features
    - Project-based document organization
    - Multi-format document support (PDF, TXT, DOCX)
    - Transcript-grounded question answering with sources
    - Guided interview workflow for requirements gathering
    - Automated SRS draft generation and PDF export
    - Multi-language support (Arabic/English)
    """,
    "lifespan": lifespan,
}
if _default_response:
    _app_kwargs['default_response_class'] = _default_response
app = FastAPI(**_app_kwargs)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def request_observability_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    elapsed_seconds = max(0.0, elapsed_ms / 1000.0)

    route_path = request.url.path
    route = request.scope.get("route")
    if route is not None:
        normalized = getattr(route, "path", None)
        if isinstance(normalized, str) and normalized:
            route_path = normalized

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = str(elapsed_ms)

    if _metrics_enabled and _request_counter is not None and _request_latency is not None:
        method = request.method
        status = str(response.status_code)
        _request_counter.labels(method=method, path=route_path, status=status).inc()
        _request_latency.labels(method=method, path=route_path).observe(elapsed_seconds)

    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    if not _metrics_enabled:
        return Response(
            content="# metrics_disabled prometheus_client_not_installed\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
            status_code=503,
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(stats.router)
app.include_router(bot_config.router)
app.include_router(app_config.router)
app.include_router(stt.router)
app.include_router(srs.router)
app.include_router(messages.router)
app.include_router(interview.router)
app.include_router(judge.router)
app.include_router(handoff.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
