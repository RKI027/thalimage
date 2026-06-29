# Thalimage

Self-hosted image browser and manager for AI-generated images. Privacy-first, local-only — no cloud, no telemetry, your images stay on your machine.

## Features

- **Source folder scanning** — point at directories containing images; Thalimage indexes them, extracts metadata, and generates thumbnails
- **AI metadata extraction** — reads generation parameters (prompt, seed, sampler, model, etc.) from PNG text chunks, EXIF, and Stable Diffusion formats via sd-parsers
- **Virtual scrolling gallery** — handles thousands of images without DOM bloat
- **Source filtering** — browse all images or filter by source folder
- **Collections** — organize images into named collections
- **Single image view** — full-size display with keyboard navigation (arrow keys, Escape) and a metadata panel showing file info, AI parameters, and raw PNG text
- **Content-addressed storage** — images identified by SHA-256 hash, so duplicates across sources are detected automatically
- **WebP thumbnails** — fast grid loading with on-demand thumbnail generation

## Deployment

### Docker (recommended)

```bash
cd docker

# Edit docker-compose.yml to set your image paths and PUID/PGID
vim docker-compose.yml

docker compose up -d
```

The compose file mounts image folders read-only at `/images`. The app stores its database and thumbnail cache in a named volume at `/data`.

**Multiple source directories**: mount each one separately and add them as sources in the Settings UI:

```yaml
volumes:
  - /photos/ai:/images/ai:ro
  - /photos/comfy:/images/comfy:ro
```

Then in Settings, add `/images/ai` and `/images/comfy` as sources.

**File permissions**: set `PUID` and `PGID` to match the owner of your image files on the host so the container can read them:

```bash
# Find your UID/GID
id -u  # PUID
id -g  # PGID
```

### Configuration

All settings can be set via environment variables with the `THALIMAGE_` prefix, or in a TOML file at `~/.thalimage/config.toml`.

| Variable | Default | Description |
|---|---|---|
| `THALIMAGE_DATA_DIR` | `~/.thalimage` | Database and cache directory |
| `THALIMAGE_DB_PATH` | `{data_dir}/thalimage.db` | SQLite database path |
| `THALIMAGE_THUMB_DIR` | `{data_dir}/cache/thumbs` | Thumbnail storage path |
| `THALIMAGE_HOST` | `127.0.0.1` | Server bind address (the Docker image sets `0.0.0.0`) |
| `THALIMAGE_PORT` | `8000` | Server port |
| `THALIMAGE_DEBUG` | `false` | Debug mode |
| `THALIMAGE_CONCURRENT_SCANS` | `true` | Allow source scans to run concurrently |
| `THALIMAGE_CORS_ORIGINS` | `[]` | Allowed CORS origins (JSON list); empty since the frontend is served same-origin |
| `THALIMAGE_ALLOWED_HOSTS` | `[]` | Permitted `Host` header values (JSON list); empty accepts all. Set the hostnames clients use (e.g. behind a reverse proxy or on a tailnet) |

The host binds to loopback by default. To expose Thalimage on a LAN, reverse proxy, or tailnet, set `THALIMAGE_HOST` explicitly and list the public hostnames in `THALIMAGE_ALLOWED_HOSTS`.

## Development

Backend is Python (managed with [uv](https://docs.astral.sh/uv/)); frontend is SvelteKit (managed with [pnpm](https://pnpm.io/)). Common tasks are wrapped in the `Makefile`.

```bash
# Backend
make install      # uv sync
make dev          # run the API on http://127.0.0.1:8000
make test         # pytest
make lint         # ruff
make typecheck    # mypy
make check        # lint + typecheck + test

# Frontend
make fe-install   # pnpm install
make fe-dev       # vite dev server on http://localhost:5173
make fe-build     # build the static bundle
make fe-preview   # serve the built bundle on http://127.0.0.1:4173
make fe-check     # svelte-check
```

In development the frontend runs separately and proxies `/api` to the backend on port 8000 (see `frontend/vite.config.ts`), so run `make dev` alongside either `make fe-dev` (hot reload) or `make fe-build && make fe-preview` (production-like bundle). In production the backend serves the built bundle directly, so a single process answers both the UI and the API.

`./check.sh` runs the backend lint/typecheck/test gate and is the validation to run after backend changes.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI, SQLite (WAL mode)
- **Frontend**: SvelteKit (SPA mode, adapter-static)
- **Metadata**: sd-parsers, piexif, Pillow
- **Thumbnails**: Pillow (WebP)

## Documentation

- `CLAUDE.md` — architecture, backend layout, and conventions for contributors
- `docs/agent/phases.md` — current roadmap and backlog
- `docs/` — historical planning and code-review records (each marked as archived)
