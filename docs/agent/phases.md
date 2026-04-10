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