-- ============================================================================
-- Migration 012: Add entity table with entity_type column
-- Created: 2025-12-31
-- Purpose: Support proper intercompany detection by distinguishing between
--          business, personal, and support entities
-- ============================================================================

-- Create entity table if it doesn't exist
CREATE TABLE IF NOT EXISTS acc.entity (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255),
    entity_type VARCHAR(20) NOT NULL DEFAULT 'business',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT entity_type_check CHECK (entity_type IN ('business', 'personal', 'support'))
);

COMMENT ON TABLE acc.entity IS 'Entity definitions with type classification for intercompany detection';
COMMENT ON COLUMN acc.entity.code IS 'Short entity code (e.g., bgs, mhb, csb)';
COMMENT ON COLUMN acc.entity.entity_type IS 'Entity classification: business (intercompany eligible), personal, or support';

-- Insert/update entity types
INSERT INTO acc.entity (code, name, entity_type) VALUES
    ('bgs', 'Breen GeoScience', 'business'),
    ('mhb', 'MHB Properties', 'business'),
    ('csb', 'CSB Personal', 'personal'),
    ('per', 'Personal', 'personal'),
    ('tax', 'Tax Account', 'support'),
    ('medical', 'Medical Account', 'support')
ON CONFLICT (code) DO UPDATE SET
    entity_type = EXCLUDED.entity_type,
    name = EXCLUDED.name,
    updated_at = CURRENT_TIMESTAMP;

-- Grant permissions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'frank') THEN
        GRANT ALL ON acc.entity TO frank;
        GRANT ALL ON acc.entity_id_seq TO frank;
    END IF;
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 012 completed: Entity table with entity_type column created';
END $$;
