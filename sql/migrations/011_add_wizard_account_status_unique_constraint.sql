-- ============================================================================
-- Migration 011: Add unique constraint to wizard_account_status
-- Created: 2025-12-30
-- Purpose: Fix "no unique or exclusion constraint matching ON CONFLICT" error
--          when using skip_account() function in allocation wizard
-- ============================================================================

-- Add unique constraint if it doesn't exist (idempotent)
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    -- Check if the constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'wizard_account_status_account_entity_period_key'
          AND conrelid = 'acc.wizard_account_status'::regclass
    ) THEN
        -- First, check for and remove any duplicate rows that would violate the constraint
        -- This uses a CTE with row_number to keep only the first occurrence (lowest id)
        WITH duplicates AS (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY account_code, entity, period 
                           ORDER BY id
                       ) as rn
                FROM acc.wizard_account_status
            ) ranked
            WHERE rn > 1
        )
        DELETE FROM acc.wizard_account_status
        WHERE id IN (SELECT id FROM duplicates);
        
        GET DIAGNOSTICS duplicate_count = ROW_COUNT;
        IF duplicate_count > 0 THEN
            RAISE NOTICE 'Removed % duplicate rows', duplicate_count;
        END IF;
        
        -- Add the unique constraint
        ALTER TABLE acc.wizard_account_status 
        ADD CONSTRAINT wizard_account_status_account_entity_period_key 
        UNIQUE (account_code, entity, period);
        
        RAISE NOTICE 'Added unique constraint wizard_account_status_account_entity_period_key to acc.wizard_account_status';
    ELSE
        RAISE NOTICE 'Unique constraint wizard_account_status_account_entity_period_key already exists on acc.wizard_account_status';
    END IF;
END $$;
