-- Add collection type system for source presets

ALTER TABLE collections ADD COLUMN type TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE collections ADD COLUMN source_id INTEGER REFERENCES sources(id);

CREATE UNIQUE INDEX uq_collections_source_preset
    ON collections(source_id) WHERE type = 'source_preset';
