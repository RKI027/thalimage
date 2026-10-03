# Testing review: thalimage

Scope: repository root (tracked files) · Commit: e28c431 (dirty working tree) · Date: 2026-09-29

## Test run

**Setup:** pytest 8, with pytest-asyncio (`asyncio_mode=auto`) and pytest-cov declared in the `backend/pyproject.toml` dev group. There are 25 test files under `backend/tests/`. They run through `check.sh` (`uv run pytest -q`), `make test`, and CI (`.github/workflows/ci.yml` → `./check.sh`; that file is untracked). **The frontend has no test runner.** `package.json` defines only `check` (svelte-check).

**Command:** `cd backend && uv run --offline --frozen pytest -q -p no:cacheprovider --cov=thalimage --cov-branch --cov-report=term-missing`

**Result:** 219 passed, 0 failed, 0 skipped, in 7.55 s. ffmpeg is installed on the review machine, so the `requires_ffmpeg` tests ran.

**Coverage (line + branch): 89% overall.** 1285 statements, 111 missed. Weak spots:

| Module | Coverage | Missed lines |
|---|---|---|
| `__main__.py` | 0% | all |
| `api/settings.py` | 43% | |
| `api/tags.py` | 54% | |
| `deps.py` | 65% | overridden in tests |
| `core/metadata.py` | 74% | 76-85, 97-106 |
| `services/scan_service.py` | 86% | 53, 106-108, 112-138 |
| `api/sources.py` | 88% | 131, 154-155, 172, 177-178, 186 |
| `api/elo.py` | 89% | 41, 71-72 |
| `api/images.py` | 90% | 95, 98, 131, 136-137 |

The coverage run left an untracked `backend/.coverage` file in the working tree.

## TST-001: Test that deleting a source cascades correctly and loses nothing else

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/sources.py:76-116`, `backend/tests/test_api_sources.py:37-45`, `backend/tests/test_collection_types.py:121-133`
- **Labels:** testing, backend, data-integrity

`delete_source` hard-deletes rows from six tables: collections (the preset), image_metadata, collection_images, elo_scores, votes and images. The image_tags rows go by FK cascade. `test_delete_source` never scans, so `hashes` is empty and the block at lines 96-114 never runs in that test. `test_source_deletion_removes_preset` only checks the preset collection.

No test asserts that:
- the dependent rows are removed;
- other sources' images keep their manual collections, votes and ELO scores;
- an image whose content also exists in another source is handled correctly (see TST-002).

**Why it matters:** This is the most destructive endpoint in the app. A wrong WHERE clause here silently deletes user curation data: collections, votes, rankings and tags. GEN-003 shows the endpoint already fails once the preset has ELO data.

**Suggested fix:** Add an API test with two sources: scan both, add images to a manual collection, vote and tag. Then delete one source and check the exact expected rows in every table.

**Done when:** A test fails if any row belonging to the surviving source is removed, or if any dependent row of the deleted source remains.

See also: GEN-003.

## TST-002: Cover the scan's changed-file, duplicate-content, video and error paths

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:92-145`, `:207-209`, `:222-237`, `backend/tests/test_scan_service.py:23-128`
- **Labels:** testing, backend, scanner

`test_scan_service.py` covers only new, unchanged and removed files, in 4 tests. These paths have no test:
- **Modified file:** same path with a new mtime or size (the partial branch 95->101).
- **Video ingest:** lines 106-138 are entirely uncovered.
- **Missing ffmpeg:** the skip path.
- **Corrupt file:** nothing asserts that one bad file increments `errors` without aborting the scan. The only `errors` assertion is `== 0`.
- **Duplicate content:** identical bytes within one source or across two sources. This path is already buggy (GEN-006), and no test catches it.

**Why it matters:** The scanner is the only way images get into the library. Its upsert and soft-delete logic decides which files the user can reach.

**Suggested fix:** Add `run_scan` tests for:
- a modified file (old hash soft-deleted, new hash added);
- an unreadable file (`errors == 1`, other files still indexed);
- a video with ffmpeg patched to be unavailable, and with ffmpeg present;
- duplicate content within one source and across two sources.

**Done when:** `scan_service.py` has no uncovered lines except the `ValueError` for a missing source, and the duplicate-content tests pin the intended ownership and path behaviour.

