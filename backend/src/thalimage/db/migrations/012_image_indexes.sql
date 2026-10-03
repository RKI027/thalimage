-- Grid pages filter on live images and order by the sort key plus the
-- hash tie-breaker; without an index every page scanned and sorted the
-- whole table. Partial indexes match the queries' `deleted = 0 AND
-- archived = 0`, and the Created index uses the exact expression the
-- query sorts on (image_service.SORT_COLUMNS).
CREATE INDEX IF NOT EXISTS idx_images_live_filename
    ON images (filename, content_hash) WHERE deleted = 0 AND archived = 0;
CREATE INDEX IF NOT EXISTS idx_images_live_modified
    ON images (file_modified, content_hash) WHERE deleted = 0 AND archived = 0;
CREATE INDEX IF NOT EXISTS idx_images_live_created
    ON images (COALESCE(file_created, file_modified), content_hash)
    WHERE deleted = 0 AND archived = 0;
CREATE INDEX IF NOT EXISTS idx_images_live_size
    ON images (file_size, content_hash) WHERE deleted = 0 AND archived = 0;
CREATE INDEX IF NOT EXISTS idx_images_live_aspect
    ON images (aspect_ratio, content_hash) WHERE deleted = 0 AND archived = 0;

-- Scans look up a source's images; source deletion and the source filter too.
CREATE INDEX IF NOT EXISTS idx_images_source ON images (source_id);
