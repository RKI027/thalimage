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

### Design
- **Dynamic collections** are defined by a query (source, date range, metadata filters, tags — eventually the full DSL from Phase 3). The query runs on access; results are always current.
- **Static collections** hold a fixed set of image hashes. Can be created manually or by snapshotting a query result. The originating query and snapshot date are stored for reference.
- **Preset collections** are built-in dynamic collections: "All Images", one per source, "Photos", "Videos", etc. Not user-deletable.

### Source removal UX
When removing a source, the user chooses:
1. **Keep DB entries or not** — convenience (preserve ELO scores, tags, collection memberships) vs. clean-up (privacy, declutter). Kept entries are flagged as orphaned and recoverable if the source is re-added.
2. **Generate sidecar files or not** — write metadata (ELO scores, tags, prompt data) to sidecar files alongside the original images before removal, so data survives independently of the DB.

### Migration path
- Sources UI is replaced by collections UI; source management moves to per-collection settings for source-backed collections.
- Sidebar shows collections (preset + user-created) instead of raw sources.
- ELO, tagging, and all future features operate on collections, never raw sources.
- The current `sources` table remains as backend plumbing (scan targets), but users interact only through collections.

### Open questions
- Ordering: this could come before or after Phase 3. The DSL isn't needed for source presets, but designing the collection query model well requires knowing what Phase 3 filters look like. A minimal version (source presets only) can land first, with the query system added in Phase 3.
- Schema changes: `collections` table gains `type` (static/dynamic), `query` (JSON), `source_id` (nullable, for source-backed presets). Migration from current schema is straightforward.

## Phase 3 — Organization & Search
- Tagging system with author tracking + tag ontology
- Auto-tagging (CLIP, face detection)
- Smart filters / DSL on metadata, prompts, models, LoRAs
- Saved searches as smart collections
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