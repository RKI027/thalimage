# Thalimage Phases

## Done (MVP — Sprints 1-5)
- Source folder scanning with metadata extraction
- Virtual scrolling gallery with sort/filter by source
- Single image view with metadata panel + keyboard nav
- Collections (CRUD, add/remove images)
- Settings page, sidebar, Docker deployment

## Phase 2 — Core UX improvements
- ELO voting mode (schema ready, needs API + UI: show two images,
  swipe/click to vote, update scores)
- SSE scan progress (placeholder exists, wire up real progress)
- Video thumbnails via ffmpeg
- Thumbnail size slider
- View mode toggle for metadata (none/custom/all with keybind)

## Phase 2.5 — Unified Collections

Collections become the universal container for images. A collection is
a set of images — either static (manually curated or snapshot of a
query result) or dynamic (backed by a live query).

### Design Decisions (confirmed)
- **Browsing context is always a collection.** Even "All Images" and
  transient searches are collection-like objects. Code paths unified.
  A transient search is just an unnamed, possibly ephemeral, dynamic
  collection.
- **ELO scores are per-collection.** Context-dependent ranking is
  desired. Same image can rank differently in different collections.
- **Tags and perceptual hashes are global on the image.** Not
  per-collection. An image tagged "landscape" is tagged "landscape"
  everywhere. Collections filter by tags.
- **Source presets: static for Phase 2.5** (auto-populated when scan
  runs). Become dynamic queries (`WHERE source_id = X`, always live)
  in Phase 3.
- **"All Images" is virtual.** No DB row, no collection_images
  entries. Represented as `id: null` in the browsing context. ELO not
  available on it.
- **Sidebar: grouped, collapsible.** Two sections: "Presets" (All
  Images + per-source) and "Collections" (user-created).
- **Browsing context passing: Svelte store + sessionStorage.** Clean
  URLs (`/image/hash`), survives refresh per tab, lost on tab close
  (acceptable). Direct link to an image works but without prev/next
  context.

### Collection Types
- **Static collections** hold a fixed set of image hashes. Can be
  created manually or by snapshotting a query result. The originating
  query and snapshot date are stored for reference.
- **Dynamic collections** (Phase 3) are defined by a query (source,
  date range, metadata filters, tags — eventually the full DSL). The
  query runs on access; results are always current.
- **Preset collections** are built-in: one per source (auto-synced on
  scan), not user-deletable. "All Images" is virtual (no DB row).
  Future presets: "Photos", "Videos", etc.

### Schema
- `collections` table gains `type TEXT NOT NULL DEFAULT 'manual'` and
  `source_id INTEGER REFERENCES sources(id)`
- Type values: `'manual'`, `'source_preset'`. Phase 3 adds
  `'dynamic_query'` + `query JSON` column.
- Unique partial index on `(source_id) WHERE type = 'source_preset'`
  prevents duplicate presets.

### Source Removal UX (deferred to later)
When removing a source, the user will choose:
1. **Keep DB entries or not** — convenience (preserve ELO scores,
   tags, collection memberships) vs. clean-up (privacy, declutter).
   Kept entries are flagged as orphaned and recoverable if the source
   is re-added.
2. **Generate sidecar files or not** — write metadata (ELO scores,
   tags, prompt data) to sidecar files alongside the original images
   before removal, so data survives independently of the DB.

### Migration Path
- Sources UI is replaced by collections UI; source management stays in
  Settings.
- Sidebar shows collections (preset + user-created) instead of raw
  sources.
- ELO, tagging, and all future features operate on collections, never
  raw sources.
- The `sources` table remains as backend plumbing (scan targets), but
  users interact only through collections.

## Phase 5a — Presenter: Slideshow & Metadata ✓
- Slideshow mode (timed, shuffle, fullscreen, fading overlay controls)
- Configurable metadata display levels (hidden/compact/full), persisted
- Overlay mode (none/minimal/full) independent of metadata mode

## Phase 5b — Presenter: Mobile ✓
- Hamburger drawer sidebar with backdrop
- Compact single-row page headers (hamburger/back + title + ⋮ options sheet)
- Collapsible filter toolbar on gallery and collection views
- Responsive auto thumb size (2 cols portrait / 3 cols landscape)
- Swipe left/right navigation in image viewer
- Fading top bar overlay with ▶ and ℹ buttons
- Metadata bottom sheet (swipe-down to dismiss)
- Slideshow entry point from gallery/collection toolbar and options sheet
- ELO vote stacks vertically on mobile with tap hints
- 44px minimum touch targets throughout

## Phase 3 — Quick Wins ✓
- Per-collection sort persistence (sort resets on every open today)
- Basic filtering UI: source, date range, aspect ratio, media type (dropdowns, no DSL)
- Source presets transition from static (sync on scan) to dynamic
  (`WHERE source_id = X`, always live)
- Archival flag (soft-delete from active sets, space-efficient storage)

## Phase 4 — Tags & NSFW ✓
- Tagging system: global on images; author tracking (created_by column reserved for Phase 8)
- NSFW flag on images: auto-set when the tag named "nsfw" is applied
- Collection-level NSFW flag with toggle in collection view; hidden from sidebar when show_nsfw=false
- User setting: show/hide NSFW content

## Phase 5 — Smart Filters & Saved Searches
- Filter DSL on metadata, prompts, models, LoRAs, tags
- Saved searches become dynamic collections (`type = 'dynamic_query'`,
  `query` JSON column in collections table)

## Phase 6 — Perceptual Dedup
- Perceptual hashing at scan time (pHash/dHash)
- Near-duplicate detection (configurable distance threshold)
- Cluster visualization

## Phase 7 — Comparison & Prompt Analysis
- Image comparison view (side-by-side or slider) — SideBySideView exists
- Prompt diff / similarity (graph-based diff)

## Phase 8 — Advanced
- Auto-tagging (CLIP, face detection)
- Model interrogation for prompt inspiration
- Multi-user support (auth, per-user votes/tags/ELO)
- Batch operations
- TIFF/GIF/AVIF support expansion

## Unsorted

- Justified grid layout (Google Photos / Flickr style): row-based layout
  where all images in a row share a height and fill the full width.
  Existing options: `flickr/justified-layout` (layout engine only, no
  renderer — good fit for a custom Svelte component), `miromannino/
  Justified-Gallery` (jQuery, mature), React variants exist but
  irrelevant here. Seam-carving for content-aware thumbnail cropping
  exists separately (`trekhleb/js-image-carver`, `mfbx9da4/
  seam-carving-js`) — would run at scan time as a preprocessing step,
  storing the carved thumbnail alongside the standard one. No library
  currently combines both; they'd be wired together. A clean Svelte
  wrapper around `flickr/justified-layout` + optional seam-carved thumbs
  could be worth releasing independently.
- add a filter on ELO, not sure which metric, i'm thinking about
  top/bottom percentile (with showing the resulting number of
  pictures). Another way would top/bottom absolute number but less
  sure.
- Tag ontology / hierarchy: parent-child relationships between tags,
  browseable tag tree, implicit inheritance (tagging with "character/alice"
  also applies "character"). Deferred from Phase 4.
- Tag coloring: associate tag names with display colors via a server-side
  config file (e.g. `~/.thalimage/tag_colors.toml`). Loaded at startup,
  surfaced as a `GET /api/v1/tag-colors` endpoint. Frontend uses the map
  to style tag pills. Removes the per-tag `nsfw` boolean from the UI
  (currently unused since NSFW is driven by the tag named "nsfw").
- bulk edit (multi select picture: range and one by one) then
  trash/archive/tags edit
