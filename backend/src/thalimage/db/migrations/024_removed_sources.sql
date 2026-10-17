-- A source removed with its images' data kept (#122). The row stays because
-- those images still reference it; it is hidden everywhere, and adding its
-- folder again brings it back.
ALTER TABLE sources ADD COLUMN removed_at TEXT;
