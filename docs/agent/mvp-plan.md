# Thalimage Reboot Plan

## Context

Thalimage is a self-hosted image browser/manager for AI-generated images. The existing codebase (~2K lines Python + Gradio) works but the UI framework felt "toyish" and limiting. The user wants a fresh start with a proper client-server architecture that can run on a Synology NAS and be accessed from desktop and mobile. The existing core logic (metadata extraction, thumbnail generation, image scanning) is solid and will be ported.

**Key constraints:** privacy-first (zero network calls except client-server), local-first with SQLite, handle ~10K images smoothly, TDD methodology.

## Decided Architecture

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python 3.11+ / FastAPI | Well-trodden path, async, huge ecosystem. User knows Python. |
| Frontend | SvelteKit (SPA mode) | Proven by Immich for photo galleries. Compiles away framework overhead. Least "frameworky" of modern frameworks. |
| Database | SQLite + WAL mode | Local-first, single server process owns all writes. Handles concurrent readers fine. |
| Thumbnails | WebP files in `~/.thalimage/cache/thumbs/` | Served as static files over HTTP. Separate cache dir, easy to wipe/rebuild. |
| Package mgmt | uv (Python), pnpm (JS) | Fast, modern. |
| Repo | New monorepo | Clean history. Port useful code from current repo. |
| Deployment | Docker on Synology NAS | Multi-stage build: frontend compiled, served by Python backend. |

**Why FastAPI over Litestar:** FastAPI is the most well-trodden path for Python async APIs. Massive community, docs, examples. Litestar has nice features but is niche — goes against the "well-trodden path" principle the user values.

**Why SPA mode:** No SSR needed (self-hosted, no SEO). SvelteKit with `adapter-static` produces a static bundle that the Python backend serves. No Node.js server in production.

## Project Structure

```
thalimage/
  backend/
    pyproject.toml
    src/thalimage/
      __init__.py
      __main__.py                  # uvicorn entry point
      config.py                    # pydantic-settings, env/TOML config
      app.py                       # FastAPI app factory
      db/
        engine.py                  # SQLite connection, WAL, migration runner
        migrations/001_initial.sql
      api/
        images.py                  # /api/v1/images
        collections.py             # /api/v1/collections
        sources.py                 # /api/v1/sources
      core/
        scanner.py                 # Port of image_scanner.py + hash computation
        metadata.py                # Port of metadata_extractor.py
        thumbnails.py              # Port of thumbnail_generator.py (file-based)
        analyzer.py                # Port of image_analyzer.py
        hasher.py                  # SHA-256 content hashing
      services/
        scan_service.py            # Orchestrates scan + index + thumbnail gen
        image_service.py           # Image retrieval, metadata queries
        collection_service.py      # Collection CRUD, hierarchy
    tests/
      conftest.py
      fixtures/                    # Small test images with known metadata
      test_scanner.py
      test_metadata.py
      test_thumbnails.py
      test_api_images.py
      test_api_collections.py
  frontend/
    package.json
    svelte.config.js
    vite.config.ts
    src/
      routes/
        +layout.svelte             # App shell
        +page.svelte               # Grid view (home)
        image/[hash]/+page.svelte  # Single image view
        collections/+page.svelte
        collections/[id]/+page.svelte
        settings/+page.svelte      # Source folder management
      lib/
        api.ts                     # Typed fetch wrappers
        types.ts                   # TS types mirroring backend schemas
        stores/                    # Svelte 5 runes-based stores
        components/
          ImageGrid.svelte         # Virtual scrolling grid (custom)
          ImageCard.svelte         # Single thumbnail
          ImageViewer.svelte       # Full-size view
          MetadataPanel.svelte     # Collapsible metadata sidebar
          SortControls.svelte
          Sidebar.svelte
  docker/
    Dockerfile
    docker-compose.yml
  Makefile
  CLAUDE.md
```

## SQLite Schema (MVP)

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Source folders the app watches
CREATE TABLE sources (
    id          INTEGER PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    label       TEXT,
    recursive   BOOLEAN NOT NULL DEFAULT 1,
    enabled     BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_scan   TEXT
);

