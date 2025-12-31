-- ============================================================================
-- Test script for gl_account_code space replacement
-- Tests the migration and constraint functionality
-- ============================================================================

-- This script can be run against a test database to verify the migration works

-- Test 1: Create table with some test data containing spaces
CREATE TABLE IF NOT EXISTS acc.gl_accounts (
    gl_account_code VARCHAR(100) PRIMARY KEY,
    description VARCHAR(500) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    entity VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data with spaces
INSERT INTO acc.gl_accounts (gl_account_code, description, account_type, entity) VALUES
    ('bgs:proj exp:gas', 'Project Expense - Gas', 'expense', 'bgs'),
    ('bgs:some code', 'Some Account Code', 'expense', 'bgs'),
    ('mhb:rent income', 'Rental Income', 'income', 'mhb'),
    ('bgs:no_spaces', 'Already Correct', 'expense', 'bgs'),
    ('test:conflict_code', 'Code that will conflict', 'expense', 'bgs'),
    ('test:conflict code', 'Code with space that becomes conflict', 'expense', 'bgs')
ON CONFLICT (gl_account_code) DO NOTHING;

-- Test 2: Show data before migration
SELECT 'BEFORE MIGRATION:' as status;
SELECT gl_account_code, description FROM acc.gl_accounts ORDER BY gl_account_code;

-- Test 3: Check for conflicts (same logic as migration)
SELECT 'CHECKING FOR CONFLICTS:' as status;
SELECT 
    gl_account_code as original_code,
    REPLACE(gl_account_code, ' ', '_') as new_code,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM acc.gl_accounts g2 
            WHERE g2.gl_account_code = REPLACE(gl_accounts.gl_account_code, ' ', '_')
        ) THEN 'CONFLICT!'
        ELSE 'OK'
    END as status
FROM acc.gl_accounts
WHERE gl_account_code LIKE '% %'
ORDER BY gl_account_code;

-- Test 4: Run the update (same as in migration) - this should fail due to conflict
DO $$
DECLARE
    updated_count INTEGER := 0;
    conflict_count INTEGER := 0;
BEGIN
    -- First, check for potential conflicts
    SELECT COUNT(*) INTO conflict_count
    FROM (
        SELECT REPLACE(gl_account_code, ' ', '_') as new_code
        FROM acc.gl_accounts
        WHERE gl_account_code LIKE '% %'
    ) space_codes
    WHERE EXISTS (
        SELECT 1 FROM acc.gl_accounts 
        WHERE gl_account_code = space_codes.new_code
    );
    
    IF conflict_count > 0 THEN
        RAISE NOTICE 'TEST: Found % conflicts (as expected with test data)', conflict_count;
        RAISE NOTICE 'TEST: Removing conflicting records for test to continue...';
        
        -- For testing purposes, remove the pre-existing codes that would conflict
        DELETE FROM acc.gl_accounts 
        WHERE gl_account_code IN (
            SELECT REPLACE(gl_account_code, ' ', '_')
            FROM acc.gl_accounts
            WHERE gl_account_code LIKE '% %'
        ) AND gl_account_code NOT LIKE '% %';
        
        RAISE NOTICE 'TEST: Conflicts resolved, proceeding with update';
    END IF;
    
    -- Now proceed with update
    UPDATE acc.gl_accounts
    SET gl_account_code = REPLACE(gl_account_code, ' ', '_'),
        updated_at = CURRENT_TIMESTAMP
    WHERE gl_account_code LIKE '% %';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    IF updated_count > 0 THEN
        RAISE NOTICE 'TEST: Updated % GL account codes', updated_count;
    END IF;
END $$;

-- Show data after migration
SELECT 'AFTER MIGRATION:' as status;
SELECT gl_account_code, description FROM acc.gl_accounts ORDER BY gl_account_code;

-- Test 5: Add the constraint
ALTER TABLE acc.gl_accounts
DROP CONSTRAINT IF EXISTS gl_account_code_no_spaces;

ALTER TABLE acc.gl_accounts
ADD CONSTRAINT gl_account_code_no_spaces 
CHECK (gl_account_code NOT LIKE '% %');

-- Test 6: Try to insert with spaces (should fail)
SELECT 'Testing constraint (next insert should fail):' as status;
DO $$
BEGIN
    INSERT INTO acc.gl_accounts (gl_account_code, description, account_type, entity)
    VALUES ('bad:code with space', 'This should fail', 'expense', 'bgs');
    RAISE EXCEPTION 'ERROR: Constraint did not prevent space in gl_account_code!';
EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'SUCCESS: Constraint properly rejected gl_account_code with spaces';
END $$;

-- Test 7: Try to insert without spaces (should succeed)
INSERT INTO acc.gl_accounts (gl_account_code, description, account_type, entity)
VALUES ('good:code_no_space', 'This should work', 'expense', 'bgs')
ON CONFLICT (gl_account_code) DO NOTHING;

SELECT 'Final verification - all codes should have underscores instead of spaces:' as status;
SELECT gl_account_code, description FROM acc.gl_accounts ORDER BY gl_account_code;

-- Cleanup (optional - comment out if you want to keep test data)
-- DROP TABLE acc.gl_accounts;
