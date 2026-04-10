# Thalimage Phases

## Done (MVP — Sprints 1-5)
- Source folder scanning with metadata extraction
- Virtual scrolling gallery with sort/filter by source
- Single image view with metadata panel + keyboard nav
- Collections (CRUD, add/remove images)
- Settings page, sidebar, Docker deployment

## Phase 2 — Core UX improvements
- ELO voting mode (schema ready, needs API + UI: show two images, swipe/click to vote, update scores)
- SSE scan progress (placeholder exists, wire up real progress)
- Video thumbnails via ffmpeg
- Thumbnail size slider
- View mode toggle for metadata (none/custom/all with keybind)

## Phase 2.5 — Unified Collections

Collections become the universal container for images. A collection is a set of images — either static (manually curated or snapshot of a query result) or dynamic (backed by a live query).

### Design Decisions (confirmed)
- **Browsing context is always a collection.** Even "All Images" and transient searches are collection-like objects. Code paths unified. A transient search is just an unnamed, possibly ephemeral, dynamic collection.
- **ELO scores are per-collection.** Context-dependent ranking is desired. Same image can rank differently in different collections.
- **Tags and perceptual hashes are global on the image.** Not per-collection. An image tagged "landscape" is tagged "landscape" everywhere. Collections filter by tags.
- **Source presets: static for Phase 2.5** (auto-populated when scan runs). Become dynamic queries (`WHERE source_id = X`, always live) in Phase 3.
- **"All Images" is virtual.** No DB row, no collection_images entries. Represented as `id: null` in the browsing context. ELO not available on it.
- **Sidebar: grouped, collapsible.** Two sections: "Presets" (All Images + per-source) and "Collections" (user-created).
- **Browsing context passing: Svelte store + sessionStorage.** Clean URLs (`/image/hash`), survives refresh per tab, lost on tab close (acceptable). Direct link to an image works but without prev/next context.

### Collection Types
- **Static collections** hold a fixed set of image hashes. Can be created manually or by snapshotting a query result. The originating query and snapshot date are stored for reference.
- **Dynamic collections** (Phase 3) are defined by a query (source, date range, metadata filters, tags — eventually the full DSL). The query runs on access; results are always current.
- **Preset collections** are built-in: one per source (auto-synced on scan), not user-deletable. "All Images" is virtual (no DB row). Future presets: "Photos", "Videos", etc.

### Schema
- `collections` table gains `type TEXT NOT NULL DEFAULT 'manual'` and `source_id INTEGER REFERENCES sources(id)`
- Type values: `'manual'`, `'source_preset'`. Phase 3 adds `'dynamic_query'` + `query JSON` column.
- Unique partial index on `(source_id) WHERE type = 'source_preset'` prevents duplicate presets.

### Source Removal UX (deferred to later)
When removing a source, the user will choose:
1. **Keep DB entries or not** — convenience (preserve ELO scores, tags, collection memberships) vs. clean-up (privacy, declutter). Kept entries are flagged as orphaned and recoverable if the source is re-added.
2. **Generate sidecar files or not** — write metadata (ELO scores, tags, prompt data) to sidecar files alongside the original images before removal, so data survives independently of the DB.

### Migration Path
- Sources UI is replaced by collections UI; source management stays in Settings.
- Sidebar shows collections (preset + user-created) instead of raw sources.
- ELO, tagging, and all future features operate on collections, never raw sources.
- The `sources` table remains as backend plumbing (scan targets), but users interact only through collections.

## Phase 3 — Organization & Search
- Tagging system with author tracking + tag ontology (tags are global on images, not per-collection)
- Auto-tagging (CLIP, face detection)
- Smart filters / DSL on metadata, prompts, models, LoRAs
- Saved searches become dynamic collections (`type = 'dynamic_query'`, `query` JSON column in collections table)
- Source presets transition from static (sync on scan) to dynamic (`WHERE source_id = X`, always live)
- Per-collection sort persistence
- Archival flag (remove from active sets, space-efficient storage)

## Phase 4 — Comparison & Dedup
- Perceptual hashing
- Near-duplicate detection (configurable distance)
- Cluster visualization (grid or side-by-side or blended)
- Image comparison view (side-by-side or slider) with prompt diff
- Prompt similarity (graph-based diff)

## Phase 5 — Presenter
- Slideshow mode (manual/timed, shuffle, sort, temporary filters)
- Configurable metadata display levels
- Mobile-friendly presentation

## Phase 6 — Advanced
- Model interrogation for prompt inspiration
- Multi-user support (auth, per-user votes/tags/ELO)
- Batch operations
- TIFF/GIF/AVIF support expansion