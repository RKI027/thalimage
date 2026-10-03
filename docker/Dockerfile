# Stage 1: build the SPA bundle
FROM node:24-slim AS frontend-build

# Stamped into the bundle by buildCommit() in vite.config.ts, so a stale
# frontend can be spotted against the commit the backend reports.
ARG THALIMAGE_COMMIT=""
ENV THALIMAGE_COMMIT=$THALIMAGE_COMMIT

# Installs the pnpm version pinned by packageManager in package.json.
RUN corepack enable pnpm
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build


# Stage 2: runtime
FROM python:3.11-slim AS runtime

ARG THALIMAGE_COMMIT=""
ENV THALIMAGE_COMMIT=$THALIMAGE_COMMIT

# ffmpeg/ffprobe back video thumbnails and probing (core/video.py);
# gosu drops privileges in the entrypoint.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg gosu \
    && rm -rf /var/lib/apt/lists/* \
    && command -v groupadd && command -v useradd

COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv

# The app finds the SPA through THALIMAGE_FRONTEND_DIR (set below), so
# it serves the UI whether the project is installed editable (uv sync's
# default) or not. Without it, the default is frontend/build in a source
# checkout, which an installed package does not have.
WORKDIR /app/backend

# Dependencies first, without the project itself — its source has not
# been copied yet and hatchling would have nothing to build.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ ./src/
# pyproject.toml names it in license-files (backend/LICENSE is a symlink
# to it in the repository, which COPY does not follow out of backend/).
COPY LICENSE ./LICENSE
RUN uv sync --frozen --no-dev

COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV THALIMAGE_DATA_DIR=/data
ENV THALIMAGE_FRONTEND_DIR=/app/frontend/build
ENV THALIMAGE_HOST=0.0.0.0
ENV THALIMAGE_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/app/backend/.venv/bin/python", "-c", \
         "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/version', timeout=4)"]

ENTRYPOINT ["/entrypoint.sh"]

# The console script from [project.scripts]; it reads host, port and
# debug from the settings. Single process by design — scan progress and
# the one-scan-per-source guard live in memory (ScanManager), so do not
# add uvicorn --workers.
CMD ["/app/backend/.venv/bin/thalimage"]
