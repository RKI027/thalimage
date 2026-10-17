-- Each still image's perceptual hash (core/perceptual_hash.py), and the
-- PERCEPTUAL_HASH_VERSION that computed it. A scan reads a file whose image
-- predates that version again, even when the file is unchanged.
--
-- Stills start at 0 (one re-read each). Videos get no perceptual hash, so
-- they are current already.
ALTER TABLE images ADD COLUMN perceptual_hash INTEGER;
ALTER TABLE images ADD COLUMN perceptual_hash_version INTEGER NOT NULL DEFAULT 0;

UPDATE images SET perceptual_hash_version = 1
WHERE format IN ('MP4', 'MOV', 'WEBM', 'AVI', 'MKV');
