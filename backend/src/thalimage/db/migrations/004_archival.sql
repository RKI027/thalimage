-- User-controlled soft-delete, separate from scan-managed deleted flag.
ALTER TABLE images ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0;
