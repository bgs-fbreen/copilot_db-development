-- ============================================================================
-- Migration 011: Add unique constraint to wizard_account_status
-- Created: 2025-12-30
-- Purpose: Fix "no unique or exclusion constraint matching ON CONFLICT" error
--          when using skip_account() function in allocation wizard
-- ============================================================================

-- Add unique constraint if it doesn't exist (idempotent)
DO $$
BEGIN
    -- Check if the constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'wizard_account_status_account_entity_period_key'
          AND conrelid = 'acc.wizard_account_status'::regclass
    ) THEN
        -- First, check for and remove any duplicate rows that would violate the constraint
        DELETE FROM acc.wizard_account_status a
        USING acc.wizard_account_status b
        WHERE a.id > b.id
          AND a.account_code = b.account_code
          AND a.entity = b.entity
          AND a.period = b.period;
        
        -- Add the unique constraint
        ALTER TABLE acc.wizard_account_status 
        ADD CONSTRAINT wizard_account_status_account_entity_period_key 
        UNIQUE (account_code, entity, period);
        
        RAISE NOTICE 'Added unique constraint wizard_account_status_account_entity_period_key to acc.wizard_account_status';
    ELSE
        RAISE NOTICE 'Unique constraint wizard_account_status_account_entity_period_key already exists on acc.wizard_account_status';
    END IF;
END $$;
