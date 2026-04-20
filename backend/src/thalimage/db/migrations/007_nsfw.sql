-- NSFW flag on images (auto-maintained by triggers) and collections (manual)
ALTER TABLE images      ADD COLUMN nsfw INTEGER NOT NULL DEFAULT 0;
ALTER TABLE collections ADD COLUMN nsfw INTEGER NOT NULL DEFAULT 0;

-- User-level settings stored as key-value pairs
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Trigger: auto-set images.nsfw = 1 when a NSFW tag is added
CREATE TRIGGER set_image_nsfw_on_tag_add
AFTER INSERT ON image_tags
WHEN (SELECT nsfw FROM tags WHERE id = NEW.tag_id) = 1
BEGIN
    UPDATE images SET nsfw = 1 WHERE content_hash = NEW.image_hash;
END;

-- Trigger: recompute images.nsfw when a tag is removed
-- Clears the flag only if no remaining NSFW tags exist
CREATE TRIGGER clear_image_nsfw_on_tag_remove
AFTER DELETE ON image_tags
WHEN (SELECT nsfw FROM tags WHERE id = OLD.tag_id) = 1
BEGIN
    UPDATE images SET nsfw = (
        SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
        FROM image_tags it JOIN tags t ON t.id = it.tag_id
        WHERE it.image_hash = OLD.image_hash AND t.nsfw = 1
    ) WHERE content_hash = OLD.image_hash;
END;
