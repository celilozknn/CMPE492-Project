-- drop classification-related indexes first
DROP INDEX IF EXISTS idx_event_class;
DROP INDEX IF EXISTS idx_entity_classes_gin;

-- drop old columns 
ALTER TABLE transfers
DROP COLUMN IF EXISTS entity_classes;

ALTER TABLE transfers
DROP COLUMN IF EXISTS event_class;

-- add new columns
ALTER TABLE transfers
ADD COLUMN from_entity_class TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN to_entity_class   TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN from_event_class   VARCHAR(32),
ADD COLUMN to_event_class     VARCHAR(32);

-- entity indexes
CREATE INDEX idx_from_entity_class_gin
ON transfers USING GIN (from_entity_class);

CREATE INDEX idx_to_entity_class_gin
ON transfers USING GIN (to_entity_class);

-- event indexes
CREATE INDEX idx_from_event_class
ON transfers (from_event_class, network);

CREATE INDEX idx_to_event_class
ON transfers (to_event_class, network);