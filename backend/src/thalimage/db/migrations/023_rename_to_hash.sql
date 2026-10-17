-- A writable source may have each scan rename its files to their picture
-- hash (#14). Off for every source.
ALTER TABLE sources ADD COLUMN rename_to_hash INTEGER NOT NULL DEFAULT 0;