See also: GEN-006, GEN-007.

## TST-003: Test AI-parameter and EXIF extraction on real metadata

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/metadata.py:71-109`, `backend/tests/test_metadata.py:27-29`
- **Labels:** testing, backend, metadata

The success path of `_extract_ai_params` (lines 76-85) and the EXIF decode loop (lines 97-106) never run in tests. The only AI test uses a plain PNG and asserts `ai_params is None or ai_params.prompt is None`, which passes whether or not parsing works. Both functions swallow every exception (`except Exception: pass` / `return None`). So a broken parser, or an API change in sd-parsers, would only show up as missing prompts in production.

**Why it matters:** Extracting prompts and generation parameters is the product's main feature for AI images, and it has no regression protection.

**Suggested fix:** Add fixtures built with `PngInfo`: an A1111-style `parameters` chunk, a ComfyUI `prompt`/`workflow` chunk, and a JPEG with an EXIF UserComment. Assert the tool, prompt, negative prompt and raw_params, plus the EXIF handling of bytes vs str (repr).

**Done when:** Lines 76-85 and 97-106 are covered, and the tests fail if extraction returns None for those fixtures.

## TST-004: Remove the vacuous early return in the video preview test

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/tests/test_api_images.py:250-258`, `:201-205`, `:208-221`, `backend/src/thalimage/api/images.py:134-137`
- **Labels:** testing, backend, api

`test_preview_rejects_a_video` writes `b"not really a video"` to `clip.mp4`. ffprobe fails on it, the scan counts an error, and `hashes` is empty. The test then reaches `if not hashes: return` and passes without asserting anything. Coverage confirms that the 415 branch (lines 136-137) never runs.

Two related tests can only ever pass:
- `test_filter_by_media_type_video` asserts `total_count == 0` on a fixture that contains no videos.
- The date-filter tests only check that extreme dates return 0 results, so a filter that excluded *everything* would still pass. GEN-012 is exactly such a bug, and these tests miss it.

**Why it matters:** These tests report behaviour as verified when it is not.

**Suggested fix:** Insert a video row directly, or generate a real clip under `requires_ffmpeg`, and assert the 415. Seed at least one video and assert that `media_type=video` returns exactly it. Add date-filter cases that include some images and exclude others.

**Done when:** No test has an unconditional early return, and each filter test has a non-empty expected result.

## TST-005: Add API tests for tags and settings; two error paths return 500

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/tags.py:47-105`, `backend/src/thalimage/api/settings.py:17-57`, `backend/src/thalimage/services/tag_service.py:52-67`, `:90-103`
- **Labels:** testing, backend, api

`api/tags.py` is 54% covered and `api/settings.py` 43%. No test calls any `/tags`, `/images/{hash}/tags` or `/settings` endpoint; only the service layer is tested directly (`test_tag_service.py`, `test_nsfw.py`). So the 409, 404 and PATCH handling is never exercised. Probing these endpoints found two bugs:
- `PATCH /tags/{id}` that renames a tag to an existing name returns **500**, because `update_tag` does not catch `IntegrityError`.
- `POST /images/<unknown 64-hex>/tags` returns **500**, because the FK violation is not caught (`INSERT OR IGNORE` does not suppress FK errors).

Settings persistence is also untested: nothing checks that the `show_nsfw` preference round-trips through its `"true"`/`"false"` strings.

**Why it matters:** These endpoints take user input directly, and the NSFW preference controls whether sensitive content is shown.

**Suggested fix:** Add `test_api_tags.py` and `test_api_settings.py`. Cover create, duplicate (409), rename, rename to an existing name, delete and 404, plus tagging and untagging existing and unknown images. Cover PATCH/GET round-trips for settings.

**Done when:** Both modules are at or near 100% coverage, and the two 500 cases have tests pinning the intended 4xx status.

See also: GEN-002.

## TST-006: Test migrations against populated databases, not only empty ones

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/tests/test_db.py:38-90`, `backend/src/thalimage/db/migrations/003_dynamic_source_presets.sql:1-6`, `backend/src/thalimage/db/migrations/009_nsfw_trigger_by_name.sql:26-31`
- **Labels:** testing, backend, database

