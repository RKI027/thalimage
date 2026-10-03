# Security review: thalimage

Scope: repository root (tracked files) · Commit: 031252b (dirty working tree) · Date: 2026-09-29

Three findings: one medium and two low. The rest of the checked surface holds up:

- **Paths and parameters:** content-hash and doc-slug path parameters are regex-constrained, and the SPA fallback checks `is_relative_to`.
- **SQL:** every SQL string built with an f-string uses whitelisted columns or `?` placeholders.
- **Subprocess calls:** ffmpeg and ffprobe run from argv lists, with no `shell=True`.
- **Hosts and CORS:** `TrustedHostMiddleware` is present, and CORS is empty by default.
- **Frontend rendering:** `{@html}` renders only the markdown docs packaged with the app, and image metadata is rendered as text.
- **Prompt injection:** no text addressed to AI agents turned up in the repo.

The lack of authentication is documented and intentional (README "Security"), so it is not reported as such.

## SEC-001: Entrypoint chowns the Tailscale node state to the app user

- **Severity:** medium
- **Confidence:** high
- **Location:** `docker/docker-compose.yml:36`, `docker/docker-compose.yml:64`, `docker/entrypoint.sh:17-18`
- **Labels:** security, docker

The sidecar keeps its node state at `${THALIMAGE_DATA}/tailscale` (compose:36). The app container mounts the parent `${THALIMAGE_DATA}` at `/data` (compose:64), so that state also appears inside the app at `/data/tailscale`. On every start, `entrypoint.sh:18` runs `chown -R "$PUID:$PGID" /data` as root. As a result, `tailscaled.state`, which holds the node's private keys, becomes owned by the unprivileged app UID (UID 1000 on the host by default). README:78-85 describes `tailscale/` as living under the app's data directory but says nothing about this ownership change.

**Why it matters:** The app parses untrusted media with Pillow and ffmpeg. Any code execution in the app process, or any host account with UID `PUID`, can read the node key and impersonate the node on the tailnet. The chown also undoes Tailscale's root-only ownership on every restart.

**Suggested fix:** Keep the Tailscale state outside the tree the app mounts, for example with sibling host directories: `${THALIMAGE_DATA}/app` → `/data` and `${THALIMAGE_DATA}/tailscale` → `/var/lib/tailscale`. Alternatively, limit the chown to the app's own paths (`thalimage.db*` and `cache/`). Update the storage layout in the README to match.

**Done when:** After a container restart, the files under the Tailscale state directory are still owned by root, and the directory is not visible inside the `thalimage` container.

## SEC-002: Cross-site pages can trigger scans; CSRF safety relies on a FastAPI default

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/api/sources.py:119-162`, `backend/src/thalimage/app.py:49-62`, `backend/pyproject.toml:15`
- **Labels:** security, backend

`POST /api/v1/sources/{id}/scan` takes no body, so it is a CORS "simple request". Any website opened in a browser on the tailnet can send it without a preflight. The browser sends the real `Host` header, so `TrustedHostMiddleware` accepts the request. Source ids are small sequential integers. The attacker still needs to know the node's hostname, which lowers the likelihood.

Endpoints that take a JSON body are protected today only because the locked FastAPI version (0.135.3, `uv.lock:184-185`) defaults to `strict_content_type=True`. Without that default, a body sent with no Content-Type would be parsed as JSON. `pyproject.toml` allows `fastapi>=0.115.0`, which does not guarantee that default. PATCH and DELETE requests always trigger a preflight, so they are not affected.

**Why it matters:** A malicious page can make the server repeatedly scan and hash whole source trees. If an older FastAPI were resolved, the same page could also create sources, collections, tags and votes.

**Suggested fix:** Add a small middleware that rejects unsafe methods (POST/PUT/PATCH/DELETE) when `Sec-Fetch-Site` is `cross-site`, or when `Origin` is present and not an allowed host. Raise the FastAPI floor to the first release with `strict_content_type`, or set that option explicitly.

**Done when:** A test sending `POST /api/v1/sources/{id}/scan` with `Origin: https://evil.example` (or `Sec-Fetch-Site: cross-site`) gets 403, and same-origin requests still succeed.

## SEC-003: Build and runtime images and the pnpm toolchain are unpinned

- **Severity:** low
- **Confidence:** high
- **Location:** `docker/Dockerfile:2`, `docker/Dockerfile:9`, `docker/Dockerfile:18`, `docker/Dockerfile:30`, `docker/docker-compose.yml:22`, `docker/docker-compose.yml:46`
- **Labels:** security, docker, supply-chain

Nothing that builds or runs the stack is pinned:

- **uv binary:** copied from `ghcr.io/astral-sh/uv:latest` (Dockerfile:30).
- **Base images:** tag-only `node:24-slim` and `python:3.11-slim` (Dockerfile:2, 18).
- **pnpm:** `corepack enable pnpm` (line 9) installs whatever version is current.
- **Tailscale sidecar:** `tailscale/tailscale:latest` (compose:22), the container that holds the tailnet credentials. The README's `docker compose pull` update step (README.md:116) upgrades it silently.

The lockfiles are frozen, but the tools that read them are not. The lock uses `revision = 3` (uv.lock:2), and a future uv could reject or re-interpret `--frozen` installs.

**Why it matters:** An upstream tag change or compromise silently changes the binaries that build the image and run next to the tailnet credentials. Builds are also not reproducible, and a breaking upstream release can land with no change in the repo.

**Suggested fix:** Pin `uv` and `tailscale` to a version tag, or better, a digest. Pin the base images by digest. The pnpm pin is covered by PKG-002.

**Done when:** No `:latest` or unversioned tool image remains in `docker/`, except through an overridable variable.

See also: PKG-002.
