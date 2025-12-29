-- ============================================================================
-- Bank Staging and Fuzzy Matching System
-- Created: 2025-12-28
-- Purpose: Staging table for bank imports with automatic GL code matching
-- ============================================================================

-- ============================================================================
-- BANK STAGING TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.bank_staging (
    id SERIAL PRIMARY KEY,
    source_account_code VARCHAR(50) NOT NULL REFERENCES acc.bank_account(code),
    normalized_date DATE NOT NULL,
    post_date DATE,
    description TEXT NOT NULL,
    memo TEXT,
    amount NUMERIC(12,2) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    gl_account_code VARCHAR(100) DEFAULT 'TODO',
    match_method VARCHAR(20) DEFAULT NULL,
    match_confidence INTEGER DEFAULT 0,
    reconciled BOOLEAN DEFAULT false,
    source VARCHAR(50) DEFAULT 'csv_import',
    import_id VARCHAR(200),
    check_number VARCHAR(20),
    source_institution VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.bank_staging IS 'Staging table for imported bank transactions with automatic GL matching';
COMMENT ON COLUMN acc.bank_staging.normalized_date IS 'Transaction date from bank statement';
COMMENT ON COLUMN acc.bank_staging.description IS 'Payee/merchant description from bank';
COMMENT ON COLUMN acc.bank_staging.entity IS 'Entity code extracted from source_account_code (e.g., bgs, per, mhb)';
COMMENT ON COLUMN acc.bank_staging.gl_account_code IS 'GL account code assigned by pattern matching or manual edit';
COMMENT ON COLUMN acc.bank_staging.match_method IS 'How GL code was assigned: pattern, manual, or NULL for TODO';
COMMENT ON COLUMN acc.bank_staging.match_confidence IS 'Confidence score of pattern match (0-100)';
COMMENT ON COLUMN acc.bank_staging.check_number IS 'Check number for check transactions';
COMMENT ON COLUMN acc.bank_staging.source_institution IS 'Bank institution name from source account';

CREATE INDEX idx_staging_account ON acc.bank_staging(source_account_code);
CREATE INDEX idx_staging_date ON acc.bank_staging(normalized_date);
CREATE INDEX idx_staging_entity ON acc.bank_staging(entity);
CREATE INDEX idx_staging_gl ON acc.bank_staging(gl_account_code);
CREATE INDEX idx_staging_match_method ON acc.bank_staging(match_method);
CREATE INDEX idx_staging_reconciled ON acc.bank_staging(reconciled);
CREATE INDEX idx_staging_check ON acc.bank_staging(check_number);
CREATE INDEX idx_staging_source_institution ON acc.bank_staging(source_institution);

-- ============================================================================
-- VENDOR GL PATTERNS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.vendor_gl_patterns (
    id SERIAL PRIMARY KEY,
    pattern TEXT NOT NULL,
    gl_account_code VARCHAR(100) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 100,
    active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.vendor_gl_patterns IS 'Patterns for automatic GL code assignment based on transaction description';
COMMENT ON COLUMN acc.vendor_gl_patterns.pattern IS 'Case-insensitive pattern to match against description (ILIKE)';
COMMENT ON COLUMN acc.vendor_gl_patterns.gl_account_code IS 'GL account code to assign when pattern matches';
COMMENT ON COLUMN acc.vendor_gl_patterns.entity IS 'Entity this pattern applies to';
COMMENT ON COLUMN acc.vendor_gl_patterns.priority IS 'Higher priority patterns are checked first (default 100)';

CREATE INDEX idx_vendor_pattern ON acc.vendor_gl_patterns(pattern);
CREATE INDEX idx_vendor_entity ON acc.vendor_gl_patterns(entity);
CREATE INDEX idx_vendor_priority ON acc.vendor_gl_patterns(priority DESC);
CREATE INDEX idx_vendor_active ON acc.vendor_gl_patterns(active);

-- ============================================================================
-- PATTERN SUGGESTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.pattern_suggestions (
    id SERIAL PRIMARY KEY,
    staging_id INTEGER REFERENCES acc.bank_staging(id),
    description TEXT NOT NULL,
    old_gl_account_code VARCHAR(100),
    new_gl_account_code VARCHAR(100) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    suggested_pattern TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.pattern_suggestions IS 'Suggestions for new patterns based on manual GL code corrections';
COMMENT ON COLUMN acc.pattern_suggestions.staging_id IS 'Reference to the transaction that was manually corrected';
COMMENT ON COLUMN acc.pattern_suggestions.old_gl_account_code IS 'GL code before manual edit (typically TODO or pattern match)';
COMMENT ON COLUMN acc.pattern_suggestions.new_gl_account_code IS 'GL code after manual edit';
COMMENT ON COLUMN acc.pattern_suggestions.suggested_pattern IS 'Suggested pattern extracted from description';
COMMENT ON COLUMN acc.pattern_suggestions.status IS 'Status: pending, approved, rejected, applied';

CREATE INDEX idx_suggestions_status ON acc.pattern_suggestions(status);
CREATE INDEX idx_suggestions_entity ON acc.pattern_suggestions(entity);
CREATE INDEX idx_suggestions_staging ON acc.pattern_suggestions(staging_id);

-- ============================================================================
-- TRIGGER: APPLY FUZZY MATCHING ON INSERT
-- ============================================================================

CREATE OR REPLACE FUNCTION acc.fn_apply_fuzzy_matching()
RETURNS TRIGGER AS $$
DECLARE
    matched_gl_code VARCHAR(100);
    matched_confidence INTEGER;
BEGIN
    -- Try to find a matching pattern for this entity and description
    SELECT 
        vp.gl_account_code,
        vp.priority
    INTO 
        matched_gl_code,
        matched_confidence
    FROM acc.vendor_gl_patterns vp
    WHERE vp.entity = NEW.entity
      AND vp.active = true
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

CREATE TRIGGER trg_apply_fuzzy_matching
    BEFORE INSERT ON acc.bank_staging
    FOR EACH ROW
    EXECUTE FUNCTION acc.fn_apply_fuzzy_matching();

COMMENT ON TRIGGER trg_apply_fuzzy_matching ON acc.bank_staging IS 
    'Automatically applies GL code based on vendor patterns when transaction is inserted';

-- ============================================================================
-- TRIGGER: DETECT MANUAL CORRECTIONS AND CREATE PATTERN SUGGESTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION acc.fn_set_match_method_manual()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if gl_account_code was manually changed
    IF NEW.gl_account_code IS DISTINCT FROM OLD.gl_account_code THEN
        -- Update match method to manual
        NEW.match_method := 'manual';
        NEW.updated_at := CURRENT_TIMESTAMP;
        
        -- Create a pattern suggestion for review
        -- Only if old code was TODO or pattern (not already manual)
        IF OLD.match_method IS NULL OR OLD.match_method = 'pattern' THEN
            INSERT INTO acc.pattern_suggestions 
                (staging_id, description, old_gl_account_code, new_gl_account_code, 
                 entity, suggested_pattern)
            VALUES 
                (NEW.id, NEW.description, OLD.gl_account_code, NEW.gl_account_code,
                 NEW.entity, NEW.description);
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_match_method_manual
    BEFORE UPDATE ON acc.bank_staging
    FOR EACH ROW
    WHEN (NEW.gl_account_code IS DISTINCT FROM OLD.gl_account_code)
    EXECUTE FUNCTION acc.fn_set_match_method_manual();

COMMENT ON TRIGGER trg_set_match_method_manual ON acc.bank_staging IS 
    'Detects manual GL code changes and creates pattern suggestions for review';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON acc.bank_staging TO frank;
GRANT ALL ON acc.vendor_gl_patterns TO frank;
GRANT ALL ON acc.pattern_suggestions TO frank;
GRANT ALL ON SEQUENCE acc.bank_staging_id_seq TO frank;
GRANT ALL ON SEQUENCE acc.vendor_gl_patterns_id_seq TO frank;
GRANT ALL ON SEQUENCE acc.pattern_suggestions_id_seq TO frank;
