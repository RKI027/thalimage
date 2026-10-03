# Organization review: thalimage

Scope: repository root (tracked files) · Commit: 031252b (dirty working tree) · Date: 2026-09-29

There are no critical or high findings. The largest problems are copied logic:
- the video-extension list, defined 6 times;
- the two gallery pages, which are near-copies;
- two copies of the image upsert in the scan service;
- a repeated list of summary columns.

A vestigial `tags.nsfw` flag still runs through the service, the API and the client. There is also a fair amount of small dead code on both the backend and the frontend. The review found no leftover debug code and no TODO/FIXME markers. The unused `aiosqlite` dependency is reported under PKG-003.

## ORG-001: Define the video-extension list once per side

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/video.py:14`, `backend/src/thalimage/services/image_service.py:50-51`, `frontend/src/routes/image/[hash]/+page.svelte:38-41,318`, `frontend/src/lib/components/ImageViewer.svelte:4,24-26`, `frontend/src/lib/components/views/ImagePanel.svelte:4,18-20`, `frontend/src/routes/elo/[collectionId]/+page.svelte:10,31-36`
- **Labels:** organization, backend, frontend

The set `{mp4, mov, webm, avi}` is hard-coded in 6 places:
- **Backend (2):** `VIDEO_EXTENSIONS` in `core/video.py`, and `VIDEO_FORMATS` in `image_service.py` (the same set, upper-cased).
- **Frontend (4):** each copy is a `new Set(['.mp4', ...])` paired with its own `filename.slice(lastIndexOf('.'))` check for "is this a video".

**Why it matters:** Adding a format such as `.mkv` means editing 6 files. Missing one leaves the scanner, the media-type filter and the viewer disagreeing about what a video is.

**Suggested fix:** In the backend, derive `VIDEO_FORMATS` from `core.video.VIDEO_EXTENSIONS`. In the frontend, export one `isVideoFilename(name)` helper from `$lib` and use it in all 4 files.

**Done when:** `grep -rn "'.mp4'" frontend/src` finds exactly one definition, and `image_service.py` has no literal list of video formats.

## ORG-002: Pull the shared gallery logic out of the two grid pages

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/routes/+page.svelte:16-68,107-115`, `frontend/src/routes/collections/[id]/+page.svelte:15-57,79-83,85-121,134-144`
- **Labels:** organization, frontend

The two pages repeat the same code, differing only in `source_id` versus `collection_id`:
- the images / totalCount / nextCursor / loading state;
- the persisted `thumbSize` effect;
- the `beforeNavigate` scroll save;
- `fetchImages(reset)` with `limit: 500`;
- `startSlideshow()`;
- the mobile resize handler for `responsiveThumbSize`.

Filter-persistence keys are also built by hand in several places: `galleryKey()` on one page, and the literal `` `collection:${id}:filters` `` at `collections/[id]/+page.svelte:62,107` and at `elo/[collectionId]/+page.svelte:125`. The collection page also repeats the same `setBrowsingContext({...})` literal 3 times.

**Why it matters:** Fixes to one page drift from the other. For example, the home page handles fetch errors and `initialLoad`, and the collection page does not (see GEN-011).

**Suggested fix:** Move paging, thumb size and slideshow start into a shared rune module (e.g. `$lib/gallery.svelte.ts`) that takes a query-builder callback. Add one helper for the filter storage key and one local helper for the browsing context.

**Done when:** Each page's script holds only its own concerns: its query parameters, the collection's sort persistence and the NSFW toggle.

## ORG-003: Merge the duplicated `images` upsert in the scan service

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:118-135`, `backend/src/thalimage/services/scan_service.py:150-177`
- **Labels:** organization, backend

The video branch and the image branch each contain the same 17-line `INSERT INTO images ... ON CONFLICT(content_hash) DO UPDATE SET ...`. The only difference is where width, height, aspect ratio and format come from. `run_scan` is one 200-line function that mixes file walking, per-file extraction, SQL and deleted-file handling.

**Why it matters:** Any change to the upsert has to be made twice and kept in sync by hand. Examples are updating `width`/`height`, which neither copy does today, or the `source_id` fix from GEN-006.

**Suggested fix:** Have each branch produce `(width, height, aspect, fmt)`, then call one `_upsert_image(conn, ...)` helper. Move the metadata upsert into a `_upsert_metadata(conn, h, meta | None)` helper.

**Done when:** `INSERT INTO images` appears once in `scan_service.py`, and `test_scan_service.py` and `test_video.py` still pass.

## ORG-004: Remove the dead `tags.nsfw` flag from the service, API and client

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/db/migrations/009_nsfw_trigger_by_name.sql:1-2`, `backend/src/thalimage/services/tag_service.py:12,38-49,52-67`, `backend/src/thalimage/api/tags.py:25-32`, `frontend/src/lib/types.ts:18`, `frontend/src/lib/api.ts:225-239`
- **Labels:** organization, backend, frontend

