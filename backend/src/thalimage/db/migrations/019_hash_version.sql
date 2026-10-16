-- Which hash keyed the image at each location (core/picture_hash.py
-- HASH_VERSION): 0 for the whole-file hash used until now. A scan reads a
-- location with an older version again, even when its file is unchanged,
-- and re-keys its image.
ALTER TABLE image_locations ADD COLUMN hash_version INTEGER NOT NULL DEFAULT 0;