Every test in `test_db.py` runs `migrate()` on a fresh, empty database. But two migrations change existing data:
- **003** deletes `collection_images` rows.
- **009** rewrites triggers and backfills `images.nsfw` from tag names, which clears flags set through the old `tags.nsfw` column.

Neither is tested with rows present. The path users actually take, upgrading an existing database with data in it, is never verified.

**Why it matters:** A migration bug silently changes or destroys user data (collections, NSFW visibility) on upgrade, and the change cannot be rolled back.

**Suggested fix:** Add tests that migrate to version N-1, insert representative rows, migrate to N and check the result. At minimum:
- **003:** manual and preset `collection_images` rows.
- **009:** images tagged `nsfw`, `NSFW` and other tags, with `tags.nsfw=1`.

**Done when:** Each data-modifying migration has a test with row assertions before and after.

## TST-007: Test ELO vote validation and source-preset pairing at the API

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/elo.py:38-41`, `:59-73`, `backend/src/thalimage/services/elo_service.py:81-109`, `backend/tests/test_api_elo.py:54-62`
- **Labels:** testing, backend, elo

The 400 branch of `post_vote` (lines 71-72) is uncovered; the only vote test uses two valid hashes. Nothing tests `winner_hash == loser_hash`, unknown hashes or a nonexistent collection. A probe shows that unknown hashes and a nonexistent collection return 400, but only because the FK check fails and the broad `except Exception` at line 71 turns that into a 400. That behaviour is accidental. A self-vote with an existing hash is accepted (GEN-010). The `/pair` lookup for a source-preset collection (line 41) is not tested at the API level either.

**Why it matters:** Bad votes permanently corrupt the rankings and the votes audit table.

**Suggested fix:** Add API tests for a self-vote with an existing hash, unknown hashes, a nonexistent collection, and `/pair` on a source-preset collection.

**Done when:** Those cases have tests asserting the intended status codes, and tests check that `elo_scores` and `votes` are unchanged after a rejected vote.

See also: GEN-010.

## TST-008: Frontend logic has no automated tests

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/package.json:10-17`, `frontend/src/lib/slideshowStore.svelte.ts`, `frontend/src/lib/browsingContext.ts:40-81`, `frontend/src/lib/swipe.ts:23-98`, `frontend/src/lib/api.ts`
- **Labels:** testing, frontend

There is no test runner (no vitest or playwright script or dependency) and no test file. `check.sh` and CI run only svelte-check, which does type-checking. Stateful logic with no tests:
- the slideshow store (419 lines);
- browsing-context persistence and back navigation (`backDestination`, `backLabel`, scroll position);
- swipe gesture thresholds;
- query-string construction in `api.ts`.

**Why it matters:** Navigation and slideshow regressions can only be caught by hand. Several of the GEN race conditions (GEN-011, GEN-013 to GEN-015) are in this code.

**Suggested fix:** Add vitest, which fits the existing vite toolchain. Write unit tests for `browsingContext.ts`, `swipe.ts`, and the slideshow store's advance, shuffle and timer logic. Wire `pnpm test` into `fe-check`.

**Done when:** `pnpm test` runs in CI through `check.sh` and covers those modules.

## TST-009: Cover the scan endpoint's conflict, failure and SSE edge paths

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/api/sources.py:130-131`, `:154-155`, `:170-186`, `backend/tests/test_api_sources.py:53-59`
- **Labels:** testing, backend, api

These paths have no test:
- the 409 "scan already running" response;
- the worker's `scan_manager.fail` path (lines 154-155);
- the SSE status for an unknown source (line 172);
- the SSE status for a source that was never scanned (the idle event, lines 177-178).

`test_trigger_scan` starts the scan on the background executor and returns without waiting. The scan thread may therefore still be writing to the test's temporary database during teardown. That is a flakiness risk, though no failure was observed (219/219 passed).

**Why it matters:** These paths drive the UI's scan progress and error reporting, and the un-awaited thread can cause intermittent test failures.

**Suggested fix:**
- In `test_trigger_scan`, drain `/scan/status` before returning.
- Test the 409 with `ScanManager.start` called beforehand.
- Test a scan failure by removing the source path after creating the source.
- Test the SSE 404 and idle event.

**Done when:** Those lines are covered, and no test leaves a scan thread running after it returns.
