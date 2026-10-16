-- Metadata belongs to a file version, not to an image: each file holding an
-- image (identified by the whole-file hash) keeps what was read from it,
-- and keeps it after the file is gone. content_hash is the image it shows.
CREATE TABLE file_metadata (
    file_hash         TEXT PRIMARY KEY,
    content_hash      TEXT NOT NULL REFERENCES images(content_hash),
    ai_tool           TEXT,
    prompt            TEXT,
    negative_prompt   TEXT,
    raw_params        TEXT,
    exif_data         TEXT,
    png_text          TEXT,
    extracted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    extractor_version INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_file_metadata_image ON file_metadata (content_hash);

-- The whole-file hash of the file at each location; NULL until a scan has
-- read it.
ALTER TABLE image_locations ADD COLUMN file_hash TEXT;

-- The tag names imported from any of the image's files, as a JSON list: a
-- tag removed from the image is not imported again from another file.
ALTER TABLE images ADD COLUMN file_tags TEXT;
UPDATE images SET file_tags = (
    SELECT m.file_tags FROM image_metadata m WHERE m.content_hash = images.content_hash
);

-- An image not re-keyed yet (no location at hash version 1 or above) is
-- keyed by the whole-file hash of the file its metadata was read from, so
-- that key is the file version's. Re-keyed images cannot be matched to a
-- file: their metadata is read again by the next scan, which reads every
-- location without a file hash.
INSERT INTO file_metadata
    (file_hash, content_hash, ai_tool, prompt, negative_prompt, raw_params,
     exif_data, png_text, extracted_at, extractor_version)
SELECT m.content_hash, m.content_hash, m.ai_tool, m.prompt, m.negative_prompt,
       m.raw_params, m.exif_data, m.png_text, m.extracted_at, m.extractor_version
FROM image_metadata m
WHERE NOT EXISTS (
    SELECT 1 FROM image_locations l
    WHERE l.content_hash = m.content_hash AND l.hash_version >= 1
);
UPDATE image_locations SET file_hash = content_hash WHERE hash_version = 0;

DROP TABLE image_metadata;
