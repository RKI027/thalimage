# Resolution of the 2026-10-26 review

Every finding from [README.md](README.md) and how it was resolved. Each
remediation PR updates its own rows, so this file is complete when the
series is.

Status: **fixed** (with the PR), **superseded** (resolved by the named
finding's fix), **won't fix** (with the reason), or **open**.

| ID | Sev | Finding | Status | Notes |
|---|---|---|---|---|
| [SEC-001](security.md#sec-001-unvalidated-hashes-in-post-imagesdelete-unlink-arbitrary-mp4-files) | medium | Unvalidated hashes in POST /images/delete unlink arbitrary *.mp4 files | fixed | [#181](https://github.com/RKI027/thalimage/pull/181): body hashes use the `ContentHash` pattern; a test covers a file outside `video_dir` |
| [SEC-002](security.md#sec-002-settings-close-link-renders-returnto-unchecked-javascript-xss) | medium | Settings "Close" link renders returnTo unchecked (javascript: XSS) | fixed | [#181](https://github.com/RKI027/thalimage/pull/181): `returnToHref` accepts only on-origin single-slash paths; unit-tested |
| [SEC-003](security.md#sec-003-ci-downloads-and-runs-unpinned-unverified-ffmpeg-builds) | medium | CI downloads and runs unpinned, unverified ffmpeg builds | fixed | [#192](https://github.com/RKI027/thalimage/pull/192): the job uses the pinned runner's apt ffmpeg, `permissions: contents: read`, and `persist-credentials: false`; the nightly download is gone |
| [SEC-004](security.md#sec-004-no-frame-ancestors--x-frame-options-clickjacking-bypasses-the-write-guard) | low | No frame-ancestors / X-Frame-Options: clickjacking bypasses the write guard | fixed | [#194](https://github.com/RKI027/thalimage/pull/194): `SecurityHeaders` sets `frame-ancestors 'none'`, `X-Frame-Options: DENY` and `nosniff` on every response, including a refused write |
| [SEC-005](security.md#sec-005-write-guards-fallback-trusts-any-loopback-port-and-every-wildcard-matched-host) | low | Write guard's fallback trusts any loopback port and every wildcard-matched host | fixed | [#194](https://github.com/RKI027/thalimage/pull/194): a write is accepted only from the request's own netloc or a CORS origin; the dev proxy rewrites Origin; compose and `.env.example` pin the exact MagicDNS name |
| [SEC-006](security.md#sec-006-dir-localsel-asks-to-permanently-trust-an-eval-that-loads-mutable-code) | low | .dir-locals.el asks to permanently trust an eval that loads mutable code | open |  |
| [SEC-007](security.md#sec-007-docker-base-images-are-pinned-by-mutable-tag-unlike-the-sha-pinned-actions) | low | Docker base images are pinned by mutable tag, unlike the SHA-pinned actions | open |  |
| [ORG-001](organization.md#org-001-break-the-service-import-cycles-instead-of-hiding-them-in-local-imports) | medium | Break the service import cycles instead of hiding them in local imports | fixed | [#196](https://github.com/RKI027/thalimage/pull/196): `iso_timestamp`/`unchanged_since_scan` moved to `file_changes`; a new `scoring` module breaks the ELO cycle; the local imports are hoisted and the service graph is acyclic |
| [ORG-002](organization.md#org-002-share-the-changed-since-scan-guard-between-file-deletion-and-renaming) | medium | Share the "changed since scan" guard between file deletion and renaming | fixed | [#196](https://github.com/RKI027/thalimage/pull/196): `location_row` and `still_as_scanned` in `file_changes`; deletion, renaming and moving share them |
| [ORG-003](organization.md#org-003-encode-collection-membership-once) | medium | Encode collection membership once | open |  |
| [ORG-004](organization.md#org-004-split-the-1025-line-viewer-page) | medium | Split the 1025-line viewer page | open |  |
| [ORG-005](organization.md#org-005-use-one-sha-256-file-hasher) | low | Use one SHA-256 file hasher | open |  |
| [ORG-006](organization.md#org-006-derive-the-stored-video-format-in-one-place) | low | Derive the stored video format in one place | open |  |
| [ORG-007](organization.md#org-007-merge-the-two-ffprobe-wrappers) | low | Merge the two ffprobe wrappers | open |  |
| [ORG-008](organization.md#org-008-drop-vestigial-columns-sourcesenabled-and-imagesthumb_generated) | low | Drop vestigial columns `sources.enabled` and `images.thumb_generated` | open |  |
| [ORG-009](organization.md#org-009-remove-the-test-only-list_images-wrapper) | low | Remove the test-only `list_images` wrapper | open |  |
| [ORG-010](organization.md#org-010-remove-dead-code-in-apits-scanmanager-and-_page) | low | Remove dead code in `api.ts`, `ScanManager` and `_page` | open |  |
| [ORG-011](organization.md#org-011-use-copypath-and-one-failure-formatter-everywhere) | low | Use `copyPath` and one failure formatter everywhere | open |  |
| [ORG-012](organization.md#org-012-move-the-shared-grid-page-glue-into-gallery) | low | Move the shared grid-page glue into `Gallery` | open |  |
| [ORG-013](organization.md#org-013-share-the-settings-keyvalue-encoding) | low | Share the `settings` key/value encoding | open |  |
| [ORG-014](organization.md#org-014-name-the-duplicated-constants-once) | low | Name the duplicated constants once | open |  |
| [ORG-015](organization.md#org-015-trim-imagefileinfo-to-what-the-scan-uses) | low | Trim `ImageFileInfo` to what the scan uses | open |  |
| [ORG-016](organization.md#org-016-reuse-_record_sql-in-image_standings) | low | Reuse `_record_sql` in `image_standings` | open |  |
| [ORG-017](organization.md#org-017-raise-the-pydantic-settings-floor-and-drop-the-toml-import-fallback) | low | Raise the pydantic-settings floor and drop the TOML import fallback | open |  |
| [ORG-018](organization.md#org-018-drop-unused-parameters-and-single-use-indirection) | low | Drop unused parameters and single-use indirection | open |  |
| [DOC-001](docs-consistency.md#doc-001-state-in-readme-security-that-the-open-api-can-delete-files-on-disk) | medium | State in README Security that the open API can delete files on disk | open |  |
| [DOC-002](docs-consistency.md#doc-002-document-the-indexed-image-formats-heic-is-named-but-never-indexed) | medium | Document the indexed image formats; HEIC is named but never indexed | open |  |
| [DOC-003](docs-consistency.md#doc-003-separate-the-unbuilt-image-analysis-plan-from-current-design-decisions) | medium | Separate the unbuilt "Image analysis" plan from current design decisions | open |  |
| [DOC-004](docs-consistency.md#doc-004-bring-the-claudemd-code-layout-up-to-date) | low | Bring the CLAUDE.md code layout up to date | open |  |
| [DOC-005](docs-consistency.md#doc-005-document-the-label-page-linked-from-every-collection) | low | Document the Label page linked from every collection | open |  |
| [DOC-006](docs-consistency.md#doc-006-update-the-readme-feature-list) | low | Update the README feature list | open |  |
| [DOC-007](docs-consistency.md#doc-007-list-development-prerequisites-and-the-api-explorer-in-readme) | low | List development prerequisites and the API explorer in README | open |  |
| [DOC-008](docs-consistency.md#doc-008-correct-the-designmd-wording-on-all-images-and-source-presets) | low | Correct the design.md wording on "All Images" and source presets | open |  |
| [DOC-009](docs-consistency.md#doc-009-list-cachevideos-and-near-duplicatesjson-in-the-storage-descriptions) | low | List cache/videos and near-duplicates.json in the storage descriptions | open |  |
| [DOC-010](docs-consistency.md#doc-010-say-the-deploy-secrets-live-in-the-test-deploy-environment) | low | Say the deploy secrets live in the test-deploy environment | open |  |
| [DOC-011](docs-consistency.md#doc-011-fix-the-ciyml-comment-on-what-checksh-runs) | low | Fix the ci.yml comment on what check.sh runs | open |  |
| [DOC-012](docs-consistency.md#doc-012-fix-the-thalimage-devel-commentary-for-the-frontend-command) | low | Fix the `thalimage-dev.el` commentary for the frontend command | open |  |
| [TST-001](testing.md#tst-001-make-the-csrf-allowed-hosts-test-reach-the-allowed-hosts-rule) | medium | Make the CSRF allowed-hosts test reach the allowed-hosts rule | superseded | [#194](https://github.com/RKI027/thalimage/pull/194) (SEC-005): the allowed-hosts fallback was the hole and is removed; `csrf.py` is at 100% lines and branches with tests for the new same-origin rule |
| [TST-002](testing.md#tst-002-test-the-viewer-pages-navigation-and-destructive-action-logic) | medium | Test the viewer page's navigation and destructive-action logic | open |  |
| [TST-003](testing.md#tst-003-run-the-backend-tests-on-the-deployed-python-and-ffmpeg) | medium | Run the backend tests on the deployed Python and ffmpeg | fixed | [#189](https://github.com/RKI027/thalimage/pull/189) + [#192](https://github.com/RKI027/thalimage/pull/192): CI and the image both use 3.14, and the tests use a packaged ffmpeg rather than a nightly. Stated limit: Ubuntu 24.04 ships ffmpeg 6.1, Debian trixie 7.1 |
| [TST-004](testing.md#tst-004-cover-rename-and-delete-failures-after-the-pre-checks-pass) | medium | Cover rename and delete failures after the pre-checks pass | fixed | [#196](https://github.com/RKI027/thalimage/pull/196): tests for a failed rename/removal, a hash name appearing before the rename, a failing sidecar rename and a file gone since the scan; `file_renaming.py` at 100% lines and branches |
| [TST-005](testing.md#tst-005-exercise-the-real-request-dependencies-at-least-once) | low | Exercise the real request dependencies at least once | open |  |
| [TST-006](testing.md#tst-006-measure-coverage-in-ci-and-for-the-frontend) | low | Measure coverage in CI, and for the frontend | open |  |
| [TST-007](testing.md#tst-007-close-the-sqlite-connections-the-tests-open) | low | Close the SQLite connections the tests open | open |  |
| [TST-008](testing.md#tst-008-type-check-the-test-suite) | low | Type-check the test suite | open |  |
| [PKG-001](packaging.md#pkg-001-stop-cis-make-install-rewriting-uvlock-before-the-lock-check) | high | Stop CI's `make install` rewriting uv.lock before the lock check | fixed | [#181](https://github.com/RKI027/thalimage/pull/181): the Makefile exports `UV_LOCKED=1`, and CI checks `git diff --exit-code -- backend/uv.lock` after `make install` |
| [PKG-002](packaging.md#pkg-002-declare-the-certifi-exclude-newer-exemption-that-uvlock-depends-on) | medium | Declare the certifi exclude-newer exemption that uv.lock depends on | fixed | [#181](https://github.com/RKI027/thalimage/pull/181): certifi 2026.10.19 is past the 7-day gate; re-locked without the exemption |
| [PKG-003](packaging.md#pkg-003-run-ci-on-the-python-version-the-image-ships) | medium | Run CI on the Python version the image ships | fixed | [#189](https://github.com/RKI027/thalimage/pull/189): image, CI and `uv` all use 3.14 (`requires-python`, mypy, ruff and `.python-version` follow); the lock is re-resolved with uv 0.12.22 |
| [PKG-004](packaging.md#pkg-004-pin-the-uv-version-for-developers-not-just-ci-and-docker) | low | Pin the uv version for developers, not just CI and Docker | open |  |
| [PKG-005](packaging.md#pkg-005-extend-dependabot-beyond-github-actions) | low | Extend Dependabot beyond GitHub Actions | open |  |
| [PKG-006](packaging.md#pkg-006-give-the-frontend-the-same-release-age-cooldown-as-the-backend) | low | Give the frontend the same release-age cooldown as the backend | open |  |
| [PKG-007](packaging.md#pkg-007-include-the-real-license-in-the-sdist-not-a-dangling-symlink) | low | Include the real LICENSE in the sdist, not a dangling symlink | open |  |
| [PKG-008](packaging.md#pkg-008-declare-starlette-which-the-backend-imports-directly) | low | Declare starlette, which the backend imports directly | open |  |
| [GEN-001](general.md#gen-001-perceptual-hash-pads-at-full-resolution-memory-grows-with-maxwh²) | high | Perceptual hash pads at full resolution, memory grows with max(w,h)² | fixed | [#190](https://github.com/RKI027/thalimage/pull/190): the picture is shrunk to a 1024-px long edge before padding (an 800x12000 picture peaks at ~40 MB, was ~780 MB); `PERCEPTUAL_HASH_VERSION` is 4 |
| [GEN-002](general.md#gen-002-removing-a-source-while-it-is-scanned-brings-its-images-and-preset-back) | medium | Removing a source while it is scanned brings its images and preset back | fixed | [#193](https://github.com/RKI027/thalimage/pull/193): `DELETE /sources/{id}` refuses with 409 while that source scans; Settings disables Remove for a scan it started |
| [GEN-003](general.md#gen-003-labelling-page-treats-imported-star-ratings-as-labels-and-deletes-them) | medium | Labelling page treats imported star ratings as labels and deletes them | fixed | [#191](https://github.com/RKI027/thalimage/pull/191): the labels endpoint takes exact labels and returns only those; `toggleLabel` and `missingNamespaces` ignore tags outside the vocabulary's values |
| [GEN-004](general.md#gen-004-raising-the-perceptual-hash-version-re-reads-every-video) | medium | Raising the perceptual-hash version re-reads every video | fixed | [#190](https://github.com/RKI027/thalimage/pull/190): videos are exempt from the perceptual and animation version tests, and a `_SkipFile` keeps the location; covers the post-review `ANIMATION_VERSION` copy too |
| [GEN-005](general.md#gen-005-source-summary-lists-a-folder-once-per-duplicate-copy) | medium | Source summary lists a folder once per duplicate copy | fixed | [#195](https://github.com/RKI027/thalimage/pull/195): the summary reads the scan's `sidecars` rows once and matches them in memory, listing no folders; 1000 copies in a 5000-file folder returns in under a second |
| [GEN-006](general.md#gen-006-thumbnails-and-previews-ignore-exif-orientation) | low | Thumbnails and previews ignore EXIF orientation | open |  |
| [GEN-007](general.md#gen-007-re-keying-in-a-scan-drops-pending-possible-edit-questions) | low | Re-keying in a scan drops pending possible-edit questions | open |  |
| [GEN-008](general.md#gen-008-derived-files-of-merged-or-purged-images-stay-in-the-cache-forever) | low | Derived files of merged or purged images stay in the cache forever | open |  |
| [GEN-009](general.md#gen-009-picture-hash-raises-indexerror-on-jpegs-cut-between-segments) | low | Picture hash raises IndexError on JPEGs cut between segments | fixed | [#190](https://github.com/RKI027/thalimage/pull/190): `IndexError` falls back to the content hash; the test cuts both JPEG fixtures after every segment |
| [GEN-010](general.md#gen-010-label-page-says-no-images-while-loading-and-desyncs-after-a-failed-toggle) | low | Label page says "no images" while loading, and desyncs after a failed toggle | open |  |
