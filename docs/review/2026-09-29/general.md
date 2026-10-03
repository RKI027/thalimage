# General review: thalimage

Scope: repository root (tracked files) · Commit: e28c431 (dirty working tree) · Date: 2026-09-29

This review covered the backend services, API, core modules and migrations, and on the frontend the grid, viewer, ELO pages, `api.ts` and the service worker.

The most serious problems are in SQLite transaction handling:
- A scan holds one write transaction for its whole run.
- Failed writes on the shared request connection are never rolled back.
- Deleting a collection or source that has ELO data fails on foreign keys.

The main bugs were checked with scratch scripts run against the real modules; no repo files were changed. Those checks covered the lock, the FK failures, NULL-cursor pagination, the NSFW trigger gaps and the preview size limit. The service worker is correct: it does not cache `/api`.

GEN-004 was first reported by the docs reviewer and moved here, because it is a functional bug.

## GEN-001: Scan holds one write transaction for its whole run, locking out API writes

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:78-220`, `backend/src/thalimage/api/sources.py:141-147`, `backend/src/thalimage/db/engine.py:10`
- **Labels:** bug, backend, concurrency

`run_scan` inserts every new or changed file on the worker connection. Python's implicit BEGIN opens a write transaction at the first INSERT, and `conn.commit()` runs only after the loop ends (line 220). So the lock is held while every file is hashed, probed with ffprobe/ffmpeg and thumbnailed. A write on any other connection waits for the default 5 s `timeout` (engine.py:10 sets none) and then raises `database is locked`. Reproduced: with a scan paused mid-loop, an INSERT on the request connection failed after 5.2 s.

**Why it matters:** For the whole duration of a large scan, archiving, voting, tagging, collection edits and settings changes all return 500. A second concurrent scan is also blocked, even though `concurrent_scans` defaults to True (config.py:52).

**Suggested fix:** Commit in small batches inside the loop (every N files, or every second). Set a `busy_timeout` (or `timeout=` on `connect()`) so short contention waits instead of failing.

**Done when:** A test runs a scan whose progress callback blocks mid-loop, and a write on a second connection succeeds within the timeout.

## GEN-002: Failed writes are never rolled back on the shared request connection

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/app.py:26-29`, `backend/src/thalimage/api/tags.py:52-55`, `backend/src/thalimage/api/sources.py:61-68`, `backend/src/thalimage/services/collection_service.py:141-147`, `backend/src/thalimage/services/tag_service.py:60-67`, `backend/src/thalimage/api/elo.py:65-72`
- **Labels:** bug, backend, concurrency

No code path calls `rollback()`. The whole app uses one `sqlite3.Connection` with `check_same_thread=False`, shared by FastAPI's threadpool. When a write fails, the implicit transaction stays open and keeps the write lock (verified: `in_transaction` is True after an FK failure, and a second connection then gets `database is locked`). The lock is held until some unrelated request commits, and that commit also persists whatever partial work is pending. Failures that trigger this include a 409 on a duplicate tag or source, adding an unknown hash to a collection, renaming a tag to an existing name, and tagging an unknown image.

**Why it matters:** After a routine error, the scan worker's writes fail until another request happens to commit. That commit can also persist half of an unrelated operation.

**Suggested fix:** Wrap each write service in `with conn:` (commit on success, rollback on exception), or add a request-scoped transaction dependency. Better still, open one connection per request.

**Done when:** After any failing write endpoint, `db.in_transaction` is False and a second connection can write immediately.

**Details:** [details/GEN-002.md](details/GEN-002.md)