Migration 009 switched image NSFW flagging from the `tags.nsfw` column to the tag *named* "nsfw". The frontend also decides by name (`MetadataPanel.svelte:145,166`). The column is still carried through `Tag`, `TagCreate`, `TagUpdate`, `create_tag(nsfw=)`, `update_tag(nsfw=)`, the TS `Tag` type and `createTag(name, nsfw)`, but nothing reads it. Tests in `test_tag_service.py:47-49,106-110` still assert on it.

**Why it matters:** A client can set `nsfw: true` on a tag and nothing happens. The two NSFW mechanisms look alike and are easy to confuse.

**Suggested fix:** Drop `nsfw` from the tag model, the request bodies and the TS types, along with the related tests. Optionally, add a migration that drops the column.

**Done when:** `grep -n nsfw backend/src/thalimage/services/tag_service.py backend/src/thalimage/api/tags.py` returns nothing, and the TS `Tag` type has no `nsfw` field.

## ORG-005: Share the ImageSummary column list and row conversion

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:179-182,219`, `backend/src/thalimage/services/elo_service.py:29-31,39-41,74-77`
- **Labels:** organization, backend

The 11 summary columns are spelled out 3 times: once as a Python list in `list_images`, and twice as SQL in the two branches of `get_pair`. The conversion `ImageSummary(**{k: r[k] for k in ImageSummary.model_fields})` is also repeated 3 times. The two query branches in `get_pair` differ only in their FROM/JOIN/WHERE clauses.

**Why it matters:** Adding a field to `ImageSummary` means updating every column list, or the ELO pair endpoint fails with a KeyError.

**Suggested fix:** Add `SUMMARY_COLUMNS` and `summary_from_row(row)` to `image_service`. Build `get_pair`'s SELECT from `", ".join(f"i.{c}" ...)`, keeping only the FROM/WHERE part per branch.

**Done when:** The column names appear once, and all three conversions call one helper.

## ORG-006: Remove unused exported client functions

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/api.ts:167-187,233-244`, `frontend/src/lib/browsingContext.ts:64-69`
- **Labels:** organization, frontend

Five exports are never imported anywhere under `frontend/src`: `addImagesToCollection`, `removeImagesFromCollection`, `updateTag` and `deleteTag` in `api.ts`, and `clearScrollPosition` in `browsingContext.ts`. `displaySize` (`api.ts:84`) is exported but only used inside `api.ts`.

**Why it matters:** Readers will assume the UI can add images to or remove them from collections, and edit or delete tags. It cannot.

**Suggested fix:** Delete these functions, or add a `phases.md` backlog note if the UI is planned. Stop exporting `displaySize`.

**Done when:** Every export in `api.ts` and `browsingContext.ts` has at least one importer.

## ORG-007: Remove the test-only `generate_thumbnails_parallel`

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/thumbnails.py:39-55`, `backend/tests/test_thumbnails.py:10,64-71`
- **Labels:** organization, backend

The scan calls `generate_thumbnail` one file at a time (`scan_service.py:148`). `generate_thumbnails_parallel` and its `ThreadPoolExecutor` import are only used by a test.

**Why it matters:** This is dead production code that looks like a live parallel thumbnail path.

**Suggested fix:** Delete the function, its import and its test, or wire it into the scan if that is the intent.

**Done when:** `grep -rn generate_thumbnails_parallel backend/src` returns nothing, or only a definition that has callers.

## ORG-008: `sourcesStore` is refreshed but never read

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/stores.ts:36`, `frontend/src/routes/settings/+page.svelte:7,23-25,34,44,59`
- **Labels:** organization, frontend

Nothing subscribes to `sourcesStore`: `$sourcesStore` appears nowhere. Meanwhile the settings page keeps its own `sources` array and calls both its own `refresh()` (`listSources()`) and `sourcesStore.refresh()`, so every change fetches the source list twice.

**Why it matters:** One list has two sources of truth, and every change makes a wasted request.

**Suggested fix:** Render the settings page from `$sourcesStore` and delete the local `sources` and `refresh`, or delete `sourcesStore`.

**Done when:** Only one mechanism holds the source list, and each change triggers a single fetch.

