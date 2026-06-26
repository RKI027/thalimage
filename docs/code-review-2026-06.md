# Code Review Remediation — June 2026

Tracks the issues found in the full idiom/pattern/organization + security review and
how each was fixed. One commit per issue; commit subjects referenced below.

## High — correctness & security

### 1. Cursor pagination broken for `date_modified` / `date_created` / `size` sorts
`list_images` returned `ImageSummary` rows (which lack the date/size columns) and built
the next-page cursor with `getattr(last, "file_modified", last.filename)`, always falling
back to `filename`. The cursor then carried a filename while the WHERE clause compared it
against the real sort column, corrupting page boundaries (duplicated/skipped rows) for
every sort except `name`/`aspect_ratio`.

**Fix:** select the active sort column alongside the summary columns and carry its real
value in the cursor. Added a regression test paginating by `date_modified` and `size`.

### 2. Single SQLite connection shared across request threads and the scan worker
The app stored one `sqlite3.Connection` on `app.state.db` and the background scan reused
it for a long write transaction while HTTP handlers read/wrote through the same object —
not safe across threads even with `check_same_thread=False`.

**Fix:** the scan worker opens its own connection from the resolved DB path; request
handlers keep the shared connection.

### 3. `asyncio.Event.set()` called from the scan worker thread
`ScanManager.update()` runs in the executor thread but signalled an `asyncio.Event`,
which is not thread-safe and could fail to wake the SSE waiter.

**Fix:** capture the running loop at scan start and notify via
`loop.call_soon_threadsafe`. Replaced the deprecated `get_event_loop()` in the scan
trigger with `get_running_loop()`.

### 4. Path traversal in the SPA fallback
`@app.get("/{path:path}")` served `FileResponse(frontend_dir / path)` with no containment
check; the `:path` converter matches `..` segments, allowing arbitrary file reads.

**Fix:** resolve the candidate and confirm it is contained within the frontend build dir
before serving; otherwise fall back to `index.html`.

## Medium — security posture & robustness

### 5. Wildcard CORS on an unauthenticated localhost media server
`allow_origins=["*"]` let any visited web page drive the API. The frontend reaches the API
same-origin (vite proxies `/api` in dev/preview; production serves the SPA itself), so
cross-origin access was never required.

**Fix:** made allowed origins a config setting (`cors_origins`) defaulting to empty (no
cross-origin access). The middleware is only added when origins are configured.

### 6. `content_hash` path params not validated
Hashes flowed straight into filesystem paths for thumbnails. Traversal isn't currently
reachable (single-segment route), but the constraint was implicit.

**Fix:** validate the `{content_hash}` path param against `^[0-9a-f]{64}$`.

### 7. Scan errors swallowed without logging
`run_scan`'s per-file `except Exception` incremented an error counter but discarded the
file and exception, making failures undiagnosable.

**Fix:** log the offending path and exception at warning level.

### 8. `add_images` returned an inflated count
It incremented `added` unconditionally despite `INSERT OR IGNORE`, counting attempts
rather than insertions.

**Fix:** track real insertions via `total_changes`.

## Low — idioms / organization

### 9. Duplicated filter-builder logic
`image_service._apply_filters` and `elo_service._append_filters` reimplemented the same
date/aspect/media-type WHERE clauses.

**Fix:** extracted a shared filter helper.

### 10. Function-local `Path` import in `resolve_file_path`
**Fix:** hoisted to module scope.

### 11. Fragile ALTER-detection in the migration runner
`_statements_to_script` contained `upper[3] in ("ADD", "ADD")` (duplicated literal).

**Fix:** reuse the existing `_parse_add_column` regex to detect ADD COLUMN statements.

### 12. `make fe-lint` referenced a non-existent `pnpm lint` script
**Fix:** pointed it at the real `pnpm check` (svelte-check).

## Deliberately not changed

- **`record_vote` input validation.** It is only invoked from a controlled internal path
  that already guarantees distinct, in-collection hashes. Adding library-style guards
  (winner ≠ loser, membership checks) would be defensive beyond what the call sites
  require, so it was left as-is.
- **Broad rename of the three `get_settings` meanings.** Cosmetic; the churn across the
  codebase outweighed the readability gain. Left as-is.
