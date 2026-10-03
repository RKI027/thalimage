-- Every place a file with given content exists: one row per source and
-- relative path. An image row is keyed by content, so the same file in two
-- sources (or twice in one) is one image with several locations.
--
-- images.source_id / relative_path / filename / file_size / file_modified /
-- file_created now describe that image's primary location: the one it is
-- opened from. It stays put while its file exists and moves to another
-- location when it disappears; an image with no location left is deleted.
CREATE TABLE IF NOT EXISTS image_locations (
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    relative_path TEXT    NOT NULL,
    content_hash  TEXT    NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    filename      TEXT    NOT NULL,
    file_size     INTEGER NOT NULL,
    file_modified TEXT    NOT NULL,
    file_created  TEXT,
    PRIMARY KEY (source_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_image_locations_hash ON image_locations (content_hash);

-- Until now each image knew only its last-written location.
INSERT OR IGNORE INTO image_locations
    (source_id, relative_path, content_hash, filename, file_size, file_modified, file_created)
SELECT source_id, relative_path, content_hash, filename, file_size, file_modified, file_created
FROM images
WHERE deleted = 0;
