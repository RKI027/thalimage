-- Enforce that source_preset collections never have collection_images rows.
-- These collections are always served dynamically (WHERE source_id = X).
CREATE TRIGGER prevent_source_preset_collection_images
BEFORE INSERT ON collection_images
BEGIN
    SELECT RAISE(ABORT, 'source_preset collections do not store image rows')
    WHERE (SELECT type FROM collections WHERE id = NEW.collection_id) = 'source_preset';
END;
