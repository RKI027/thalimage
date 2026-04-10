# Thalimage

Self-hosted image browser/manager for AI-generated images.

## Architecture

- **Backend**: Python 3.11+ / FastAPI, SQLite (WAL mode)
- **Frontend**: SvelteKit (SPA mode with adapter-static)
- **Monorepo**: `backend/` and `frontend/` directories

## Development

```bash
make install      # Install backend deps (uv)
make test         # Run backend tests
make lint         # Ruff lint
make typecheck    # Mypy
make check        # All of the above
make dev          # Run backend dev server
```

## Backend Layout

- `src/thalimage/config.py` — pydantic-settings, loads from `~/.thalimage/config.toml`
- `src/thalimage/app.py` — FastAPI app factory
- `src/thalimage/db/` — SQLite engine, migrations
- `src/thalimage/core/` — scanner, metadata, thumbnails, hasher, analyzer
- `src/thalimage/services/` — scan orchestration, image queries, collections
- `src/thalimage/api/` — REST endpoints

## Key Conventions

- Cursor-based pagination (not offset)
- Content-addressed images by SHA-256 hash
- Thumbnails: WebP files at `{cache_dir}/thumbs/{hash[:2]}/{hash}.webp`
- All dates stored as ISO 8601 text in SQLite
- TDD: tests first, then implementation

## Documentation

- `docs/agent/reboot.org` — original vision and requirements document
- `docs/agent/mvp-plan.md` — implementation plan for the MVP (sprints 1-5, completed)
- `docs/agent/phases.md` — roadmap of future phases (2-6)