## GEN-003: Deleting a collection or source with ELO data fails with 500

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/collection_service.py:122-131`, `backend/src/thalimage/api/sources.py:85-89`, `backend/src/thalimage/db/migrations/001_initial.sql:46,64,72`
- **Labels:** bug, backend, collections

`votes.collection_id`, `elo_scores.collection_id` and `collections.parent_id` all reference `collections(id)` with no `ON DELETE` clause, and `foreign_keys=ON`. This breaks two deletions:

- **Collections:** once a collection has had a single vote, `DELETE FROM collections` raises `IntegrityError: FOREIGN KEY constraint failed` (verified). The error is not caught, so the endpoint returns 500 and leaves the transaction open (see GEN-002).
- **Sources:** `delete_source` deletes the source's preset collection *before* it deletes the `elo_scores`/`votes` rows. So deleting a source whose preset collection was ever used for ELO also returns 500. Reproduced during consolidation: scan, one vote on the preset, `DELETE /api/v1/sources/1` → 500.

**Why it matters:** Users cannot delete any collection they have ranked, nor any source they have ranked through its preset collection. Each attempt also leaves the database locked.

**Suggested fix:** In `delete_collection` and `delete_source`, delete the `votes` and `elo_scores` rows for the collection first, and re-parent or reject child collections, all in one transaction. Alternatively, add a migration that sets `ON DELETE CASCADE`.

**Done when:** Two tests pass. One records a vote in a manual collection, deletes the collection and gets 204. The other records a vote on a source preset, deletes the source and gets 204. In both, no `votes` or `elo_scores` rows remain for the deleted collection.

## GEN-004: Previews requested above 2560px get 422, so the viewer breaks on hi-DPI screens

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/images.py:116-121`, `frontend/src/lib/api.ts:80-87`, `backend/src/thalimage/core/previews.py:24-29`, `backend/src/thalimage/docs/03-delivery.md:25-28`
- **Labels:** bug, backend, frontend

`displaySize()` sends `max(innerWidth, innerHeight) * min(dpr, 2)` with no upper cap. `nearest_size()` is meant to clamp larger values to 2560. But the endpoint declares `le=PREVIEW_SIZES[-1]`, so FastAPI rejects the request before the clamp can run. Verified: `GET /api/v1/images/<hash>/preview?size=3024` returns `422 "Input should be less than or equal to 2560"`.

The code comment (`api.ts:80-82`), the Query `description` and the in-app page `03-delivery.md` all promise that such requests are snapped down to the largest size.

**Why it matters:** A 1512px-wide retina laptop, or any window wider than 1280 CSS px at dpr 2, gets no image in the viewer, the slideshow or the ELO page.

**Suggested fix:** Drop `le=` (keep `ge=1`) so `nearest_size` clamps, or cap the value in `displaySize()`. State in 03-delivery that requests above 2560 get the 2560 bucket.

**Done when:** `preview?size=5000` returns 200 with `X-Preview-Size: 2560`, a test covers it, and the comment, the description and the in-app page all match that behaviour.

## GEN-005: "Created" sort stops after one page when `file_created` is NULL (always on Linux/Docker)

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:85-90`, `backend/src/thalimage/services/image_service.py:194-207,224`, `frontend/src/lib/components/SortControls.svelte:19`
- **Labels:** bug, backend, pagination

`file_created` comes only from `st_birthtime`. That attribute does not exist on Linux under Python 3.11, which is the Docker runtime, so `file_created` is NULL for every image there. The next cursor then becomes `"None|<hash>"`. The comparison `(file_created, content_hash) > ('None', ?)` evaluates to NULL for rows where `file_created` is NULL, and to false for ISO dates. Verified with a pagination loop: ascending returns only the first page, and descending never returns the NULL rows after page 1.

**Why it matters:** In the Docker deployment, sorting by Created shows only the first 500 images. On macOS, images without a birthtime vanish after page 1.

**Suggested fix:** Sort by `COALESCE(file_created, file_modified)`, or backfill that value at scan time, so the sort key is never NULL. Encode the cursor from the same expression.

**Done when:** A test with NULL `file_created` rows pages through all rows in both directions under `sort=date_created`.

## GEN-006: Same content in two sources resolves to a non-existent path

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:118-135,150-177,67-73`, `backend/src/thalimage/services/image_service.py:260-274`
- **Labels:** bug, backend, scanning

On a hash conflict, the upsert updates `filename` and `relative_path` but not `source_id`. So when source B contains a copy of a file already indexed from source A, the row ends up with `source_id=A` and B's `relative_path`. `resolve_file_path` then joins A's root with B's path, and `/file` and `/preview` return 404. Rescanning A flips the path back, and the next scan of B flips it again. The testing reviewer reproduced this independently.

