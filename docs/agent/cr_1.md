# Code Review #1 — 2026-04-17

Focus: code organization, duplicated functions, anti-patterns.

---

## Medium

### Redundant error check in `archive_image`
**File:** `backend/src/thalimage/api/images.py`

After `set_archived()` returns `True` (confirming the image exists), the code calls `get_image()` and checks for `None` again — but that can't fail if the first check passed. Either remove the second check or replace it with an `assert`. Other endpoints (e.g. `get_image_detail`) don't do this double-check.

### `# type: ignore[return-value]` masking a real type gap
**File:** `backend/src/thalimage/services/collection_service.py` (lines 71–72, 175, 182–183)

`create_collection()` and `get_or_create_source_preset()` are typed to return `Collection` (non-optional), but delegate to `get_collection()` which can return `None`. The type errors are suppressed with `# type: ignore` instead of being fixed with assertions or a proper `Optional` return type.

---

## Low

### Frontend sheet UI duplicated across two pages
**Files:** `frontend/src/routes/+page.svelte`, `frontend/src/routes/collections/[id]/+page.svelte`

The mobile options sheet (backdrop, handle area, swipe gesture, all CSS) is copy-pasted between both pages — roughly 50+ lines of markup and ~140 lines of CSS. Should be a shared `OptionsSheet` component in `lib/components/`.

### Image viewer sheet is behind on the pattern
**File:** `frontend/src/routes/image/[hash]/+page.svelte` (~line 319)

The gallery and collection pages added a `.sheet-handle-area` wrapper with swipe detection; the image viewer's bottom sheet still uses the old pattern (bare `.sheet-handle` div, no wrapper). Inconsistent behavior across the app.

### Unused return value from `remove_images()`
**File:** `backend/src/thalimage/services/collection_service.py`

Returns `cursor.rowcount` (count of removed images) but no API endpoint uses it. `add_images()` has symmetric logic. Either surface it in the DELETE response for API symmetry, or document why it's intentionally unused.

### Gallery filters not scoped to source
**File:** `frontend/src/routes/+page.svelte`

Collection filters are persisted per-collection (`collection:${id}:filters`), but gallery filters are global. If a user filters by aspect ratio on one source and navigates to another, the filter carries over silently. Should be keyed by `source_id` to match the collection pattern.

### Schema allows `source_preset` collections to have `collection_images` rows
**File:** `backend/src/thalimage/db/migrations/003_dynamic_source_presets.sql`

The migration deletes existing rows but adds no constraint to prevent future insertions. A DB trigger would enforce the invariant that source presets are always served dynamically.

### FilterBar accepts invalid date strings
**File:** `frontend/src/lib/components/FilterBar.svelte` (lines 28–29, 37–38)

Date inputs rely on HTML5 `type="date"` but the value is passed to the API as-is. A manually typed invalid date string would propagate to SQL comparisons silently.

---

## Positive

- Migration to dynamic source preset queries is well-executed — no action needed.
- `_COUNT_SQL` constant extraction in `collection_service.py` correctly addresses earlier SQL duplication.
