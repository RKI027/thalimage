-- Pictures changed in place (#121): at a path whose picture changed, the
-- image that lost its last copy there (old_hash) and the one that replaced
-- it (new_hash), when their perceptual hashes are within the edit
-- threshold. The pair is offered until the user merges the two (the row
-- goes) or keeps them separate (kept_separate, so it is not offered again),
-- and only while the old image has no copy left.
CREATE TABLE picture_edits (
    old_hash TEXT NOT NULL,
    new_hash TEXT NOT NULL,
    distance REAL NOT NULL,
    found_at TEXT NOT NULL DEFAULT (datetime('now')),
    kept_separate INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (old_hash, new_hash)
);

CREATE INDEX idx_picture_edits_new ON picture_edits (new_hash);
