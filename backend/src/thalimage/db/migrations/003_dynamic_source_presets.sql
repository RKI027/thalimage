-- Source presets are now served dynamically (WHERE source_id = X).
-- Remove the static snapshot rows that are no longer needed.
DELETE FROM collection_images
WHERE collection_id IN (
    SELECT id FROM collections WHERE type = 'source_preset'
);
