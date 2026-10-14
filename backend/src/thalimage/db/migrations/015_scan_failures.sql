-- The files (and folders) a source's latest scan could not index, with
-- why. Each scan replaces its source's rows, so this lists what is wrong
-- now, not a history. A folder that could not be listed is stored with a
-- trailing separator.
CREATE TABLE IF NOT EXISTS scan_failures (
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    relative_path TEXT    NOT NULL,
    reason        TEXT    NOT NULL,
    PRIMARY KEY (source_id, relative_path)
);
