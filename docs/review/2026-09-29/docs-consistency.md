# Docs consistency review: thalimage

Scope: repository root (tracked files) · Commit: 031252b (dirty working tree) · Date: 2026-09-29

## Inventory

| File | Class | Reason |
|---|---|---|
| `README.md` | current | Features, deployment, configuration, dev commands |
| `CLAUDE.md` | current | Architecture, backend layout and conventions for contributors |
| `docs/agent/phases.md` | current | Called the "current roadmap and backlog" by CLAUDE.md and README (also has dated narrative for each phase) |
| `docs/agent/reboot.org` | historical | "Archived" banner, original vision |
| `docs/agent/mvp-plan.md` | historical | "Archived" banner, plan for Sprints 1–5 |
| `docs/agent/cr_1.md` | historical | "Archived" banner, review dated 2026-04-17 |
| `docs/code-review-2026-06.md` | historical | "Archived" banner, remediation log |
| `docs/code-review-2026-07.md` | unclear | Dated review, but no Archived banner and not indexed in CLAUDE.md; some of its findings still hold |
| `docs/todos.md` | historical | "Archived" banner, log of resolved fixes |
| `backend/src/thalimage/docs/01-overview.md` … `04-scanning.md` | current | In-app user docs served at `/docs` |
| `backend/pyproject.toml` (description/metadata) | current | Packaging metadata |
| `frontend/package.json`, `frontend/static/manifest.webmanifest` | current | Packaging and PWA metadata (both consistent with the code) |
| `thalimage-dev.el`, `.dir-locals.el` (commentary) | current | Emacs dev helpers; the commentary matches the Makefile targets |
| `docker/docker-compose.yml`, `docker/Dockerfile`, `docker/entrypoint.sh` (header comments) | current | Operational comments |

## Summary

Most docs match the code: the config variables, Makefile targets, the security warning and the Docker layout all check out. The drift that matters is in the **in-app user docs** (scanning, ELO), in CLAUDE.md's layout map, and in the README feature list. The docs tree also mixes the live roadmap with archived records.

The docs reviewer's most serious finding, that preview requests above 2560px return 422 even though the docs and comments promise they are rounded down, is a functional bug. It was moved to **GEN-004**, whose fix includes aligning those docs.

## DOC-001: Scanning page says videos are catalogued without ffmpeg

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/docs/04-scanning.md:22-23`, `backend/src/thalimage/services/scan_service.py:104-108`
- **Labels:** docs, in-app-docs

The in-app page says: "Without them, video files are still catalogued but get no thumbnail." The code does the opposite. It logs "Skipping video … ffmpeg not available", increments `errors` and `continue`s, so no `images` row is written.

**Why it matters:** A user without ffmpeg sees scan errors and missing videos, while the docs say the videos are there.

**Suggested fix:** Change the sentence to say that videos are skipped and counted as errors when ffmpeg or ffprobe is missing. Alternatively, change the code to match the docs.

**Done when:** The 04-scanning text matches what `run_scan` does when `ffmpeg_available()` is False.

## DOC-002: Scanning page misdescribes the skip rule and preset sync

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/docs/04-scanning.md:3-5,19-20`, `backend/src/thalimage/services/scan_service.py:41-48,92-98,222,246-250`
- **Labels:** docs, in-app-docs

- **Skip rule:** the page says "a file already known by its hash is skipped". The code actually skips on same relative path + mtime + size (`scan_service.py:92-98`), before any hashing. A new or changed file is always hashed and upserted, even when its hash is already known.
- **Preset collections:** step 4 says the preset collection is "kept up to date as the scan runs". The code only makes sure the preset row exists after the scan (`:246-250`). Presets are dynamic views of their source (migration 003), so there is nothing to sync.
- **Step numbering:** the comments inside `run_scan` do not match its 5-step docstring; for example, line 222 says "Step 7: mark deleted files".

**Why it matters:** Users get the wrong idea of when files are re-read, for example after an edit, a move or a duplicate copy.

**Suggested fix:** Describe the path + mtime + size skip rule, describe presets as live views of their source, and renumber the step comments to match the docstring.

**Done when:** The 04-scanning text and the `run_scan` comments agree with `scan_service.py`.

## DOC-003: README feature list is stale and says thumbnails are on-demand

