# Stage 1: build the SPA bundle
FROM node:24-slim AS frontend-build

# Stamped into the bundle by buildCommit() in vite.config.ts, so a stale
# frontend can be spotted against the commit the backend reports.
ARG THALIMAGE_COMMIT=""
ENV THALIMAGE_COMMIT=$THALIMAGE_COMMIT

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

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# The repo layout is preserved on purpose: app.py derives the SPA
# directory, and version.py its repo root, from four parents above
# backend/src/thalimage/. Flattening away the backend/ level makes the
# app serve the API only.
WORKDIR /app/backend

# Dependencies first, without the project itself — its source has not
# been copied yet and hatchling would have nothing to build.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ ./src/
RUN uv sync --frozen --no-dev

COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV THALIMAGE_DATA_DIR=/data
ENV THALIMAGE_HOST=0.0.0.0
ENV THALIMAGE_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/app/backend/.venv/bin/python", "-c", \
         "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/version', timeout=4)"]

ENTRYPOINT ["/entrypoint.sh"]

# The console script from [project.scripts]; it reads host, port and
# debug from the settings. Single process by design — app.py keeps one
# sqlite3.Connection on app.state with check_same_thread=False, so do
# not add uvicorn --workers.
CMD ["/app/backend/.venv/bin/thalimage"]
