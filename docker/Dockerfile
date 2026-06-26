# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
RUN corepack enable pnpm
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: Build backend + bundle
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg gosu \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/src/ ./src/
COPY --from=frontend-build /app/frontend/build ./frontend/build
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV THALIMAGE_DATA_DIR=/data
ENV THALIMAGE_HOST=0.0.0.0
ENV THALIMAGE_PORT=8000

EXPOSE 8000
VOLUME /data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "thalimage.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
