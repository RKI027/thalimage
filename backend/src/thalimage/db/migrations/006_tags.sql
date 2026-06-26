-- Global tagging system: tags live on images, not per-collection
CREATE TABLE tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    nsfw       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE image_tags (
    image_hash TEXT    NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_by TEXT,  -- reserved for Phase 8 multi-user; nullable for now
    created_at TEXT   NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (image_hash, tag_id)
);

CREATE INDEX idx_image_tags_hash ON image_tags(image_hash);
CREATE INDEX idx_image_tags_tag  ON image_tags(tag_id);