## ORG-009: Remove unused `ImageViewer` props and a dead `sheetEl` binding

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/components/ImageViewer.svelte:9-12,17-20,58`, `frontend/src/routes/image/[hash]/+page.svelte:22,350-353,460-463,492`
- **Labels:** organization, frontend

`ImageViewer` declares `width` and `height` props that its template never uses. `nativeControls` defaults to `true`, but both call sites pass `false`, so the native-controls path never runs. On the image page, `sheetEl` is bound with `bind:this` but never read.

**Why it matters:** These suggest behaviour (sizing, native controls) that does not exist.

**Suggested fix:** Drop `width` and `height` from the props and both call sites. Remove `nativeControls`, or keep it with a `false` default. Delete `sheetEl`.

**Done when:** `ImageViewer` has no unused props and `sheetEl` no longer exists.

## ORG-010: Resolve source-preset collections in one place

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/images.py:52-57`, `backend/src/thalimage/api/elo.py:37-41`
- **Labels:** organization, backend

Both routers repeat the same steps: call `get_collection`, check for `type == "source_preset"`, then swap in `coll.source_id`. That is domain logic living in the API layer, twice.

**Why it matters:** Every new collection-scoped endpoint has to remember this step.

**Suggested fix:** Add `collection_service.resolve_scope(conn, collection_id) -> (source_id, collection_id)` and call it from both routers.

**Done when:** The string `"source_preset"` no longer appears in `api/images.py` or `api/elo.py`.

## ORG-011: Share the WebP thumbnail encoder between image and video

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/thumbnails.py:32-34`, `backend/src/thalimage/core/video.py:95-98`, `backend/src/thalimage/core/previews.py:62-72`
- **Labels:** organization, backend

`extract_video_thumbnail` repeats the resize-and-save code from `generate_thumbnail`, including the hard-coded quality of 80. `previews.py` has a third copy of the resize and save, with its own atomic temp-file write.

**Why it matters:** Quality and size settings can drift between image and video thumbnails, and a fix to how the file is written lands in only one copy (compare GEN-017).

**Suggested fix:** Add a `write_webp(img, dest, *, max_size, quality)` helper in `core/` and call it from all three places.

**Done when:** `format="WEBP"` (or `"WEBP"`) appears once under `core/`.

## ORG-012: Define the check pipeline once

- **Severity:** low
- **Confidence:** high
- **Location:** `Makefile:1,10-20`, `check.sh:6-22`, `CLAUDE.md:13-20`
- **Labels:** organization, tooling

`check.sh` writes out the `ruff`, `mypy` and `pytest` commands itself instead of calling the Make targets. `make check` leaves out the frontend check that `check.sh` runs, so "check" means two different things. `.PHONY` also omits `lint-fix` and the `fe-*` targets.

**Why it matters:** A flag changed in one place (for example `pytest -q` versus `pytest`) silently diverges from the other, and a passing `make check` does not mean CI (`check.sh`) passes.

**Suggested fix:** Have `check.sh` call `make lint typecheck test` (plus `fe-check`), or have `make check` run `./check.sh`. Complete `.PHONY`.

**Done when:** Each tool invocation is written once, and `make check` does the same as `./check.sh`.

## ORG-013: Move the duplicated test seed helpers into conftest

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/tests/test_api_collections.py:8-16`, `backend/tests/test_api_images.py:8-18`, `backend/tests/test_collection_types.py:9-20`, `backend/tests/test_nsfw.py:9-29`, `backend/tests/test_tag_service.py:19-33`
- **Labels:** organization, tests

`_seed_images` (create a source, scan it, wait on SSE, list the hashes) is copied into 3 files. `_seed_image`, a raw `INSERT INTO images` with the same literal values, is copied into 2 files.

**Why it matters:** A schema change to `images`, such as a new NOT NULL column, breaks each copy separately.

**Suggested fix:** Move both helpers into `conftest.py` as fixtures or factory functions (e.g. `seeded_hashes`, `insert_image`).

**Done when:** Each helper exists once, and the tests import it or use it as a fixture.

## ORG-014: Deduplicate `settingsHref` in the layout and sidebar

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/routes/+layout.svelte:15-19`, `frontend/src/lib/components/Sidebar.svelte:29-33`
- **Labels:** organization, frontend

Both files use the same `$derived` expression to build `/settings?returnTo=...`.

**Why it matters:** The two links to Settings can drift apart.

**Suggested fix:** Export a `settingsHref(url)` helper from `$lib`, or pass the value down from the layout as a prop.

**Done when:** The `returnTo` URL is built in one place.

## ORG-015: Derive the repository root once

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/app.py:19`, `backend/src/thalimage/version.py:17`, `docker/Dockerfile:32-35`
- **Labels:** organization, backend

