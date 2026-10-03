# Packaging review: thalimage

Scope: repository root (tracked files) · Commit: e28c431 (dirty working tree) · Date: 2026-09-29

The core packaging is sound:
- `uv lock --check` passes.
- The version is 0.5.0 everywhere: `pyproject.toml`, `uv.lock`, `package.json` and the `v0.5.0` tag.
- A wheel built into a scratch directory contains all `migrations/*.sql` and `docs/*.md` files.
- `.dockerignore` keeps the in-app docs in the build context.
- The Docker HEALTHCHECK uses host 127.0.0.1, which the app always allows (`app.py:53`).

There are five findings. The two medium ones: the app serves its UI only from a source-tree or editable install, and the pnpm version is not pinned. The floating `latest` image tags are reported under SEC-003.

## PKG-001: Built wheel ships without the SPA; runtime needs a source-tree install

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/app.py:19`, `backend/src/thalimage/app.py:75-76`, `backend/src/thalimage/version.py:17`, `docker/Dockerfile:32-44`
- **Labels:** packaging, docker

`FRONTEND_DIR` is resolved as four parents above `app.py` plus `frontend/build` (`app.py:19`). `REPO_ROOT` is computed the same way (`version.py:17`). A wheel built with `uv build` contains no frontend files. Once installed normally into site-packages, the path points outside the package, and `if frontend_dir.is_dir()` (`app.py:76`) quietly skips the UI, so only the API is served.

The Docker image works only because `uv sync` installs the project in editable mode by default (`Dockerfile:44`). The Dockerfile comment (lines 32-35) explains the directory layout, but not that it depends on an editable install. Using `--no-editable`, a common image optimisation, or `pip install` of the wheel would produce an image with no UI and no error.

**Why it matters:** The published image can lose its UI without any warning, and the wheel is not a self-contained artifact.

**Suggested fix:** Make the SPA location configurable, e.g. a `THALIMAGE_FRONTEND_DIR` setting set in the Dockerfile. Alternatively, pass `--editable` explicitly and extend the Dockerfile comment to state that requirement. Either way, log a warning at startup when the frontend directory is missing.

**Done when:** The image still serves `/` when built with `uv sync --no-editable` (or the Dockerfile states and enforces the editable install), and a missing SPA directory produces a log line at startup.

See also: ORG-015.

## PKG-002: pnpm version is not pinned (no `packageManager` field)

- **Severity:** medium
- **Confidence:** medium
- **Location:** `frontend/package.json:1-31`, `frontend/pnpm-workspace.yaml:3`, `docker/Dockerfile:9-12`
- **Labels:** packaging, frontend, ci

`frontend/package.json` has only `"engines": {"pnpm": ">=10"}` and no `packageManager` field. `docker/Dockerfile:9` runs `corepack enable pnpm`, so `pnpm install --frozen-lockfile` uses whichever pnpm version the corepack in `node:24-slim` defaults to at build time.

The in-progress CI workflow (`.github/workflows/ci.yml:19`, untracked) uses `pnpm/action-setup@v4` without a `version:` input. That action reads the version from `packageManager` in a `package.json` at the repo root, and there is none. The reviewer expects the step to fail with "No pnpm version is specified", but did not run it. `engineStrict: true` (`pnpm-workspace.yaml:3`) turns any version mismatch into a hard failure.

**Why it matters:** Image builds are not reproducible, and CI probably cannot set up pnpm.

**Suggested fix:** Add `"packageManager": "pnpm@10.x.y"` to `frontend/package.json`, using the version that wrote `lockfileVersion: '9.0'`. In CI, set `package_json_file: frontend/package.json` on `pnpm/action-setup`.

**Done when:** `corepack pnpm --version` in the build stage prints the pinned version, and the CI pnpm setup step passes.

See also: SEC-003.

## PKG-003: Dependency list does not match imports (aiosqlite unused, starlette undeclared)

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/pyproject.toml:23`, `backend/pyproject.toml:33`, `backend/src/thalimage/app.py:11`
- **Labels:** packaging, dependencies

- **aiosqlite:** a runtime dependency (`pyproject.toml:23`) that nothing imports. All DB access uses the synchronous `sqlite3` (`db/engine.py`). `docs/code-review-2026-07.md:88-89` already flagged it.
- **starlette:** `app.py:11` imports `starlette.middleware.trustedhost` directly, but `starlette` is not declared. It is only installed as a dependency of `fastapi`.
- **pytest-cov:** a dev dependency (`pyproject.toml:33`) that no `check.sh`, `Makefile` or `[tool.pytest.ini_options]` target uses. It may be run by hand.

**Why it matters:** The unused dependency enlarges the image and the supply-chain surface. A direct import that relies on a transitive dependency can break if fastapi changes its pins.

**Suggested fix:** Remove `aiosqlite`. Declare `starlette`, or import the middleware through `fastapi.middleware.trustedhost`. Either wire `--cov` into a target or drop `pytest-cov`. Then run `uv lock`.

**Done when:** Every runtime dependency is imported somewhere under `src/`, every third-party top-level import under `src/` is declared, and `uv lock --check` passes.

## PKG-004: No LICENSE file; license metadata is non-SPDX "Proprietary"

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/pyproject.toml:13`, `README.md:1-3`
- **Labels:** packaging, metadata, license

There is no LICENSE or COPYING file in the repo. `pyproject.toml:13` declares `license = {text = "Proprietary"}`, which is not an SPDX expression. Yet CI publishes the image to ghcr.io and the README describes it as self-hostable. `docs/code-review-2026-07.md:86-87` already asked for the license to be confirmed, and it is still unresolved. The metadata also has no `readme` or `[project.urls]`. The reviewer could not confirm whether the GHCR package is public.

**Why it matters:** Anyone who pulls the image has no terms of use, and license tooling cannot read the metadata.

**Suggested fix:** Decide on the license. Add a matching LICENSE file, and set `license = "LicenseRef-Proprietary"` (or an SPDX id) together with `license-files`. Optionally add `readme` and `urls`.

**Done when:** A LICENSE file exists at the repo root, and the `License-Expression` / `License` field in the wheel's METADATA matches it.

## PKG-005: Frontend package.json carries a second, unguarded version literal

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/package.json:4`, `backend/tests/test_api_version.py:22`
- **Labels:** packaging, versioning

The release commit e28c431 says `pyproject.toml` is the only place the version is stated, and adds a test so that no second literal can come back (`test_api_version.py:22`). But that same commit also bumped `"version": "0.5.0"` in `frontend/package.json:4`. Nothing reads that value, and the test does not cover it.

**Why it matters:** A release that forgets this file leaves a stale frontend version that nothing catches, which is exactly the drift the release commit set out to remove.

**Suggested fix:** Drop `version` from the private `frontend/package.json`, or extend the version test to assert that it equals the `pyproject.toml` version.

**Done when:** `frontend/package.json` has no version field, or a test fails when it differs from `backend/pyproject.toml`.
