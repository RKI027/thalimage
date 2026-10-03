# Thalimage

Self-hosted image browser and manager for AI-generated images. Privacy-first, local-only — no cloud, no telemetry, your images stay on your machine.

## Features

- **Source folder scanning** — point at directories of images and videos; Thalimage indexes them, extracts metadata and generates thumbnails at scan time, re-reading only files that changed
- **AI metadata extraction** — reads generation parameters (prompt, seed, sampler, model, etc.) from PNG text chunks, EXIF, and Stable Diffusion formats via sd-parsers
- **Content-addressed images** — identified by SHA-256 hash, so a file kept in several folders or sources is one image, listed under each
- **Gallery** — virtual-scrolling grid for libraries of any size, with sort, date / aspect-ratio / media-type filters, and a thumbnail size slider
- **Collections** — one live preset per source folder, plus your own named collections, each with its own sort
- **Viewer** — keyboard and swipe navigation through the grid you came from, and a metadata panel with file info, AI parameters and raw PNG text
- **Slideshow** — timed, sequential or shuffled (optionally weighted by ELO score), fullscreen, with overlay controls
- **ELO ranking** — vote between two images at a time; scores are kept per collection
- **Tags, NSFW and archiving** — global tags; a tag named "nsfw" hides an image unless NSFW display is on, as does an NSFW collection; archiving sets images aside without losing their data
- **Video** — MP4, MOV, WebM and AVI with ffmpeg-made thumbnails and in-browser playback
- **Fast over a slow link** — 400px WebP thumbnails from the scan, display-sized WebP previews generated on demand, and immutable caching
- **Mobile** — drawer navigation, compact headers, swipe gestures, and an installable web-app manifest
- **In-app documentation** — at `/docs`, for behaviour the UI does not show (ranking, delivery, scanning)

## Deployment

Thalimage runs as a single container. The image is published to GitHub
Container Registry by CI, so a deployment is a pull rather than a build.

```
docker pull ghcr.io/rki027/thalimage:latest
```

### Security

**There is no authentication of any kind.** Every endpoint is open:
anything that can reach the port with an accepted `Host` header can add
and delete sources, trigger scans, archive images, edit tags and delete
collections, and `GET /api/v1/images/{hash}/file` streams originals
straight off the filesystem. Network-level access control is the only
control there is. Do not expose it to the internet.

What the app does guard against is a web page on another site, open in a
browser on the same network, making the server write on its behalf:
POST, PUT, PATCH and DELETE requests that a browser marks as cross-site,
or whose `Origin` is not one the app answers to, get a 403. Requests
without those headers (scripts, curl) are unaffected.

The stack below answers that by never publishing a port at all.

### The stack

`docker/docker-compose.yml` is a ready-to-use sample — copy it into
wherever your stack definitions live, or paste it into Portainer. It
runs two services:

- **`tailscale`** — a `tailscale/tailscale` sidecar that joins the
  tailnet as its own node and runs `tailscale serve` (config in
  `docker/serve.json`), terminating TLS with a Tailscale-issued
  certificate. Tailscale does **not** need to be installed on the Docker
  host.
- **`thalimage`** — the app, with `network_mode: service:tailscale`, so
  it lives inside the sidecar's network namespace and has no network
  identity of its own. Nothing is published to the host, so the app is
  unreachable from the LAN.

The app ends up at `https://<TS_HOSTNAME>.<your-tailnet>.ts.net`.

Before deploying, in the Tailscale admin console:

- enable **MagicDNS** and **HTTPS certificates** for the tailnet, or
  `serve` cannot obtain a certificate;
- define the tag named in `TS_TAG` and grant your account permission to
  apply it. Tagged nodes never expire; an untagged one drops off the
  tailnet at node-key expiry and has to be re-authenticated by hand;
- to narrow access to particular devices, write a Tailscale ACL grant
  against that tag. Without one, every device on the tailnet can reach
  it.

`TS_AUTHKEY` (an auth key, or an OAuth client secret) is needed only for
the node's first authentication — after that the node identity lives in
the state directory on the bind mount.

Copy `docker/.env.example` to `.env` and fill it in, then:

```bash
cd docker
docker compose up -d
```

### Storage

Everything the stack owns lives under one host directory
(`THALIMAGE_DATA`, `/srv/thalimage` by default), split in two siblings:

```
app/                           mounted at /data in the app container
  thalimage.db  (+ -wal, -shm) SQLite, WAL mode
  cache/thumbs/                400px WebP thumbnails
  cache/previews/{size}/       long-edge-capped WebP, generated on demand
tailscale/                     Tailscale node state, sidecar only
```

They are siblings on purpose: the app's entrypoint hands `/data` to the
app user on every start, and the Tailscale node keys must stay root-owned
and out of the app container.

This is what to back up. Because the database is in WAL mode, copying
`thalimage.db` alone is not enough — either stop the container first, or
use `sqlite3 /srv/thalimage/app/thalimage.db ".backup /tmp/snapshot.db"`,
which takes a consistent snapshot of a live database. It should be a
real local filesystem, not a network share.

**Image folders** are mounted read-only; nothing is ever written back
into them. `THALIMAGE_IMAGES` is required: it names the host folder the
compose file mounts at `/images`. Register `/images`, or folders under
it, as sources in Settings. Further trees go on extra lines, as the
commented example in the compose file shows:

```yaml
volumes:
  - ${THALIMAGE_IMAGES:?...}:/images:ro
  - /photos/comfy:/images/comfy:ro
```