- **Severity:** medium
- **Confidence:** high
- **Location:** `README.md:5-14`, `backend/src/thalimage/services/scan_service.py:148`, `backend/src/thalimage/api/images.py:102-110`
- **Labels:** docs, readme

`README.md:14` says "WebP thumbnails — … with on-demand thumbnail generation". In the code, thumbnails are generated during the scan (`scan_service.py:148`), and `/thumb` returns 404 when one is missing. Only *previews* are generated on demand.

The list also leaves out shipped features that `phases.md` marks ✓:
- ELO voting
- tags and NSFW handling
- archiving
- video support
- the slideshow
- display-sized previews
- the in-app docs at `/docs`
- the mobile layout and PWA manifest

**Why it matters:** The README is the entry point, and right now it misstates one feature and hides most of the others.

**Suggested fix:** Change the thumbnail bullet to "generated at scan time" and add a "previews on demand" bullet. Add one bullet per shipped feature, and link to the in-app `/docs`.

**Done when:** Every README feature bullet matches the code, and every phase marked ✓ in `phases.md` has a matching bullet.

## DOC-004: CLAUDE.md backend layout lists a nonexistent module and omits several

- **Severity:** medium
- **Confidence:** high
- **Location:** `CLAUDE.md:24-29,35`, `backend/src/thalimage/core/`, `backend/src/thalimage/services/`, `backend/src/thalimage/config.py:77-79`
- **Labels:** docs, contributor

- **core/:** `CLAUDE.md:27` lists "scanner, metadata, thumbnails, hasher, analyzer". There is no `analyzer`. The actual modules are hasher, metadata, previews, scanner, thumbnails and video.
- **services/:** line 28 omits `elo_service`, `tag_service`, `docs_service` and `scan_manager`.
- **Unlisted files:** the layout does not mention `deps.py`, `version.py`, the in-app docs directory `src/thalimage/docs/`, or `frontend/`.
- **Cache paths:** line 35 gives the thumbnail location as `{cache_dir}/thumbs/...`, but there is no `cache_dir` setting. The real default is `{data_dir}/cache/thumbs`, which `THALIMAGE_THUMB_DIR` can override (`config.py:77-79`). The previews directory (`{data_dir}/cache/previews/{size}/...`) is not listed.

**Why it matters:** Contributors and agents use this file as the map of the code, and it points to a module that does not exist while leaving out several that do.

**Suggested fix:** Regenerate the layout list from the tree. Add `docs/`, `deps.py`, `version.py` and `frontend/`, and describe the cache paths in terms of the real settings.

**Done when:** Every module named in CLAUDE.md exists, and every file under `core/` and `services/` is named.

## DOC-005: Docs tree mixes the current roadmap with archives; one review is unindexed

- **Severity:** medium
- **Confidence:** high
- **Location:** `README.md:186-190`, `CLAUDE.md:47-53`, `docs/code-review-2026-07.md:1-3`, `docs/agent/phases.md`
- **Labels:** docs, organization

- **Archive claim:** `README.md:190` says every file under `docs/` is historical and "marked as archived". That is not true of `docs/agent/phases.md` (the live roadmap) or of `docs/code-review-2026-07.md`, which has no banner.
- **Unindexed review:** `code-review-2026-07.md` is missing from the CLAUDE.md index. Its HIGH issue, one `sqlite3.Connection` shared across request threads (`app.py:26-28`), still holds (see GEN-002) but is not tracked in `phases.md`.
- **Undiscoverable docs:** neither README nor CLAUDE.md mentions the in-app user docs or the Emacs helpers.
- **Duplicate commands:** the dev commands are listed in both README and CLAUDE.md.

**Why it matters:** Readers cannot tell which files are live, and open review findings get lost.

**Suggested fix:** Adopt the layout proposed in the detail file.

**Done when:** Every file under `docs/` is either current and indexed, or sits in `docs/archive/` with an Archived banner. The open 2026-07 items are either resolved or tracked in the roadmap.

**Details:** [details/DOC-005.md](details/DOC-005.md)

## DOC-006: phases.md has stale "today" text and contradicts itself

- **Severity:** low
- **Confidence:** high
- **Location:** `docs/agent/phases.md:34-36,51-56,61-62,113-121,221`, `backend/src/thalimage/core/scanner.py:8-10`
- **Labels:** docs, roadmap

