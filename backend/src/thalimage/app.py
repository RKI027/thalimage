"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from thalimage.api import collections, elo, images, sources
from thalimage.config import get_settings
from thalimage.db.engine import connect, migrate
from thalimage.services.scan_manager import ScanManager

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "build"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.ensure_dirs()
    conn = connect(settings.resolved_db_path, check_same_thread=False)
    migrate(conn)
    app.state.db = conn
    app.state.settings = settings
    app.state.scan_manager = ScanManager(concurrent=settings.concurrent_scans)
    yield
    conn.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Thalimage", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(images.router, prefix="/api/v1")
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(elo.router, prefix="/api/v1")

    # Serve built frontend as static files (SPA with fallback to index.html)
    frontend_dir = FRONTEND_DIR
    if frontend_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=frontend_dir / "_app"), name="static")

        @app.get("/{path:path}")
        async def spa_fallback(path: str) -> FileResponse:
            file = frontend_dir / path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(frontend_dir / "index.html")

    return app
