# Thalimage

Self-hosted image browser and manager for AI-generated images. Privacy-first, local-only — no cloud, no telemetry, your images stay on your machine.

## Features

- **Source folder scanning** — point at directories containing images; Thalimage indexes them, extracts metadata, and generates thumbnails
- **AI metadata extraction** — reads generation parameters (prompt, seed, sampler, model, etc.) from PNG text chunks, EXIF, and Stable Diffusion formats via sd-parsers
- **Virtual scrolling gallery** — handles thousands of images without DOM bloat
- **Source filtering** — browse all images or filter by source folder
- **Collections** — organize images into named collections
- **Single image view** — full-size display with keyboard navigation (arrow keys, Escape) and a metadata panel showing file info, AI parameters, and raw PNG text
- **Content-addressed storage** — images identified by SHA-256 hash, so duplicates across sources are detected automatically
- **WebP thumbnails** — fast grid loading with on-demand thumbnail generation

## Deployment

### Docker (recommended)

```bash
cd docker

# Edit docker-compose.yml to set your image paths and PUID/PGID
vim docker-compose.yml

docker compose up -d
```

The compose file mounts image folders read-only at `/images`. The app stores its database and thumbnail cache in a named volume at `/data`.

**Multiple source directories**: mount each one separately and add them as sources in the Settings UI:

```yaml
volumes:
  - /photos/ai:/images/ai:ro
  - /photos/comfy:/images/comfy:ro
```

Then in Settings, add `/images/ai` and `/images/comfy` as sources.

**File permissions**: set `PUID` and `PGID` to match the owner of your image files on the host so the container can read them:

```bash
# Find your UID/GID
id -u  # PUID
id -g  # PGID
```

### Configuration

All settings can be set via environment variables with the `THALIMAGE_` prefix, or in a TOML file at `~/.thalimage/config.toml`.

| Variable | Default | Description |
|---|---|---|
| `THALIMAGE_DATA_DIR` | `~/.thalimage` | Database and cache directory |
| `THALIMAGE_DB_PATH` | `{data_dir}/thalimage.db` | SQLite database path |
| `THALIMAGE_THUMB_DIR` | `{data_dir}/cache/thumbs` | Thumbnail storage path |
| `THALIMAGE_HOST` | `0.0.0.0` | Server bind address |
| `THALIMAGE_PORT` | `8000` | Server port |
| `THALIMAGE_DEBUG` | `false` | Debug mode |

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI, SQLite (WAL mode)
- **Frontend**: SvelteKit (SPA mode, adapter-static)
- **Metadata**: sd-parsers, piexif, Pillow
- **Thumbnails**: Pillow (WebP)
