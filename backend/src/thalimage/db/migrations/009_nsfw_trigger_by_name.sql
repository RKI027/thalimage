-- Replace tag-driven NSFW triggers: flag is now set by the tag named "nsfw"
-- (case-insensitive) rather than the tag's nsfw column.
DROP TRIGGER IF EXISTS set_image_nsfw_on_tag_add;
DROP TRIGGER IF EXISTS clear_image_nsfw_on_tag_remove;

CREATE TRIGGER set_image_nsfw_on_tag_add
AFTER INSERT ON image_tags
WHEN (SELECT LOWER(name) FROM tags WHERE id = NEW.tag_id) = 'nsfw'
BEGIN
    UPDATE images SET nsfw = 1 WHERE content_hash = NEW.image_hash;
END;

CREATE TRIGGER clear_image_nsfw_on_tag_remove
AFTER DELETE ON image_tags
WHEN (SELECT LOWER(name) FROM tags WHERE id = OLD.tag_id) = 'nsfw'
BEGIN
    UPDATE images SET nsfw = (
        SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
        FROM image_tags it JOIN tags t ON t.id = it.tag_id
        WHERE it.image_hash = OLD.image_hash AND LOWER(t.name) = 'nsfw'
    ) WHERE content_hash = OLD.image_hash;
END;

-- Backfill: set nsfw=1 on images that have a tag named "nsfw",
-- clear nsfw on images whose flag was set by the old tags.nsfw column only.
UPDATE images SET nsfw = (
    SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
    FROM image_tags it JOIN tags t ON t.id = it.tag_id
    WHERE it.image_hash = images.content_hash AND LOWER(t.name) = 'nsfw'
);
