-- Source folders the app watches
CREATE TABLE sources (
    id          INTEGER PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    label       TEXT,
    recursive   BOOLEAN NOT NULL DEFAULT 1,
    enabled     BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_scan   TEXT
);

-- Core image table - lean for grid queries
CREATE TABLE images (
    content_hash    TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    relative_path   TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    aspect_ratio    REAL NOT NULL,
    format          TEXT NOT NULL,
    file_modified   TEXT NOT NULL,
    file_created    TEXT,
    thumb_generated BOOLEAN NOT NULL DEFAULT 0,
    deleted         BOOLEAN NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Metadata separate to keep images table fast
CREATE TABLE image_metadata (
    content_hash    TEXT PRIMARY KEY REFERENCES images(content_hash),
    ai_tool         TEXT,
    prompt          TEXT,
    negative_prompt TEXT,
    raw_params      TEXT,
    exif_data       TEXT,
    png_text        TEXT,
    extracted_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Virtual hierarchy (not on disk)
CREATE TABLE collections (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES collections(id),
    sort_by     TEXT NOT NULL DEFAULT 'name',
    sort_dir    TEXT NOT NULL DEFAULT 'asc',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE collection_images (
    collection_id   INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    content_hash    TEXT NOT NULL REFERENCES images(content_hash),
    position        INTEGER,
    added_at        TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (collection_id, content_hash)
);

-- ELO ranking
CREATE TABLE votes (
    id              INTEGER PRIMARY KEY,
    collection_id   INTEGER REFERENCES collections(id),
    winner_hash     TEXT NOT NULL REFERENCES images(content_hash),
    loser_hash      TEXT NOT NULL REFERENCES images(content_hash),
    voted_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE elo_scores (
    content_hash    TEXT NOT NULL REFERENCES images(content_hash),
    collection_id   INTEGER NOT NULL REFERENCES collections(id),
    score           REAL NOT NULL DEFAULT 1500.0,
    matches         INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (content_hash, collection_id)
);

CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
