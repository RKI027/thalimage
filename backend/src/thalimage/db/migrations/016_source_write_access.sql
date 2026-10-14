-- Thalimage changes files (deletes, renames, moves) only in a source
-- marked writable; every source starts read-only.
ALTER TABLE sources ADD COLUMN writable INTEGER NOT NULL DEFAULT 0;

-- Every change Thalimage makes on disk, kept when the source is removed
-- (so no foreign key). `path` is relative to the source; `target` is the
-- new path of a rename or move.
CREATE TABLE IF NOT EXISTS file_changes (
    id        INTEGER PRIMARY KEY,
    at        TEXT    NOT NULL DEFAULT (datetime('now')),
    source_id INTEGER NOT NULL,
    operation TEXT    NOT NULL,
    path      TEXT    NOT NULL,
    target    TEXT,
    outcome   TEXT    NOT NULL CHECK (outcome IN ('done', 'failed')),
    error     TEXT
);