Duplicates inside a single source have a related problem: they are re-hashed on every scan, because `existing` is keyed by one `relative_path`.

**Why it matters:** Duplicated AI images, such as copies kept in a "favorites" folder, show up in the grid but fail to open.

**Suggested fix:** Pick a deliberate rule. Either update `source_id` together with `relative_path`, or keep the first location and skip the path update while that path still exists on disk. Key `existing` so duplicates are recognised as unchanged.

**Done when:** A test scans two sources containing an identical file, and `resolve_file_path` returns an existing file after each scan, in either order.

## GEN-007: An unreachable source root marks every image in that source deleted

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/scanner.py:20-21,36-37`, `backend/src/thalimage/services/scan_service.py:222-237`
- **Labels:** bug, backend, scanning

`scan_directory` returns `[]` when the root does not exist, and it swallows `OSError` and `PermissionError`. `os.walk` also silently skips unreadable subdirectories. `run_scan` then treats every hash it did not see as deleted. So scanning an unmounted NAS, or a folder with a permission problem, soft-deletes the whole source (or subtree), and the scan still reports success.

**Why it matters:** A transient mount failure empties the library view until the next successful rescan, and the user sees no error.

**Suggested fix:** Fail the scan when the root is missing or unreadable. Pass `onerror` to `os.walk`, and skip the deletion pass for subtrees that could not be read.

**Done when:** Scanning a source whose path no longer exists ends in `phase=error` and leaves the `deleted` flags unchanged.

## GEN-008: NSFW flag is not recomputed when the "nsfw" tag is deleted or a tag is renamed

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/db/migrations/009_nsfw_trigger_by_name.sql:7-24`, `backend/src/thalimage/services/tag_service.py:60-74`
- **Labels:** bug, backend, tags

The NSFW triggers fire only on inserts into and deletes from `image_tags`, and the removal trigger's `WHEN` clause looks up the tag's name. When the "nsfw" tag itself is deleted, its `image_tags` rows go through `ON DELETE CASCADE` after the tag row is gone, so the lookup finds nothing and the trigger does not fire. Verified: after `delete_tag("nsfw")` the image stays `nsfw=1`. Renames are not handled either (also verified): renaming "spicy" to "nsfw" does not flag the tagged images, and renaming "nsfw" to something else does not unflag them.

**Why it matters:** Images get stuck hidden, and the user cannot un-flag them without re-creating the tag. Or NSFW images show when NSFW display is off.

**Suggested fix:** Recompute `images.nsfw` for the affected hashes inside `delete_tag` and `update_tag`, or add `BEFORE DELETE` and `AFTER UPDATE OF name` triggers on `tags`.

**Done when:** Tests show that deleting the "nsfw" tag clears the flag, and that renaming a tag to or from "nsfw" updates it.

## GEN-009: ELO page records duplicate votes on key repeat or double click

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/routes/elo/[collectionId]/+page.svelte:76-90,96-110`
- **Labels:** bug, frontend, elo

`vote()` has no in-flight guard. `selectedSide` is set but never checked, and the pair is only replaced 300 ms after the POST resolves. So pressing ArrowLeft twice, holding the key down or double-tapping each posts another vote for the same pair. Each extra vote also schedules another `loadPair()`, which skips a pair.

**Why it matters:** Accidental repeat votes skew the rankings, and the vote counter over-counts.

**Suggested fix:** Return early from `vote()` when `selectedSide !== null` or a vote is pending, and ignore `e.repeat` in `onKeydown`.

**Done when:** Pressing a vote key twice in quick succession sends exactly one POST per pair.

## GEN-010: `record_vote` read-modify-write is not atomic and accepts a self-vote

- **Severity:** medium
- **Confidence:** medium
- **Location:** `backend/src/thalimage/services/elo_service.py:89-110`, `backend/src/thalimage/api/elo.py:59-73`
- **Labels:** bug, backend, elo

`record_vote` reads the scores (lines 89-90) before any write, so the implicit transaction only starts at the INSERT. If two votes involving the same image run at the same time on the shared connection, both compute from the same old score. The second upsert then overwrites the first score while `matches` is incremented twice: a lost update. `winner_hash == loser_hash` is also accepted. Verified: a self-vote changed the score from 1516 to 1500 and added 2 to `matches`. The hashes are not checked against collection membership either.

**Why it matters:** ELO scores silently drift away from what the recorded votes imply.

**Suggested fix:** Run the reads and writes in one `BEGIN IMMEDIATE` transaction, or compute the new score in SQL. Reject `winner == loser`, and hashes that are not in the collection, with 400.

**Done when:** Concurrent votes produce the same scores as replaying the votes one after another, and a self-vote returns 400.

## GEN-011: Grid ignores sort, filter or collection changes while a page load is in flight

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/routes/+page.svelte:35-37,80-93,119-134`, `frontend/src/routes/collections/[id]/+page.svelte:39-41,60-76,122-128`
- **Labels:** bug, frontend, race-condition

