-- The files beside a source's media files that are not media themselves,
-- as its latest scan found them: sidecars, and orphans that no media file
-- in their folder names. The digest of the content tells when one changed;
-- the size and modification time tell when it must be read again.
CREATE TABLE sidecars (
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    relative_path TEXT    NOT NULL,
    digest        TEXT    NOT NULL,
    file_size     INTEGER NOT NULL,
    file_modified TEXT    NOT NULL,
    orphan        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source_id, relative_path)
);
