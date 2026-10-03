"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from thalimage.api import collections, docs, elo, images, sources, tags, version
from thalimage.api import settings as user_settings
from thalimage.config import get_settings
from thalimage.db.engine import connect, migrate
from thalimage.services.scan_manager import ScanManager
from thalimage.version import version_info

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "build"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.ensure_dirs()
    conn = connect(settings.resolved_db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
    # Requests open their own connections (deps.get_db).
    app.state.db_path = settings.resolved_db_path
    app.state.settings = settings
    app.state.scan_manager = ScanManager(concurrent=settings.concurrent_scans)
    yield


def create_app() -> FastAPI:
    # The OpenAPI explorer sits under /api, alongside the API it describes:
    # /docs is the in-app documentation the SPA serves to users.
    app = FastAPI(
        title="Thalimage",
        version=version_info().version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    config = get_settings()

    # Reject requests with an unexpected Host header (DNS-rebinding defense).
    # Loopback is always allowed; operators add the hostnames clients use.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", *config.allowed_hosts],
    )

    cors_origins = config.cors_origins
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(images.router, prefix="/api/v1")
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(elo.router, prefix="/api/v1")
    app.include_router(tags.router, prefix="/api/v1")
    app.include_router(user_settings.router, prefix="/api/v1")
    app.include_router(docs.router, prefix="/api/v1")
    app.include_router(version.router, prefix="/api/v1")

    # Serve built frontend as static files (SPA with fallback to index.html)
    frontend_dir = FRONTEND_DIR
    if frontend_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=frontend_dir / "_app"), name="static")

        frontend_root = frontend_dir.resolve()

        @app.get("/{path:path}")
        async def spa_fallback(path: str) -> FileResponse:
            # The API namespace is not the SPA's to answer for: an unmatched
            # endpoint must report a JSON 404, not index.html with a 200.
            if path == "api" or path.startswith("api/"):
                raise HTTPException(404, "Not found")
            file = (frontend_root / path).resolve()
            if file.is_file() and file.is_relative_to(frontend_root):
                return FileResponse(file)
            return FileResponse(frontend_root / "index.html")

    return app
