-- ============================================================================
-- Migration 013: Replace spaces with underscores in gl_account_code
-- Created: 2025-12-31
-- Purpose: Update existing GL account codes to replace spaces with underscores
--          and add constraint to prevent future spaces
-- ============================================================================

-- Ensure the gl_accounts table exists (idempotent)
CREATE TABLE IF NOT EXISTS acc.gl_accounts (
    gl_account_code VARCHAR(100) PRIMARY KEY,
    description VARCHAR(500) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    entity VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.gl_accounts IS 'General Ledger account codes for financial reporting';
COMMENT ON COLUMN acc.gl_accounts.gl_account_code IS 'GL account code - should not contain spaces, use underscores instead';

-- Create indexes if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_gl_accounts_type') THEN
        CREATE INDEX idx_gl_accounts_type ON acc.gl_accounts(account_type);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_gl_accounts_entity') THEN
        CREATE INDEX idx_gl_accounts_entity ON acc.gl_accounts(entity);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_gl_accounts_active') THEN
        CREATE INDEX idx_gl_accounts_active ON acc.gl_accounts(is_active);
    END IF;
END $$;

-- ============================================================================
-- Step 1: Update existing records to replace spaces with underscores
-- ============================================================================

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Update gl_account_code values that contain spaces
    UPDATE acc.gl_accounts
    SET gl_account_code = REPLACE(gl_account_code, ' ', '_'),
        updated_at = CURRENT_TIMESTAMP
    WHERE gl_account_code LIKE '% %';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    IF updated_count > 0 THEN
        RAISE NOTICE 'Updated % GL account codes to replace spaces with underscores', updated_count;
    ELSE
        RAISE NOTICE 'No GL account codes with spaces found - no updates needed';
    END IF;
END $$;

-- ============================================================================
-- Step 2: Add CHECK constraint to prevent future spaces
-- ============================================================================

DO $$
BEGIN
    -- Drop the constraint if it already exists (for idempotency)
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'gl_account_code_no_spaces' 
        AND conrelid = 'acc.gl_accounts'::regclass
    ) THEN
        ALTER TABLE acc.gl_accounts DROP CONSTRAINT gl_account_code_no_spaces;
        RAISE NOTICE 'Dropped existing gl_account_code_no_spaces constraint';
    END IF;
    
    -- Add the constraint
    ALTER TABLE acc.gl_accounts
    ADD CONSTRAINT gl_account_code_no_spaces 
    CHECK (gl_account_code NOT LIKE '% %');
    
    RAISE NOTICE 'Added CHECK constraint gl_account_code_no_spaces to prevent spaces in gl_account_code';
END $$;

-- ============================================================================
-- Step 3: Grant permissions
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'frank') THEN
        GRANT ALL ON acc.gl_accounts TO frank;
    END IF;
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 013 completed: GL account codes updated and constraint added';
    RAISE NOTICE 'All spaces in gl_account_code have been replaced with underscores';
    RAISE NOTICE 'Future inserts/updates with spaces will be rejected by CHECK constraint';
END $$;
