"""FastAPI application factory."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import Scope

from thalimage.api import backups, collections, docs, elo, images, sources, tags, version
from thalimage.api import settings as user_settings
from thalimage.compression import TextCompression
from thalimage.config import get_settings
from thalimage.csrf import CrossSiteWriteGuard
from thalimage.db.engine import connect, migrate
from thalimage.services.db_backup import BackupScheduler
from thalimage.services.scan_manager import ScanManager
from thalimage.version import version_info

logger = logging.getLogger(__name__)

# Files under _app/immutable/ carry a content hash in their name, so a cached
# copy can never be stale. Everything else, index.html above all, is
# revalidated on each load: a cached page keeps loading the previous build.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"


class BuildAssets(StaticFiles):
    """The SPA's /_app tree, with caching set per file."""

    def file_response(
        self,
        full_path: "os.PathLike[str] | str",
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        relative = os.path.relpath(full_path, str(self.directory))
        immutable = relative.split(os.sep)[0] == "immutable"
        response.headers["Cache-Control"] = IMMUTABLE_CACHE if immutable else REVALIDATE
        return response


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
    app.state.backup_scheduler = BackupScheduler(
        settings.resolved_db_path, settings.resolved_backup_dir
    )
    app.state.backup_scheduler.start()
    try:
        yield
    finally:
        await app.state.backup_scheduler.stop()


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
        # A JSON body must be sent as application/json. A cross-site form can
        # only send "simple" content types, so this keeps JSON endpoints out
        # of its reach without a preflight. FastAPI's default today, but not
        # in every release the dependency range once allowed.
        strict_content_type=True,
    )

    config = get_settings()

    # Added first, so it runs innermost: compresses what the app answers.
    app.add_middleware(TextCompression)

    # Reject requests with an unexpected Host header (DNS-rebinding defense).
    # Loopback is always allowed; operators add the hostnames clients use.
    allowed_hosts = ["localhost", "127.0.0.1", *config.allowed_hosts]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_origins = config.cors_origins
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Added last, so it runs first: a foreign page's write is refused before
    # CORS or routing see it (SEC-002).
    app.add_middleware(
        CrossSiteWriteGuard,
        allowed_hosts=allowed_hosts,
        allowed_origins=cors_origins,
    )

    app.include_router(backups.router, prefix="/api/v1")
    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(images.router, prefix="/api/v1")
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(elo.router, prefix="/api/v1")
    app.include_router(tags.router, prefix="/api/v1")
    app.include_router(user_settings.router, prefix="/api/v1")
    app.include_router(docs.router, prefix="/api/v1")
    app.include_router(version.router, prefix="/api/v1")

    # Serve built frontend as static files (SPA with fallback to index.html)
    frontend_dir = config.resolved_frontend_dir
    if not (frontend_dir / "index.html").is_file():
        logger.warning(
            "No frontend build at %s: serving the API only."
            " Build it (make fe-build) or set THALIMAGE_FRONTEND_DIR.",
            frontend_dir,
        )
    else:
        app.mount("/_app", BuildAssets(directory=frontend_dir / "_app"), name="static")

        frontend_root = frontend_dir.resolve()

        @app.get("/{path:path}")
        async def spa_fallback(path: str) -> FileResponse:
            # The API namespace is not the SPA's to answer for: an unmatched
            # endpoint must report a JSON 404, not index.html with a 200.
            if path == "api" or path.startswith("api/"):
                raise HTTPException(404, "Not found")
            file = (frontend_root / path).resolve()
            headers = {"Cache-Control": REVALIDATE}
            if file.is_file() and file.is_relative_to(frontend_root):
                return FileResponse(file, headers=headers)
            return FileResponse(frontend_root / "index.html", headers=headers)

    return app