`phases.md` is billed as current, yet it contains present-tense statements that are no longer true:
- **Phase 5.3 baseline (`:113-121`):** says "only two sizes are served today… The viewer, slideshow and ELO all use the original" and "preloads three neighbours at full resolution". Both have since been fixed; preloading now uses `previewUrl` (`image/[hash]/+page.svelte:297-310`).
- **Phase 2.5 (`:34-36,54`):** describes presets as "static… auto-synced on scan". Phase 3 (`:79-80`) and migration 003 made them dynamic.
- **Phase numbering (`:51,61-62`):** says dynamic collections / `'dynamic_query'` arrive in Phase 3. Phase 3 is marked ✓ without them, and Phase 5 (`:89-92`) now owns them.
- **Phase 8 (`:221`):** lists "TIFF/GIF/AVIF support expansion", but `.tiff` and `.gif` are already scanned (`scanner.py:9`).

**Why it matters:** Readers of the roadmap get a wrong picture of what is still open.

**Suggested fix:** Put the baseline text in the past tense or mark it "(before 5.3)". Add "superseded by Phase 3" notes. Move the Phase 3 references to Phase 5. Cut the Phase 8 bullet down to AVIF.

**Done when:** No sentence in `phases.md` describes, as current, behaviour the code no longer has.

## DOC-007: README deployment omits required THALIMAGE_IMAGES and its single mount

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:94-108`, `docker/docker-compose.yml:66-71`
- **Labels:** docs, deployment

The README says to "Mount each one separately" and shows `/photos/ai:/images/ai:ro`. The shipped compose file instead requires `THALIMAGE_IMAGES` (`${THALIMAGE_IMAGES:?…}`) and mounts it as a single `/images` tree. The README never names this variable, and `compose up` fails when it is unset. Only `docker/.env.example` (untracked) documents it.

**Why it matters:** An operator following the README gets a compose error, or ends up with a volume layout that differs from the README.

**Suggested fix:** Document `THALIMAGE_IMAGES` as required. Say that the default mounts one tree at `/images`, and that extra folders are added as extra lines, as the commented example shows.

**Done when:** Following the README alone, with the shipped compose file, produces a working deployment.

## DOC-008: Minor README reference drift (check.sh, DEBUG, config.toml)

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:177`, `check.sh:15-22`, `README.md:139`, `backend/src/thalimage/__main__.py:15`, `README.md:125-129`, `docker/entrypoint.sh:20-22`
- **Labels:** docs, readme

- **check.sh:** `README.md:177` says `./check.sh` "runs the backend lint/typecheck/test gate". It also runs `make fe-check` whenever `frontend/node_modules` exists (`check.sh:17-19`).
- **THALIMAGE_DEBUG:** the README table calls it "Debug mode". Its only effect is uvicorn `reload=` (`__main__.py:15`), i.e. auto-reload rather than debug output.
- **config.toml in containers:** the README steers container users away from `config.toml`, but `entrypoint.sh:20-22` deliberately sets `HOME=/data` so that `/data/.thalimage/config.toml` works.

**Why it matters:** These are small inaccuracies in reference text.

**Suggested fix:** Mention the conditional frontend check. Describe DEBUG as "auto-reload on code changes (development only)". Either document the `/data/.thalimage/config.toml` location or drop the HOME export.

**Done when:** All three README statements match the code.

## DOC-009: ELO docstring and in-app page misstate the pair pool

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/elo_service.py:23-27,50-60,69-71`, `backend/src/thalimage/docs/02-elo.md:26-30`
- **Labels:** docs, elo

The `get_pair` docstring claims it "Favors images with fewer matches to ensure even coverage". The in-app page (`02-elo.md:32-38`) and `phases.md:148-157` both correctly say that sampling within the pool is uniform and under-favours new images. `02-elo.md:26-28` lists the candidate filters as not deleted, not archived and NSFW. It leaves out the active date-range, aspect-ratio and media-type filters (`elo_service.py:50-57`), which also narrow the pool before the quartile is taken.

**Why it matters:** The docstring contradicts the documented, known limitation.

**Suggested fix:** Reword the docstring to "Draws uniformly from the least-matched quarter", and add the active filters to the candidate description in 02-elo.

**Done when:** The docstring and 02-elo agree with `get_pair`.
