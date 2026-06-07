ALTER TABLE transfers
DROP COLUMN IF EXISTS from_class;

ALTER TABLE transfers
DROP COLUMN IF EXISTS to_class;

ALTER TABLE transfers
DROP COLUMN IF EXISTS classified_at;