# Full review: thalimage — 2026-09-29

- **Scope:** repository root, files tracked by git (`git ls-files`), excluding `docs/review/`.
- **Commit:** `e28c431` (chore: release 0.5.0). **The working tree was dirty**: the reviewed contents of `CLAUDE.md`, `README.md`, `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/entrypoint.sh` and `docs/agent/phases.md` include uncommitted edits.
- **Date:** 2026-09-29

## Counts

| Category | Critical | High | Medium | Low | Total |
|---|---|---|---|---|---|
| [Security](security.md) | 0 | 0 | 1 | 2 | 3 |
| [Organization](organization.md) | 0 | 0 | 5 | 14 | 19 |
| [Docs consistency](docs-consistency.md) | 0 | 0 | 5 | 4 | 9 |
| [Testing](testing.md) | 0 | 2 | 6 | 1 | 9 |
| [Packaging](packaging.md) | 0 | 0 | 2 | 3 | 5 |
| [General](general.md) | 0 | 6 | 7 | 5 | 18 |
| **Total** | **0** | **8** | **26** | **29** | **63** |

## Findings by severity

### High

- GEN-001 — [Scan holds one write transaction for its whole run, locking out API writes](general.md#gen-001-scan-holds-one-write-transaction-for-its-whole-run-locking-out-api-writes)
- GEN-002 — [Failed writes are never rolled back on the shared request connection](general.md#gen-002-failed-writes-are-never-rolled-back-on-the-shared-request-connection)
- GEN-003 — [Deleting a collection or source with ELO data fails with 500](general.md#gen-003-deleting-a-collection-or-source-with-elo-data-fails-with-500)
- GEN-004 — [Previews requested above 2560px get 422, so the viewer breaks on hi-DPI screens](general.md#gen-004-previews-requested-above-2560px-get-422-so-the-viewer-breaks-on-hi-dpi-screens)
- GEN-005 — ["Created" sort stops after one page when `file_created` is NULL](general.md#gen-005-created-sort-stops-after-one-page-when-file_created-is-null-always-on-linuxdocker)
- GEN-006 — [Same content in two sources resolves to a non-existent path](general.md#gen-006-same-content-in-two-sources-resolves-to-a-non-existent-path)
- TST-001 — [Test that deleting a source cascades correctly and loses nothing else](testing.md#tst-001-test-that-deleting-a-source-cascades-correctly-and-loses-nothing-else)
- TST-002 — [Cover the scan's changed-file, duplicate-content, video and error paths](testing.md#tst-002-cover-the-scans-changed-file-duplicate-content-video-and-error-paths)

### Medium

- SEC-001 — [Entrypoint chowns the Tailscale node state to the app user](security.md#sec-001-entrypoint-chowns-the-tailscale-node-state-to-the-app-user)
- ORG-001 — [Define the video-extension list once per side](organization.md#org-001-define-the-video-extension-list-once-per-side)
- ORG-002 — [Pull the shared gallery logic out of the two grid pages](organization.md#org-002-pull-the-shared-gallery-logic-out-of-the-two-grid-pages)
- ORG-003 — [Merge the duplicated `images` upsert in the scan service](organization.md#org-003-merge-the-duplicated-images-upsert-in-the-scan-service)
- ORG-004 — [Remove the dead `tags.nsfw` flag from the service, API and client](organization.md#org-004-remove-the-dead-tagsnsfw-flag-from-the-service-api-and-client)
- ORG-005 — [Share the ImageSummary column list and row conversion](organization.md#org-005-share-the-imagesummary-column-list-and-row-conversion)
- DOC-001 — [Scanning page says videos are catalogued without ffmpeg](docs-consistency.md#doc-001-scanning-page-says-videos-are-catalogued-without-ffmpeg)
- DOC-002 — [Scanning page misdescribes the skip rule and preset sync](docs-consistency.md#doc-002-scanning-page-misdescribes-the-skip-rule-and-preset-sync)
- DOC-003 — [README feature list is stale and says thumbnails are on-demand](docs-consistency.md#doc-003-readme-feature-list-is-stale-and-says-thumbnails-are-on-demand)
- DOC-004 — [CLAUDE.md backend layout lists a nonexistent module and omits several](docs-consistency.md#doc-004-claudemd-backend-layout-lists-a-nonexistent-module-and-omits-several)
- DOC-005 — [Docs tree mixes the current roadmap with archives; one review is unindexed](docs-consistency.md#doc-005-docs-tree-mixes-the-current-roadmap-with-archives-one-review-is-unindexed)
- TST-003 — [Test AI-parameter and EXIF extraction on real metadata](testing.md#tst-003-test-ai-parameter-and-exif-extraction-on-real-metadata)
- TST-004 — [Remove the vacuous early return in the video preview test](testing.md#tst-004-remove-the-vacuous-early-return-in-the-video-preview-test)
- TST-005 — [Add API tests for tags and settings; two error paths return 500](testing.md#tst-005-add-api-tests-for-tags-and-settings-two-error-paths-return-500)
- TST-006 — [Test migrations against populated databases, not only empty ones](testing.md#tst-006-test-migrations-against-populated-databases-not-only-empty-ones)
- TST-007 — [Test ELO vote validation and source-preset pairing at the API](testing.md#tst-007-test-elo-vote-validation-and-source-preset-pairing-at-the-api)
- TST-008 — [Frontend logic has no automated tests](testing.md#tst-008-frontend-logic-has-no-automated-tests)
- PKG-001 — [Built wheel ships without the SPA; runtime needs a source-tree install](packaging.md#pkg-001-built-wheel-ships-without-the-spa-runtime-needs-a-source-tree-install)
- PKG-002 — [pnpm version is not pinned (no `packageManager` field)](packaging.md#pkg-002-pnpm-version-is-not-pinned-no-packagemanager-field)
- GEN-007 — [An unreachable source root marks every image in that source deleted](general.md#gen-007-an-unreachable-source-root-marks-every-image-in-that-source-deleted)
- GEN-008 — [NSFW flag is not recomputed when the "nsfw" tag is deleted or a tag is renamed](general.md#gen-008-nsfw-flag-is-not-recomputed-when-the-nsfw-tag-is-deleted-or-a-tag-is-renamed)
- GEN-009 — [ELO page records duplicate votes on key repeat or double click](general.md#gen-009-elo-page-records-duplicate-votes-on-key-repeat-or-double-click)
- GEN-010 — [`record_vote` read-modify-write is not atomic and accepts a self-vote](general.md#gen-010-record_vote-read-modify-write-is-not-atomic-and-accepts-a-self-vote)
- GEN-011 — [Grid ignores sort, filter or collection changes while a page load is in flight](general.md#gen-011-grid-ignores-sort-filter-or-collection-changes-while-a-page-load-is-in-flight)
- GEN-012 — [`date_to` filter excludes the selected end day](general.md#gen-012-date_to-filter-excludes-the-selected-end-day)
- GEN-013 — [Viewer prev/next ignores the grid's source and filters and breaks past 1000 images](general.md#gen-013-viewer-prevnext-ignores-the-grids-source-and-filters-and-breaks-past-1000-images)

### Low

- SEC-002 — [Cross-site pages can trigger scans; CSRF safety relies on a FastAPI default](security.md#sec-002-cross-site-pages-can-trigger-scans-csrf-safety-relies-on-a-fastapi-default)
- SEC-003 — [Build and runtime images and the pnpm toolchain are unpinned](security.md#sec-003-build-and-runtime-images-and-the-pnpm-toolchain-are-unpinned)
- ORG-006 — [Remove unused exported client functions](organization.md#org-006-remove-unused-exported-client-functions)
- ORG-007 — [Remove the test-only `generate_thumbnails_parallel`](organization.md#org-007-remove-the-test-only-generate_thumbnails_parallel)
- ORG-008 — [`sourcesStore` is refreshed but never read](organization.md#org-008-sourcesstore-is-refreshed-but-never-read)
- ORG-009 — [Remove unused `ImageViewer` props and a dead `sheetEl` binding](organization.md#org-009-remove-unused-imageviewer-props-and-a-dead-sheetel-binding)
- ORG-010 — [Resolve source-preset collections in one place](organization.md#org-010-resolve-source-preset-collections-in-one-place)
- ORG-011 — [Share the WebP thumbnail encoder between image and video](organization.md#org-011-share-the-webp-thumbnail-encoder-between-image-and-video)
- ORG-012 — [Define the check pipeline once](organization.md#org-012-define-the-check-pipeline-once)
- ORG-013 — [Move the duplicated test seed helpers into conftest](organization.md#org-013-move-the-duplicated-test-seed-helpers-into-conftest)
- ORG-014 — [Deduplicate `settingsHref` in the layout and sidebar](organization.md#org-014-deduplicate-settingshref-in-the-layout-and-sidebar)
- ORG-015 — [Derive the repository root once](organization.md#org-015-derive-the-repository-root-once)
- ORG-016 — [Simplify the settings router and give it a service like the other routers](organization.md#org-016-simplify-the-settings-router-and-give-it-a-service-like-the-other-routers)
- ORG-017 — [Remove the needless indirection in filter tables and service return values](organization.md#org-017-remove-the-needless-indirection-in-filter-tables-and-service-return-values)
- ORG-018 — [Share the safe localStorage helpers](organization.md#org-018-share-the-safe-localstorage-helpers)
- ORG-019 — [Delete the empty template placeholder files](organization.md#org-019-delete-the-empty-template-placeholder-files)
- DOC-006 — [phases.md has stale "today" text and contradicts itself](docs-consistency.md#doc-006-phasesmd-has-stale-today-text-and-contradicts-itself)
- DOC-007 — [README deployment omits required THALIMAGE_IMAGES and its single mount](docs-consistency.md#doc-007-readme-deployment-omits-required-thalimage_images-and-its-single-mount)
- DOC-008 — [Minor README reference drift (check.sh, DEBUG, config.toml)](docs-consistency.md#doc-008-minor-readme-reference-drift-checksh-debug-configtoml)
- DOC-009 — [ELO docstring and in-app page misstate the pair pool](docs-consistency.md#doc-009-elo-docstring-and-in-app-page-misstate-the-pair-pool)
- TST-009 — [Cover the scan endpoint's conflict, failure and SSE edge paths](testing.md#tst-009-cover-the-scan-endpoints-conflict-failure-and-sse-edge-paths)
- PKG-003 — [Dependency list does not match imports (aiosqlite unused, starlette undeclared)](packaging.md#pkg-003-dependency-list-does-not-match-imports-aiosqlite-unused-starlette-undeclared)
- PKG-004 — [No LICENSE file; license metadata is non-SPDX "Proprietary"](packaging.md#pkg-004-no-license-file-license-metadata-is-non-spdx-proprietary)
- PKG-005 — [Frontend package.json carries a second, unguarded version literal](packaging.md#pkg-005-frontend-packagejson-carries-a-second-unguarded-version-literal)
- GEN-014 — [Viewer shows a stale image when image responses arrive out of order](general.md#gen-014-viewer-shows-a-stale-image-when-image-responses-arrive-out-of-order)
- GEN-015 — [A prefetched ELO pair from the previous collection can leak into the next](general.md#gen-015-a-prefetched-elo-pair-from-the-previous-collection-can-leak-into-the-next)
- GEN-016 — [No indexes on `images` for source or sort columns](general.md#gen-016-no-indexes-on-images-for-source-or-sort-columns)
- GEN-017 — [Preview temp file is unique per process only, so concurrent requests collide](general.md#gen-017-preview-temp-file-is-unique-per-process-only-so-concurrent-requests-collide)
- GEN-018 — [Cursor splits on the first `|`, so filenames containing `|` break name pagination](general.md#gen-018-cursor-splits-on-the-first--so-filenames-containing--break-name-pagination)

## Consolidation notes

- The docs reviewer's preview-size finding is a functional bug, so it moved to **GEN-004**.
- The floating `latest` tags reported by packaging were merged into **SEC-003**.
- The unused `aiosqlite` dependency, raised by both organization and packaging, is kept in **PKG-003**.
- Cross-references ("See also") link these overlapping findings:
  - TST-001 ↔ GEN-003
  - TST-002 ↔ GEN-006, GEN-007
  - TST-005 ↔ GEN-002
  - TST-007 ↔ GEN-010
  - PKG-001 ↔ ORG-015
  - PKG-002 ↔ SEC-003
- **Spot checks.** The orchestrator checked the high findings against the code:
  - GEN-001 (single commit after the loop), GEN-002 (no `rollback` anywhere) and GEN-005 (`st_birthtime`, `str(None)` cursor) were confirmed by reading the code.
  - GEN-006 (upsert omits `source_id`) and TST-001 / TST-002 (test gaps) were confirmed by reading the code and tests.
  - GEN-003 and GEN-004 were reproduced against a scratch database. Deleting a source after a preset vote returned 500, which extended GEN-003 to sources. `preview?size=3024` returned 422.

## What was skipped

- **Untracked files:** `.dockerignore`, `.github/` (CI workflows), `.gitignore`, `docker/.env.example` and `docker/serve.json` were not reviewed, and their absence from git is not reported. Reviewers read them only to check claims made in tracked files.
- **Historical docs:** no drift was reported in `docs/agent/reboot.org`, `docs/agent/mvp-plan.md`, `docs/agent/cr_1.md`, `docs/code-review-2026-06.md` or `docs/todos.md`. `docs/code-review-2026-07.md` is classified as unclear (see DOC-005).
- **Tests:** the backend suite ran (219 passed, 89% line + branch coverage). The frontend has no test runner. `pnpm check` (svelte-check) was not run during the review.
- **CI:** the in-progress CI workflow was not run. PKG-002's expected pnpm setup failure is inferred from the action's documented behaviour.
