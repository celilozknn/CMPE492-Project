-- 1. Add entity classification column (multi-label)
ALTER TABLE transfers
ADD COLUMN IF NOT EXISTS entity_classes JSONB DEFAULT '[]'::jsonb;

-- 2. Add event classification column (single-label)
ALTER TABLE transfers
ADD COLUMN IF NOT EXISTS event_class VARCHAR(32);

-- 3. Index for fast filtering by event type
CREATE INDEX IF NOT EXISTS idx_event_class
ON transfers (event_class, network);

-- 4. GIN index for JSONB queries like:
--    entity_classes @> '["CEX"]'
CREATE INDEX IF NOT EXISTS idx_entity_classes_gin
ON transfers
USING GIN (entity_classes);