-- Core image table - lean for grid queries
CREATE TABLE images (
    content_hash    TEXT PRIMARY KEY,        -- SHA-256
    filename        TEXT NOT NULL,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    relative_path   TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    aspect_ratio    REAL NOT NULL,
    format          TEXT NOT NULL,            -- PNG, JPEG, MP4, etc.
    file_modified   TEXT NOT NULL,
    file_created    TEXT,
    thumb_generated BOOLEAN NOT NULL DEFAULT 0,
    deleted         BOOLEAN NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Metadata separate to keep images table fast
CREATE TABLE image_metadata (
    content_hash    TEXT PRIMARY KEY REFERENCES images(content_hash),
    ai_tool         TEXT,
    prompt          TEXT,
    negative_prompt TEXT,
    raw_params      TEXT,                    -- JSON
    exif_data       TEXT,                    -- JSON
    png_text        TEXT,                    -- JSON
    extracted_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Virtual hierarchy (not on disk)
CREATE TABLE collections (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES collections(id),
    sort_by     TEXT NOT NULL DEFAULT 'name',
    sort_dir    TEXT NOT NULL DEFAULT 'asc',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE collection_images (
    collection_id   INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    content_hash    TEXT NOT NULL REFERENCES images(content_hash),
    position        INTEGER,
    added_at        TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (collection_id, content_hash)
);

-- Phase 2: ELO (schema included now to avoid migrations later)
CREATE TABLE votes (
    id              INTEGER PRIMARY KEY,
    collection_id   INTEGER REFERENCES collections(id),
    winner_hash     TEXT NOT NULL REFERENCES images(content_hash),
    loser_hash      TEXT NOT NULL REFERENCES images(content_hash),
    voted_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE elo_scores (
    content_hash    TEXT NOT NULL REFERENCES images(content_hash),
    collection_id   INTEGER NOT NULL REFERENCES collections(id),
    score           REAL NOT NULL DEFAULT 1500.0,
    matches         INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (content_hash, collection_id)
);

CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## REST API (MVP)

**Sources**
- `GET    /api/v1/sources` — list configured source folders
- `POST   /api/v1/sources` — add source `{path, label, recursive}`
- `DELETE /api/v1/sources/{id}` — remove source
- `POST   /api/v1/sources/{id}/scan` — trigger background scan
- `GET    /api/v1/sources/{id}/scan/status` — SSE for scan progress

**Images**
- `GET    /api/v1/images?cursor=&limit=200&sort=name&dir=asc&source_id=&collection_id=` — paginated list (cursor-based)
- `GET    /api/v1/images/{hash}` — full details + metadata
- `GET    /api/v1/images/{hash}/file` — serve original file
- `GET    /api/v1/images/{hash}/thumb` — serve cached thumbnail

**Collections**
- `GET    /api/v1/collections` — tree structure
- `POST   /api/v1/collections` — create `{name, parent_id?}`
- `PATCH  /api/v1/collections/{id}` — update name/sort
- `DELETE /api/v1/collections/{id}`
- `POST   /api/v1/collections/{id}/images` — add images `{hashes: [...]}`
- `DELETE /api/v1/collections/{id}/images` — remove images

Cursor-based pagination: the cursor encodes the sort value of the last item. Better than offset for large datasets and stable under inserts/deletes.

## Code to Port

From `src/thalimage/core/` in the current repo:

| Current file | New location | Changes needed |
|---|---|---|
| `metadata_extractor.py` (193 lines) | `core/metadata.py` | Drop `get_display_metadata()` and `_format_file_size()` (frontend concerns). Return Pydantic models instead of dicts. Keep sd-parsers/piexif/Pillow integration. |
| `thumbnail_generator.py` (212 lines) | `core/thumbnails.py` | Write WebP to disk instead of base64. Remove BytesIO pool. Add hash-based file paths `{cache}/thumbs/{hash[:2]}/{hash}.webp`. Keep ThreadPoolExecutor parallelism. |
| `image_analyzer.py` (284 lines) | `core/analyzer.py` | Keep `analyze_image()` for dimensions/aspect. Drop grid layout logic (frontend) and `sort_images()` (SQL). |
| `image_scanner.py` (62 lines) | `core/scanner.py` | Add MP4 to extensions. Add content hash computation. Return `(path, hash, stat_info)`. |
| `gallery_types.py` (87 lines) | Inform Pydantic schemas + DB schema | `SortBy` enum reused. `ImageInfo` becomes a Pydantic model. |

## Virtual Scrolling Strategy

The frontend `ImageGrid.svelte` uses a custom virtual scroller (no library needed):

1. Backend returns `total_count` with first image page request
2. Grid computes: `columns = floor(containerWidth / (thumbSize + gap))`, `totalRows = ceil(totalCount / columns)`, `totalHeight = totalRows * rowHeight`
3. Outer div has `height: totalHeight` for the scrollbar
4. On scroll: render only visible rows + 2-row buffer
5. Fetch image manifests in pages of 500, pre-fetch next page at 70% scroll
6. Each card: `<img src="/api/v1/images/{hash}/thumb" loading="lazy">` with fixed bounding box, `object-fit: contain`

## Scan Pipeline

1. Walk source directory, collect file paths matching known extensions
2. For each file: check `(path, mtime, size)` against DB — skip unchanged files
3. New/changed files: compute SHA-256 in 64KB chunks (parallel with ThreadPoolExecutor)
4. Extract metadata (dimensions, AI params, EXIF) — parallel
5. Generate thumbnails — parallel
6. Upsert into DB
7. Mark files no longer on disk as `deleted=1`
8. Report progress via SSE: `{phase, current, total}`

**Video thumbnails:** Extract frame via `ffmpeg` subprocess. If ffmpeg not available, use placeholder icon.

## Implementation Sequence

### Sprint 1: Foundation
1. Scaffold monorepo (pyproject.toml, package.json, Makefile)
2. `config.py` — pydantic-settings loading from `~/.thalimage/config.toml`
3. `db/engine.py` — SQLite connection, WAL mode, migration runner
4. Run `001_initial.sql` migration
5. Port `scanner.py` + write `hasher.py` → tests first (TDD)
6. Port `metadata.py` → tests first
7. Port `thumbnails.py` (file-based) → tests first
8. `scan_service.py` orchestrating the above → integration test

### Sprint 2: API Layer
9. FastAPI app factory, CORS, static file serving
10. `/sources` endpoints + scan trigger with SSE progress
11. `/images` endpoints with cursor pagination and sorting
12. `/images/{hash}/thumb` and `/images/{hash}/file` serving
13. `/collections` CRUD
14. API tests with httpx test client

### Sprint 3: Frontend Grid
15. SvelteKit scaffold with adapter-static, Vite proxy to backend
16. Typed API client (`lib/api.ts`)
17. `ImageGrid.svelte` with virtual scrolling
18. `SortControls.svelte`
19. Home page showing all images in grid

### Sprint 4: Single View + Collections
20. `ImageViewer.svelte` — full-size image
21. `MetadataPanel.svelte` — structured metadata display
22. `/image/[hash]` route with keyboard navigation (arrows for prev/next)
23. `Sidebar.svelte` — source management + collection tree
24. Collection routes
25. Source folder add/remove in settings

### Sprint 5: Polish + Deploy
26. Loading states, error handling, empty states
27. Backend serves built frontend at `/`
28. Dockerfile (multi-stage) + docker-compose.yml
29. Test on Docker (Synology-like setup)
30. CLAUDE.md and README for new repo

## Verification

After each sprint:
- `cd backend && uv run pytest` — all tests pass
- `cd backend && uv run ruff check src/ && uv run mypy src/` — clean
- `cd frontend && pnpm lint && pnpm build` — clean build

End-to-end after Sprint 4:
1. Start backend: `uv run uvicorn thalimage.app:create_app --factory`
2. Start frontend: `pnpm dev`
3. Add a source folder via settings page
4. Trigger scan, watch SSE progress
5. Grid populates with thumbnails, virtual scrolling works at 1K+ images
6. Click image → single view with metadata panel
7. Sort by different criteria, verify order changes
8. Create collection, add images, browse collection view

## Multi-user Readiness

Not implementing now, but the schema supports it:
- `votes` table can gain a `user_id` column
- `elo_scores` can gain a `user_id` column
- Tags (future) will have an `author` field per the reboot spec
- The server architecture (single API server, all clients connect remotely) naturally supports multiple users once auth is added
