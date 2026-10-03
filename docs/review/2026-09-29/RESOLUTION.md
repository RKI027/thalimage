# Resolution of the 2026-09-29 review

Every finding from [README.md](README.md) and how it was resolved. Each
remediation PR updates its own rows, so this file is complete when the
series is.

Status: **fixed** (with the PR), **superseded** (resolved by the named
finding's fix), **won't fix** (with the reason), or **open**.

| ID | Sev | Finding | Status | Notes |
|---|---|---|---|---|
| [GEN-001](general.md#gen-001-scan-holds-one-write-transaction-for-its-whole-run-locking-out-api-writes) | high | Scan holds one write transaction for its whole run, locking out API writes | open | |
| [GEN-002](general.md#gen-002-failed-writes-are-never-rolled-back-on-the-shared-request-connection) | high | Failed writes are never rolled back on the shared request connection | fixed | transactions PR: one connection per request; `open_db` rolls back whatever a request leaves open, then closes. Unknown hashes in a collection add are filtered instead of failing the FK; preset collections reject adds with 400 |
| [GEN-003](general.md#gen-003-deleting-a-collection-or-source-with-elo-data-fails-with-500) | high | Deleting a collection or source with ELO data fails with 500 | open | |
| [GEN-004](general.md#gen-004-previews-requested-above-2560px-get-422-so-the-viewer-breaks-on-hi-dpi-screens) | high | Previews requested above 2560px get 422, so the viewer breaks on hi-DPI screens | open | |
| [GEN-005](general.md#gen-005-created-sort-stops-after-one-page-when-file_created-is-null-always-on-linuxdocker) | high | "Created" sort stops after one page when `file_created` is NULL | fixed | deploy PR: Created sorts on `COALESCE(file_created, file_modified)` and the cursor carries that key. Pulled forward because the existing pagination test fails on Linux CI |
| [GEN-006](general.md#gen-006-same-content-in-two-sources-resolves-to-a-non-existent-path) | high | Same content in two sources resolves to a non-existent path | open | |
| [GEN-007](general.md#gen-007-an-unreachable-source-root-marks-every-image-in-that-source-deleted) | medium | An unreachable source root marks every image in that source deleted | open | |
| [GEN-008](general.md#gen-008-nsfw-flag-is-not-recomputed-when-the-nsfw-tag-is-deleted-or-a-tag-is-renamed) | medium | NSFW flag is not recomputed when the "nsfw" tag is deleted or a tag is renamed | open | |
| [GEN-009](general.md#gen-009-elo-page-records-duplicate-votes-on-key-repeat-or-double-click) | medium | ELO page records duplicate votes on key repeat or double click | open | |
| [GEN-010](general.md#gen-010-record_vote-read-modify-write-is-not-atomic-and-accepts-a-self-vote) | medium | `record_vote` read-modify-write is not atomic and accepts a self-vote | open | |
| [GEN-011](general.md#gen-011-grid-ignores-sort-filter-or-collection-changes-while-a-page-load-is-in-flight) | medium | Grid ignores sort, filter or collection changes while a page load is in flight | open | |
| [GEN-012](general.md#gen-012-date_to-filter-excludes-the-selected-end-day) | medium | `date_to` filter excludes the selected end day | open | |
| [GEN-013](general.md#gen-013-viewer-prevnext-ignores-the-grids-source-and-filters-and-breaks-past-1000-images) | medium | Viewer prev/next ignores the grid's source and filters and breaks past 1000 images | open | |
| [GEN-014](general.md#gen-014-viewer-shows-a-stale-image-when-image-responses-arrive-out-of-order) | low | Viewer shows a stale image when image responses arrive out of order | open | |
| [GEN-015](general.md#gen-015-a-prefetched-elo-pair-from-the-previous-collection-can-leak-into-the-next) | low | A prefetched ELO pair from the previous collection can leak into the next | open | |
| [GEN-016](general.md#gen-016-no-indexes-on-images-for-source-or-sort-columns) | low | No indexes on `images` for source or sort columns | open | |
| [GEN-017](general.md#gen-017-preview-temp-file-is-unique-per-process-only-so-concurrent-requests-collide) | low | Preview temp file is unique per process only, so concurrent requests collide | open | |
| [GEN-018](general.md#gen-018-cursor-splits-on-the-first--so-filenames-containing--break-name-pagination) | low | Cursor splits on the first `\|`, so filenames containing `\|` break name pagination | open | |
| [TST-001](testing.md#tst-001-test-that-deleting-a-source-cascades-correctly-and-loses-nothing-else) | high | Test that deleting a source cascades correctly and loses nothing else | open | |
| [TST-002](testing.md#tst-002-cover-the-scans-changed-file-duplicate-content-video-and-error-paths) | high | Cover the scan's changed-file, duplicate-content, video and error paths | open | |
| [TST-003](testing.md#tst-003-test-ai-parameter-and-exif-extraction-on-real-metadata) | medium | Test AI-parameter and EXIF extraction on real metadata | open | |
| [TST-004](testing.md#tst-004-remove-the-vacuous-early-return-in-the-video-preview-test) | medium | Remove the vacuous early return in the video preview test | open | |
| [TST-005](testing.md#tst-005-add-api-tests-for-tags-and-settings-two-error-paths-return-500) | medium | Add API tests for tags and settings; two error paths return 500 | open | |
| [TST-006](testing.md#tst-006-test-migrations-against-populated-databases-not-only-empty-ones) | medium | Test migrations against populated databases, not only empty ones | open | |
| [TST-007](testing.md#tst-007-test-elo-vote-validation-and-source-preset-pairing-at-the-api) | medium | Test ELO vote validation and source-preset pairing at the API | open | |
| [TST-008](testing.md#tst-008-frontend-logic-has-no-automated-tests) | medium | Frontend logic has no automated tests | open | |
| [TST-009](testing.md#tst-009-cover-the-scan-endpoints-conflict-failure-and-sse-edge-paths) | low | Cover the scan endpoint's conflict, failure and SSE edge paths | open | |
| [SEC-001](security.md#sec-001-entrypoint-chowns-the-tailscale-node-state-to-the-app-user) | medium | Entrypoint chowns the Tailscale node state to the app user | fixed | deploy PR: app data at `$THALIMAGE_DATA/app`, sibling of `tailscale/`; README has the upgrade steps |
| [SEC-002](security.md#sec-002-cross-site-pages-can-trigger-scans-csrf-safety-relies-on-a-fastapi-default) | low | Cross-site pages can trigger scans; CSRF safety relies on a FastAPI default | open | |
| [SEC-003](security.md#sec-003-build-and-runtime-images-and-the-pnpm-toolchain-are-unpinned) | low | Build and runtime images and the pnpm toolchain are unpinned | fixed | deploy PR: uv and the Tailscale sidecar pinned by version (`TS_VERSION`). Base images stay on `node:24-slim` / `python:3.11-slim` on purpose: without Dependabot a digest pin would freeze out security updates |
| [PKG-001](packaging.md#pkg-001-built-wheel-ships-without-the-spa-runtime-needs-a-source-tree-install) | medium | Built wheel ships without the SPA; runtime needs a source-tree install | open | |
| [PKG-002](packaging.md#pkg-002-pnpm-version-is-not-pinned-no-packagemanager-field) | medium | pnpm version is not pinned (no `packageManager` field) | fixed | deploy PR: `packageManager: pnpm@10.28.0`; CI's pnpm/action-setup reads it |
| [PKG-003](packaging.md#pkg-003-dependency-list-does-not-match-imports-aiosqlite-unused-starlette-undeclared) | low | Dependency list does not match imports (aiosqlite unused, starlette undeclared) | open | |
| [PKG-004](packaging.md#pkg-004-no-license-file-license-metadata-is-non-spdx-proprietary) | low | No LICENSE file; license metadata is non-SPDX "Proprietary" | open | |
| [PKG-005](packaging.md#pkg-005-frontend-packagejson-carries-a-second-unguarded-version-literal) | low | Frontend package.json carries a second, unguarded version literal | open | |
| [ORG-001](organization.md#org-001-define-the-video-extension-list-once-per-side) | medium | Define the video-extension list once per side | open | |
| [ORG-002](organization.md#org-002-pull-the-shared-gallery-logic-out-of-the-two-grid-pages) | medium | Pull the shared gallery logic out of the two grid pages | open | |
| [ORG-003](organization.md#org-003-merge-the-duplicated-images-upsert-in-the-scan-service) | medium | Merge the duplicated `images` upsert in the scan service | open | |
| [ORG-004](organization.md#org-004-remove-the-dead-tagsnsfw-flag-from-the-service-api-and-client) | medium | Remove the dead `tags.nsfw` flag from the service, API and client | open | |
| [ORG-005](organization.md#org-005-share-the-imagesummary-column-list-and-row-conversion) | medium | Share the ImageSummary column list and row conversion | open | |
| [ORG-006](organization.md#org-006-remove-unused-exported-client-functions) | low | Remove unused exported client functions | open | |
| [ORG-007](organization.md#org-007-remove-the-test-only-generate_thumbnails_parallel) | low | Remove the test-only `generate_thumbnails_parallel` | open | |
| [ORG-008](organization.md#org-008-sourcesstore-is-refreshed-but-never-read) | low | `sourcesStore` is refreshed but never read | open | |
| [ORG-009](organization.md#org-009-remove-unused-imageviewer-props-and-a-dead-sheetel-binding) | low | Remove unused `ImageViewer` props and a dead `sheetEl` binding | open | |
| [ORG-010](organization.md#org-010-resolve-source-preset-collections-in-one-place) | low | Resolve source-preset collections in one place | open | |
| [ORG-011](organization.md#org-011-share-the-webp-thumbnail-encoder-between-image-and-video) | low | Share the WebP thumbnail encoder between image and video | open | |
| [ORG-012](organization.md#org-012-define-the-check-pipeline-once) | low | Define the check pipeline once | open | |
| [ORG-013](organization.md#org-013-move-the-duplicated-test-seed-helpers-into-conftest) | low | Move the duplicated test seed helpers into conftest | open | |
| [ORG-014](organization.md#org-014-deduplicate-settingshref-in-the-layout-and-sidebar) | low | Deduplicate `settingsHref` in the layout and sidebar | open | |
| [ORG-015](organization.md#org-015-derive-the-repository-root-once) | low | Derive the repository root once | open | |
| [ORG-016](organization.md#org-016-simplify-the-settings-router-and-give-it-a-service-like-the-other-routers) | low | Simplify the settings router and give it a service like the other routers | open | |
| [ORG-017](organization.md#org-017-remove-the-needless-indirection-in-filter-tables-and-service-return-values) | low | Remove the needless indirection in filter tables and service return values | open | |
| [ORG-018](organization.md#org-018-share-the-safe-localstorage-helpers) | low | Share the safe localStorage helpers | open | |
| [ORG-019](organization.md#org-019-delete-the-empty-template-placeholder-files) | low | Delete the empty template placeholder files | open | |
| [DOC-001](docs-consistency.md#doc-001-scanning-page-says-videos-are-catalogued-without-ffmpeg) | medium | Scanning page says videos are catalogued without ffmpeg | open | |
| [DOC-002](docs-consistency.md#doc-002-scanning-page-misdescribes-the-skip-rule-and-preset-sync) | medium | Scanning page misdescribes the skip rule and preset sync | open | |
| [DOC-003](docs-consistency.md#doc-003-readme-feature-list-is-stale-and-says-thumbnails-are-on-demand) | medium | README feature list is stale and says thumbnails are on-demand | open | |
| [DOC-004](docs-consistency.md#doc-004-claudemd-backend-layout-lists-a-nonexistent-module-and-omits-several) | medium | CLAUDE.md backend layout lists a nonexistent module and omits several | open | |
| [DOC-005](docs-consistency.md#doc-005-docs-tree-mixes-the-current-roadmap-with-archives-one-review-is-unindexed) | medium | Docs tree mixes the current roadmap with archives; one review is unindexed | open | |
| [DOC-006](docs-consistency.md#doc-006-phasesmd-has-stale-today-text-and-contradicts-itself) | low | phases.md has stale "today" text and contradicts itself | open | |
| [DOC-007](docs-consistency.md#doc-007-readme-deployment-omits-required-thalimage_images-and-its-single-mount) | low | README deployment omits required THALIMAGE_IMAGES and its single mount | fixed | deploy PR: README documents the required `THALIMAGE_IMAGES` and its single `/images` mount |
| [DOC-008](docs-consistency.md#doc-008-minor-readme-reference-drift-checksh-debug-configtoml) | low | Minor README reference drift (check.sh, DEBUG, config.toml) | open | |
| [DOC-009](docs-consistency.md#doc-009-elo-docstring-and-in-app-page-misstate-the-pair-pool) | low | ELO docstring and in-app page misstate the pair pool | open | |