Source paths are stored absolutely in the database (per-file paths are
stored relative to them), so a mount point has to stay stable across
redeploys — moving a library later means updating `sources.path` by
hand.

**File permissions**: set `PUID`/`PGID` to the owner of the image files
on the host (`id -u` / `id -g`) so the container can read them.

### Updating

```bash
docker compose pull && docker compose up -d
```

The Tailscale sidecar is pinned (`TS_VERSION`), so `pull` does not
upgrade it; bump the variable to do that.

**Upgrading from the single-directory layout** (database at the top of
`THALIMAGE_DATA`, before `app/` existed): stop the stack, then move the
app's files down one level before starting it again:

```bash
cd /srv/thalimage && mkdir app && mv thalimage.db* cache app/
chown -R root:root tailscale
```

The app reports the commit it was built from at `/api/v1/version`, and
the frontend bundle carries the same stamp, so a half-updated deployment
is visible rather than mysterious.

### Configuration

All settings can be set via environment variables with the `THALIMAGE_`
prefix. A TOML file at `~/.thalimage/config.toml` also works; the
lookup is always relative to the home directory and does not follow
`THALIMAGE_DATA_DIR`. In the container the entrypoint sets `HOME=/data`,
so the file goes at `/data/.thalimage/config.toml`, which is
`$THALIMAGE_DATA/app/.thalimage/config.toml` on the host. Environment
variables take precedence over it.

| Variable | Default | Description |
|---|---|---|
| `THALIMAGE_DATA_DIR` | `~/.thalimage` | Database and cache directory |
| `THALIMAGE_DB_PATH` | `{data_dir}/thalimage.db` | SQLite database path |
| `THALIMAGE_THUMB_DIR` | `{data_dir}/cache/thumbs` | Thumbnail storage path |
| `THALIMAGE_PREVIEW_DIR` | `{data_dir}/cache/previews` | Preview storage path |
| `THALIMAGE_HOST` | `127.0.0.1` | Server bind address (the Docker image sets `0.0.0.0`) |
| `THALIMAGE_PORT` | `8000` | Server port |
| `THALIMAGE_FRONTEND_DIR` | `frontend/build` in a checkout | Built SPA to serve (the Docker image sets it) |
| `THALIMAGE_DEBUG` | `false` | Auto-reload on code changes (development only) |
| `THALIMAGE_CONCURRENT_SCANS` | `true` | Allow source scans to run concurrently |
| `THALIMAGE_CORS_ORIGINS` | `[]` | Allowed CORS origins (JSON list); empty since the frontend is served same-origin |
| `THALIMAGE_ALLOWED_HOSTS` | `[]` | Additional permitted `Host` header values (JSON list) |

`THALIMAGE_ALLOWED_HOSTS` is a DNS-rebinding defense, not
authentication. `localhost` and `127.0.0.1` are always accepted; an
empty list therefore means loopback only, and any request arriving under
another name gets a 400. Add the hostnames clients actually use — e.g.
`["thalimage.tail1234.ts.net"]`, or the wildcard `["*.ts.net"]`. Set it
to `["*"]` to disable the check.

The app runs as a **single process**: scan progress and the
one-scan-per-source guard live in its memory, so do not add
`uvicorn --workers`.

## Development

Backend is Python (managed with [uv](https://docs.astral.sh/uv/)); frontend is SvelteKit (managed with [pnpm](https://pnpm.io/)). Common tasks are wrapped in the `Makefile`.

```bash
# Backend
make install      # uv sync
make dev          # run the API on http://127.0.0.1:8000
make test         # pytest
make cov          # pytest with line + branch coverage
make lint         # ruff (lint-fix applies fixes)
make typecheck    # mypy
make lock-check   # uv.lock matches pyproject.toml

# Frontend
make fe-install   # pnpm install
make fe-dev       # vite dev server on http://localhost:5173
make fe-build     # build the static bundle
make fe-preview   # serve the built bundle on http://127.0.0.1:4173
make fe-check     # svelte-check
make fe-test      # vitest

# Everything
make check        # same as ./check.sh: what CI runs
```

In development the frontend runs separately and proxies `/api` to the backend on port 8000 (see `frontend/vite.config.ts`), so run `make dev` alongside either `make fe-dev` (hot reload) or `make fe-build && make fe-preview` (production-like bundle). In production the backend serves the built bundle directly, so a single process answers both the UI and the API.

`./check.sh` (or `make check`) is the gate CI runs: lock check, lint, typecheck and tests for the backend, then svelte-check and vitest for the frontend when `frontend/node_modules` exists. Run it before pushing.

`thalimage-dev.el` and `.dir-locals.el` wire the dev servers and the frontend build into Emacs.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI, SQLite (WAL mode)
- **Frontend**: SvelteKit (SPA mode, adapter-static)
- **Metadata**: sd-parsers, piexif, Pillow
- **Thumbnails**: Pillow (WebP)

## Documentation

- In-app user documentation at `/docs`, written in `backend/src/thalimage/docs/*.md` and shipped with the package
- `CLAUDE.md` — architecture, code layout and conventions for contributors
- `docs/roadmap.md` — current roadmap and backlog
- `docs/review/` — full-review runs, each with a `RESOLUTION.md` ledger
- `docs/archive/` — earlier plans, fix logs and reviews, kept for history (indexed in its `README.md`)
- `LICENSE` — proprietary; all rights reserved
