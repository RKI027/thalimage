# Thalimage

Self-hosted image browser/manager for AI-generated images.

## Architecture

- **Backend**: Python 3.11+ / FastAPI, SQLite (WAL mode)
- **Frontend**: SvelteKit (SPA mode with adapter-static)
- **Monorepo**: `backend/` and `frontend/` directories

## Development

Commands are in the Development section of `README.md` (all wrapped in
the `Makefile`). `./check.sh` is the gate CI runs; run it before pushing.
The frontend needs Node 24 and the pnpm pinned in `frontend/package.json`.

## Backend Layout (`backend/src/thalimage/`)

- `config.py` — pydantic-settings: `THALIMAGE_*` env vars, `~/.thalimage/config.toml`
- `app.py` — FastAPI app factory: middleware, routers, SPA serving
- `deps.py` — request dependencies; `get_db` opens a connection per request
- `csrf.py` — refuses cross-site writes
- `paths.py` — repository-relative paths (checkout only)
- `version.py` — package version and build commit
- `db/` — SQLite engine and the numbered migrations (`db/migrations/NNN_*.sql`)
- `core/` — file-level work: `scanner` (listing), `hasher`, `metadata`,
  `thumbnails`, `previews`, `video` (ffmpeg), `webp` (the one WebP writer)
- `services/` — `scan_service` (a scan), `scan_manager` (scan state, SSE),
  `image_service` (listing, neighbours, details), `locations` (where
  content lives), `collection_service`, `source_service` (removal),
  `elo_service`, `tag_service`, `user_settings`, `docs_service`
- `api/` — REST endpoints under `/api/v1`, one router per resource
- `docs/` — in-app user documentation (Markdown), served at `/docs`

## Frontend Layout (`frontend/src/`)

- `routes/` — pages: gallery (`+page.svelte`), `collections/[id]`,
  `image/[hash]` (viewer), `elo/[collectionId]`, `settings`, `docs`
- `lib/api.ts` — API client; `lib/types.ts` — shared types
- `lib/gallery.svelte.ts`, `lib/eloRound.svelte.ts`,
  `lib/slideshowStore.svelte.ts` — page state, unit-tested
- `lib/browsingContext.ts` — the listing the viewer walks
- `lib/storage.ts` — the only code touching local/session storage
- `lib/components/` — UI components
- `*.test.ts` next to the module — vitest

## Deployment

- `docker/` — Dockerfile, the Portainer-ready compose sample (Tailscale
  sidecar + app), `serve.json`, `.env.example`
- `.github/workflows/docker.yml` — builds and publishes
  `ghcr.io/rki027/thalimage`; `ci.yml` runs `check.sh`
- See the Deployment section of `README.md` for the operational details

## Documentation

- `docs/roadmap.md` — **current** roadmap and backlog
- `docs/review/` — full-review runs, each with a `RESOLUTION.md` ledger
- `docs/archive/` — archived plans, fix logs and reviews (indexed in its README)
- `backend/src/thalimage/docs/` — in-app user documentation