`fetchImages` starts with `if (loading) return;`. So a reset requested during any fetch, including an infinite-scroll "load more", is silently dropped. The controls then show the new sort or filters while the grid keeps the old results. On the collection page, navigating from collection A to collection B while A's fetch is pending shows A's images under B's header, and B's fetch never runs. The collection page's `fetchImages` also has no `catch`.

**Why it matters:** The grid can show images that do not match the visible sort, filter or collection. This is most likely on the slow links the app is optimised for.

**Suggested fix:** Let a reset supersede an in-flight request. Tag each request with a token or AbortController, and discard responses whose token is stale instead of refusing to start a new request.

**Done when:** Changing the sort, or switching collection, while a load is pending always ends with the grid matching the latest parameters.

## GEN-012: `date_to` filter excludes the selected end day

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:77-79`, `frontend/src/lib/components/FilterBar.svelte:42-46`
- **Labels:** bug, backend, filters

The UI sends `date_to` as `YYYY-MM-DD`, but `file_modified` is a full ISO timestamp such as `2024-01-31T10:00:00+00:00`. `file_modified <= '2024-01-31'` is false for every timestamp on that day, so the end date is excluded from the range. A range that covers a single day returns nothing. ELO pair selection uses the same clause.

**Why it matters:** Date filtering silently drops the last day of every range.

**Suggested fix:** Compare with `file_modified < date(date_to, '+1 day')`, or use `substr(file_modified, 1, 10) <= ?` when only a date is given.

**Done when:** With `date_from = date_to = D`, the results include images modified on D.

## GEN-013: Viewer prev/next ignores the grid's source and filters and breaks past 1000 images

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/lib/browsingContext.ts:5`, `frontend/src/routes/+page.svelte:85,89-93,104`, `frontend/src/routes/image/[hash]/+page.svelte:36,83-106,110-126`
- **Labels:** bug, frontend, viewer

The "all" browsing context stores only the sort and direction. It does not record `sourceId` or the filters, and `onFilterChange` does not update it. So `loadNeighbors` walks the unfiltered library. It also fetches only the first `NEIGHBOR_LIMIT` (1000) rows. For an image outside those rows, or one excluded by the context, `currentIndex` is -1: → jumps to the first image in the library and ← does nothing.

**Why it matters:** Arrow-key and slideshow navigation leaves the filtered set, and in large libraries it jumps back to the start.

**Suggested fix:** Store `sourceId` and the filters in the "all" context. Fetch neighbours in a cursor-based window around the current image rather than the first 1000.

**Done when:** In a filtered grid, ←/→ from any image, including one beyond position 1000, moves to its neighbours within that filtered set.

## GEN-014: Viewer shows a stale image when image responses arrive out of order

- **Severity:** low
- **Confidence:** medium
- **Location:** `frontend/src/routes/image/[hash]/+page.svelte:68-72,236-239`
- **Labels:** bug, frontend, race-condition

Each hash change calls `load(hash)`, which assigns `image = await getImage(hash)` without checking that `hash` is still the current one. With fast ←/→ presses or slideshow advances on a slow link, an earlier response can arrive last. The page then shows image X while the URL and index say image Y, and archive or tag actions apply to X.

