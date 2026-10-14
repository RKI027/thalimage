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

Thalimage runs as a single container. CI publishes the image to GitHub
Container Registry for each release tag (`v*`), as `:latest` and as the
version, so a deployment is a pull rather than a build. A manual run of
the workflow on any branch publishes `:dev` instead, for testing a branch
on a deployment set to `THALIMAGE_TAG=dev`:

```
gh workflow run docker.yml --ref <branch>
```

Redeploy with "re-pull image" (or `docker compose pull`) to pick it up.

The stack below runs in Portainer on a homelab host, with the images and
the data directory on an NFS share and the database on the host's local
disk.

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
  `serve.json`), terminating TLS with a Tailscale-issued
  certificate. Tailscale does **not** need to be installed on the Docker
  host.
- **`thalimage`** — the app, with `network_mode: service:tailscale`, so
  it lives inside the sidecar's network namespace and has no network
  identity of its own. Nothing is published to the host, so the app is
  unreachable from the LAN.

The app ends up at `https://<TS_HOSTNAME>.<your-tailnet>.ts.net`. Open
it with the `https://` scheme: only port 443 is served, and a bare name
may make the browser try port 80 and fail to connect.

Before deploying, in the Tailscale admin console:

- enable **MagicDNS** and **HTTPS certificates** for the tailnet, or
  `serve` cannot obtain a certificate;
- define the tag named in `TS_TAG` in `tagOwners`, **with an owner**
  allowed to apply it. Without an owner the first join can succeed and a
  later restart fail with `requested tags [...] are invalid or not
  permitted`. Tagged nodes never expire; an untagged one drops off the
  tailnet at node-key expiry and has to be re-authenticated by hand;
- to narrow access to particular devices, write a Tailscale ACL grant
  against that tag. Without one, every device on the tailnet can reach
  it.

`TS_AUTHKEY` (an auth key, or an OAuth client secret) is needed only for
the node's first authentication — after that the node identity lives in
the state directory on the bind mount, and `TS_AUTH_ONCE` keeps the
sidecar from logging in again on later starts. Generate the key under
Settings → Keys → Generate auth key (not "Add app", which makes an App
Connector): not reusable, not ephemeral, tagged with `TS_TAG`, and
pre-approved if device approval is on.

Copy `docker/serve.json` to `$THALIMAGE_DATA/serve.json`. It is mounted
from there rather than from beside the compose file: a stack pasted into
Portainer has no `./serve.json`, and Docker would mount an empty
directory in its place (the sidecar then logs `read /config/serve.json:
is a directory`). Copy `docker/.env.example` to `.env` and fill it in, then:

```bash
cd docker
docker compose up -d
```

### Storage

The stack keeps its state in two host directories:

```
THALIMAGE_DB_DIR/              mounted at /db; local disk only
  thalimage.db  (+ -wal, -shm) SQLite, WAL mode
THALIMAGE_DATA/                /srv/thalimage by default; a network share is fine
  app/                         mounted at /data in the app container
    cache/thumbs/              400px WebP thumbnails
    cache/previews/{size}/     long-edge-capped WebP, generated on demand
    db_backups/                the daily database backups
  tailscale/                   Tailscale node state, sidecar only
  serve.json                   tailscale serve config
```

**The database must be on the Docker host's local disk.** SQLite's WAL
mode does not work over a network filesystem: with the database on NFS,
requests stalled for 10–35 s (measured in the container: a 35.7 s worst
case on NFS against 22 ms on local disk). `THALIMAGE_DB_DIR` is required
for that reason. The caches and backups are plain files and can live on
a share.

`app/` and `tailscale/` are siblings on purpose: the app's entrypoint
hands `/data` (and the database folder) to the app user on every start,
and the Tailscale node keys must stay root-owned and out of the app
container.

**Backups.** The app copies the database into `db_backups/` once a day,
with SQLite's backup API, so the copy is consistent while the app runs.
Settings → Database backup sets the time of day (06:00 by default, read
in the `TZ` zone), how many copies to keep (7), and has "Back up now".
A run missed while the app was down is not made up. With the data
directory on a NAS, this keeps a recent copy of the local-disk database
there. To restore one: stop the stack, copy a
`db_backups/thalimage-*.db` over `$THALIMAGE_DB_DIR/thalimage.db`,
delete any `thalimage.db-wal` and `thalimage.db-shm` beside it, and start
the stack again.

**Moving an existing database in** (e.g. from a desktop install):

1. Checkpoint the WAL before copying (`sqlite3 thalimage.db "PRAGMA
   wal_checkpoint(TRUNCATE)"`), or copy with `.backup`.
2. Put it in `THALIMAGE_DB_DIR` and copy `cache/` into `app/` along with
   it.
3. Rewrite `sources.path` to the container paths (`/images/...`). Image
   paths are stored relative to their source, so only the sources change.
4. Make sure the copied image files kept their modification times. If
   they did not, the next scan reprocesses every file and records the
   copy dates; restore the mtimes before scanning.

**Image folders** are mounted read-only by default. Thalimage changes
files only in a source marked writable in Settings, and marking one
writable is refused while its folder does not accept writes. To allow
it, drop `:ro` from that folder's mount and make sure `PUID`/`PGID` may
write there. `THALIMAGE_IMAGES` is required: it names the host folder the
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
| `THALIMAGE_BACKUP_DIR` | `{data_dir}/db_backups` | Where the daily database backups go |
| `THALIMAGE_HOST` | `127.0.0.1` | Server bind address (the Docker image sets `0.0.0.0`) |
| `THALIMAGE_PORT` | `8000` | Server port |
| `THALIMAGE_FRONTEND_DIR` | `frontend/build` in a checkout | Built SPA to serve (the Docker image sets it) |
| `THALIMAGE_DEBUG` | `false` | Auto-reload on code changes (development only) |
| `THALIMAGE_CONCURRENT_SCANS` | `true` | Allow source scans to run concurrently |
| `THALIMAGE_CORS_ORIGINS` | `[]` | Allowed CORS origins (JSON list); empty since the frontend is served same-origin |
| `THALIMAGE_ALLOWED_HOSTS` | `[]` | Additional permitted `Host` header values (JSON list) |

`THALIMAGE_ALLOWED_HOSTS` must be a JSON list
(`["thalimage.tail1234.ts.net"]`); anything else stops startup with
`error parsing value for field "allowed_hosts"`. It is a DNS-rebinding
defense, not authentication. `localhost` and `127.0.0.1` are always accepted; an
empty list therefore means loopback only, and any request arriving under
another name gets a 400. Add the hostnames clients actually use — e.g.
`["thalimage.tail1234.ts.net"]`, or the wildcard `["*.ts.net"]`. Set it
to `["*"]` to disable the check. An entry with a scheme
(`https://...`) or a short name the browser does not use gives "Invalid
host header"; pin the exact MagicDNS name once it is known.

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
