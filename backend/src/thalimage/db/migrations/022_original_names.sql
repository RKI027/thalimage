-- The name each file version was first scanned under, kept when the file is
-- renamed (by Thalimage or by hand). Existing versions get the current name
-- of a file holding them: the first one known.
ALTER TABLE file_metadata ADD COLUMN original_name TEXT;
UPDATE file_metadata SET original_name = (
    SELECT l.filename FROM image_locations l
    WHERE l.file_hash = file_metadata.file_hash
    ORDER BY l.source_id, l.relative_path
    LIMIT 1
);