**Why it matters:** The wrong image is displayed, and edits apply to it.

**Suggested fix:** Before assigning, check that `hash === $page.params.hash`, or use a request counter or AbortController.

**Done when:** A delayed earlier response never replaces the image for the current URL.

## GEN-015: A prefetched ELO pair from the previous collection can leak into the next

- **Severity:** low
- **Confidence:** medium
- **Location:** `frontend/src/routes/elo/[collectionId]/+page.svelte:39-48,120-128`
- **Labels:** bug, frontend, elo

When the route parameter changes, the page sets `nextPair = null`. But a `prefetchNext()` still in flight for the old collection can resolve afterwards and set `nextPair` again. The next `loadPair()` then shows the old collection's pair, and votes on it are recorded under the new collection id. The comment at line 123 says this cannot happen.

**Why it matters:** Votes get recorded against images from the wrong collection.

**Suggested fix:** Tag each prefetch with the collection id and filters it was issued for, and discard its result on a mismatch.

**Done when:** Switching collection while a prefetch is pending never shows a pair from the previous collection.

## GEN-016: No indexes on `images` for source or sort columns

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/db/migrations/001_initial.sql:12-27`, `backend/src/thalimage/services/image_service.py:180-212`, `backend/src/thalimage/services/scan_service.py:68-73`
- **Labels:** performance, backend, db

The migrations index only `collections(source_id)` (a partial index) and `image_tags`. Every grid page runs a `COUNT(*)` plus a filtered query that fully scans `images` and sorts it by `filename`, `file_modified` or another sort column. The scan's `WHERE source_id = ?` lookups are full scans too. This was not benchmarked; the cost grows linearly with library size, on every page fetch.

**Why it matters:** Page latency and CPU use grow with the library, which hurts infinite scroll on large collections.

**Suggested fix:** Add indexes such as `(deleted, archived, <sort col>, content_hash)` for the main sorts, plus one on `images(source_id)`.

**Done when:** `EXPLAIN QUERY PLAN` for the default list query and the scan queries shows index use rather than `SCAN images` + `USE TEMP B-TREE FOR ORDER BY`.

## GEN-017: Preview temp file is unique per process only, so concurrent requests collide

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/core/previews.py:65-72`
- **Labels:** bug, backend, concurrency

The temp file is named `dest.with_suffix(f".{os.getpid()}.tmp")`, but requests run as threads in a single process. So two simultaneous requests for the same preview (for example the viewer plus a prefetch) write to the same temp path. The first `replace` moves the file away, and the second `tmp.replace(dest)` raises `FileNotFoundError`, a 500. Worse, one request can truncate the file while the other is writing it, leaving a partial file cached permanently under an immutable URL. This follows from reading the code; it has not been reproduced.

**Why it matters:** Occasional 500s, and possibly a corrupt preview that is never regenerated.

**Suggested fix:** Create the temp file with `tempfile.NamedTemporaryFile(dir=dest.parent, delete=False)`, or add the thread id or a uuid to the name.

**Done when:** Parallel `generate_preview` calls for the same hash all succeed and produce a valid WebP.

## GEN-018: Cursor splits on the first `|`, so filenames containing `|` break name pagination

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:196-207,224`
- **Labels:** bug, backend, pagination

The cursor is built as `f"{sort_value}|{hash}"` and parsed with `cursor.split("|", 1)`. For a filename such as `a|b.png`, the parsed sort value is `a` and the hash is `b.png|<hash>`, so the next page starts at the wrong position and rows are duplicated or skipped. Separately, a malformed ELO cursor makes `float()` raise `ValueError`, which returns 500 instead of 400.

**Why it matters:** Pagination is wrong for valid filenames, and bad input causes a server error.

**Suggested fix:** Use `rsplit("|", 1)`, since the hash never contains `|`, or encode the cursor as base64 JSON. Validate the cursor and return 400 when it cannot be parsed.

**Done when:** A test with `|` in filenames pages through every row exactly once, and a garbage cursor returns 400.
