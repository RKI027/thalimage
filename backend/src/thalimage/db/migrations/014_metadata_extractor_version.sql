-- Which version of the metadata extractor filled each row. A scan re-reads
-- a file whose row predates core.metadata.EXTRACTOR_VERSION, even when the
-- file is unchanged, so extraction fixes reach existing libraries.
--
-- Version 1 is the first that stored AI parameters at all: until then the
-- extractor read attribute names sd-parsers does not have, and every
-- prompt, negative prompt, tool and raw-parameter field stayed empty.
-- Still images therefore start at 0 (one re-read each); videos carry no
-- AI metadata, so they are current already.
ALTER TABLE image_metadata ADD COLUMN extractor_version INTEGER NOT NULL DEFAULT 0;

UPDATE image_metadata SET extractor_version = 1
WHERE content_hash IN (
    SELECT content_hash FROM images WHERE format IN ('MP4', 'MOV', 'WEBM', 'AVI')
);
