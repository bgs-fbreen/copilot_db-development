-- ============================================================================
-- Migration 014: Allow Wildcard Entity Patterns
-- Created: 2025-12-31
-- Purpose: Enable wildcard patterns by making vendor_gl_patterns.entity nullable
-- ============================================================================

-- Make entity column nullable to support wildcard patterns
ALTER TABLE acc.vendor_gl_patterns 
    ALTER COLUMN entity DROP NOT NULL;

COMMENT ON COLUMN acc.vendor_gl_patterns.entity IS 
    'Entity this pattern applies to. NULL means pattern applies to all entities (wildcard).';

-- Update the fuzzy matching trigger to support wildcard patterns
CREATE OR REPLACE FUNCTION acc.fn_apply_fuzzy_matching()
RETURNS TRIGGER AS $$
DECLARE
    matched_gl_code VARCHAR(100);
    matched_confidence INTEGER;
BEGIN
    -- Try to find a matching pattern for this entity and description
    -- Patterns with NULL entity are wildcards that match all entities
    SELECT 
        vp.gl_account_code,
        vp.priority
    INTO 
        matched_gl_code,
        matched_confidence
    FROM acc.vendor_gl_patterns vp
    WHERE (vp.entity IS NULL OR vp.entity = NEW.entity)
      AND vp.is_active = true
      AND NEW.description ILIKE '%' || vp.pattern || '%'
    ORDER BY vp.priority DESC, vp.id
    LIMIT 1;
    
    -- If a pattern matched, assign the GL code
    IF matched_gl_code IS NOT NULL THEN
        NEW.gl_account_code := matched_gl_code;
        NEW.match_method := 'pattern';
        NEW.match_confidence := matched_confidence;
    ELSE
        -- No match found, mark as TODO
        NEW.gl_account_code := 'TODO';
        NEW.match_method := NULL;
        NEW.match_confidence := 0;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION acc.fn_apply_fuzzy_matching IS 
    'Automatically applies GL code based on vendor patterns. Supports wildcard patterns where entity IS NULL.';
