-- Since 009 an image is NSFW when it carries a tag *named* "nsfw"; the
-- tags.nsfw column has been read by nothing since then.
ALTER TABLE tags DROP COLUMN nsfw;