`FRONTEND_DIR` and `REPO_ROOT` each walk `.parent.parent.parent.parent` from their own file. A comment in the Dockerfile explains that both depend on this layout.

**Why it matters:** The coupling to the directory layout is spread across two modules and a comment, and moving either file breaks it silently.

**Suggested fix:** Define `REPO_ROOT` once (in `version.py` or a small `paths.py`), and set `FRONTEND_DIR = REPO_ROOT / "frontend" / "build"`.

**Done when:** The four-parent walk appears once in `backend/src`.

See also: PKG-001.

## ORG-016: Simplify the settings router and give it a service like the other routers

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/settings.py:12-42`, `backend/src/thalimage/app.py:13,24`
- **Labels:** organization, backend

`api/settings.py` is the only router that runs SQL itself. Its `_DEFAULTS` dict and `_read_settings` are generic key/value plumbing for a single boolean. The `show_nsfw` default is stated three times: in `_DEFAULTS`, in `UserSettings`, and in `data.get("show_nsfw", False)`. The endpoint is named `get_settings`, like `config.get_settings`. In `app.py`, `settings` is both the imported router module (line 13) and a local variable (line 24).

**Why it matters:** The layering is inconsistent with the other routers, the default is defined three times, and one name refers to both the user preferences and the app configuration.

**Suggested fix:** Add a `services/user_settings.py` with `read()` and `write()` returning `UserSettings`. Rename the endpoint (e.g. `read_user_settings`) and import the router as `user_settings`.

**Done when:** The router contains no SQL, and the `show_nsfw` default is defined once.

## ORG-017: Remove the needless indirection in filter tables and service return values

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:53-58,80-82,139`, `backend/src/thalimage/services/collection_service.py:86-92,122-128`, `backend/src/thalimage/api/collections.py:82-83,93-94`
- **Labels:** organization, backend

- **`ASPECT_RATIO_FILTERS`:** every entry is a `(clause, [])` pair whose params list is always empty and thrown away (`clause, _ =`).
- **`append_media_filters`:** it both mutates `params` and returns it, and callers discard the return value (`q, _ =`).
- **`update_collection` / `delete_collection`:** they return the magic strings `"preset_rename_forbidden"` / `"preset_delete_forbidden"`, but callers only test `isinstance(result, str)`.

**Why it matters:** The return types (`Optional[Collection] | str`, `bool | str`) are harder to read, and the filter table carries a field that does nothing.

**Suggested fix:** Make `ASPECT_RATIO_FILTERS` a plain `dict[str, str]`, and have `append_media_filters` return only `q`. Raise a `PresetCollectionError` from the service and map it to 403 in the router.

**Done when:** No `str` appears in these service return annotations, and no `, _ =` unpacking remains for these calls.

## ORG-018: Share the safe localStorage helpers

- **Severity:** low
- **Confidence:** medium
- **Location:** `frontend/src/lib/slideshowStore.svelte.ts:21-45`, `frontend/src/routes/+page.svelte:23,29,75-77,83-84,91`, `frontend/src/routes/collections/[id]/+page.svelte:25,29,62,107`, `frontend/src/routes/elo/[collectionId]/+page.svelte:125`, `frontend/src/lib/components/Sidebar.svelte:37-38,43,48`, `frontend/src/lib/components/ImageViewer.svelte:37-42`, `frontend/src/routes/image/[hash]/+page.svelte:31,43`
- **Labels:** organization, frontend

`slideshowStore` defines `readLocalStorage`, `writeLocalStorage` and `removeLocalStorage`, which wrap storage access in try/catch and handle JSON. The other 6 files call `localStorage` directly, each decoding values its own way (`JSON.parse`, `Number()`, `=== 'true'`).

**Why it matters:** The same job follows two conventions, and the direct calls lack the fallback that the helpers exist to provide.

**Suggested fix:** Move the three helpers to `$lib/storage.ts` and use them everywhere.

**Done when:** `localStorage.` appears only in `$lib/storage.ts`.

## ORG-019: Delete the empty template placeholder files

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/assets/favicon.svg`, `frontend/src/lib/index.ts:1`
- **Labels:** organization, frontend

`favicon.svg` is 0 bytes, and nothing references it: `app.html:11` uses `/favicon.png`. `lib/index.ts` holds only the SvelteKit template comment, and nothing imports from `'$lib'`.

**Why it matters:** These are leftover scaffold files that look like real assets or entry points.

**Suggested fix:** Delete both files.

**Done when:** Neither file is tracked, and `pnpm check` and `pnpm build` still pass.
