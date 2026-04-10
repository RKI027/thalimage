"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from thalimage.api import images, sources, collections
from thalimage.config import get_settings
from thalimage.db.engine import connect, migrate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.ensure_dirs()
    conn = connect(settings.resolved_db_path, check_same_thread=False)
    migrate(conn)
    app.state.db = conn
    app.state.settings = settings
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

    return app
