-- The tag names last imported from each file's own metadata (keywords,
-- star rating), as a JSON list; NULL until the file is read for them. A
-- re-read adds only names missing from this list, so a tag the user
-- removed is not brought back.
--
-- Extractor version 2 reads keywords and ratings, so still images are
-- read again once. Videos carry none, so they are current already.
ALTER TABLE image_metadata ADD COLUMN file_tags TEXT;

UPDATE image_metadata SET extractor_version = 2
WHERE content_hash IN (
    SELECT content_hash FROM images WHERE format IN ('MP4', 'MOV', 'WEBM', 'AVI')
);
