-- 009's triggers watch image_tags only. Deleting the "nsfw" tag itself
-- removes its image_tags rows by ON DELETE CASCADE after the tag row is
-- gone, so their name lookup finds nothing and the flag stays set; a
-- rename to or from "nsfw" changes no image_tags row at all. These two
-- triggers recompute the flag for the tag's images in both cases.

DROP TRIGGER IF EXISTS recompute_image_nsfw_on_nsfw_tag_delete;
CREATE TRIGGER recompute_image_nsfw_on_nsfw_tag_delete
BEFORE DELETE ON tags
WHEN LOWER(OLD.name) = 'nsfw'
BEGIN
    UPDATE images SET nsfw = EXISTS (
        SELECT 1 FROM image_tags it JOIN tags t ON t.id = it.tag_id
        WHERE it.image_hash = images.content_hash
          AND LOWER(t.name) = 'nsfw' AND t.id != OLD.id
    )
    WHERE content_hash IN (SELECT image_hash FROM image_tags WHERE tag_id = OLD.id);
END;

DROP TRIGGER IF EXISTS recompute_image_nsfw_on_tag_rename;
CREATE TRIGGER recompute_image_nsfw_on_tag_rename
AFTER UPDATE OF name ON tags
WHEN (LOWER(OLD.name) = 'nsfw') != (LOWER(NEW.name) = 'nsfw')
BEGIN
    UPDATE images SET nsfw = EXISTS (
        SELECT 1 FROM image_tags it JOIN tags t ON t.id = it.tag_id
        WHERE it.image_hash = images.content_hash AND LOWER(t.name) = 'nsfw'
    )
    WHERE content_hash IN (SELECT image_hash FROM image_tags WHERE tag_id = NEW.id);
END;

-- Unstick images flagged by an "nsfw" tag deleted before these triggers.
UPDATE images SET nsfw = EXISTS (
    SELECT 1 FROM image_tags it JOIN tags t ON t.id = it.tag_id
    WHERE it.image_hash = images.content_hash AND LOWER(t.name) = 'nsfw'
);
