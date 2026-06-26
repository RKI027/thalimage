-- Ensure settings table exists; may be absent on databases where migration 007
-- ran but did not complete the CREATE TABLE statement.
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
