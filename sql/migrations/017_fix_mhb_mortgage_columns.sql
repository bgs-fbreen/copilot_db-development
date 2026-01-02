-- ============================================================================
-- Migration: Fix mhb.mortgage Column Names for Schema Consistency
-- Created: 2026-01-02
-- Description: Renames mhb.mortgage columns to match per.mortgage and Python code expectations
--              - start_date → issued_on
--              - original_amount → original_balance
--              - maturity_date → matures_on
-- ============================================================================

-- ============================================================================
-- Rename start_date to issued_on
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mhb' 
        AND table_name = 'mortgage' 
        AND column_name = 'start_date'
    ) THEN
        ALTER TABLE mhb.mortgage RENAME COLUMN start_date TO issued_on;
        RAISE NOTICE 'Renamed mhb.mortgage.start_date to issued_on';
    ELSE
        RAISE NOTICE 'Column mhb.mortgage.start_date does not exist (already renamed or never existed)';
    END IF;
END $$;

-- ============================================================================
-- Rename original_amount to original_balance
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mhb' 
        AND table_name = 'mortgage' 
        AND column_name = 'original_amount'
    ) THEN
        ALTER TABLE mhb.mortgage RENAME COLUMN original_amount TO original_balance;
        RAISE NOTICE 'Renamed mhb.mortgage.original_amount to original_balance';
    ELSE
        RAISE NOTICE 'Column mhb.mortgage.original_amount does not exist (already renamed or never existed)';
    END IF;
END $$;

-- ============================================================================
-- Rename maturity_date to matures_on
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mhb' 
        AND table_name = 'mortgage' 
        AND column_name = 'maturity_date'
    ) THEN
        ALTER TABLE mhb.mortgage RENAME COLUMN maturity_date TO matures_on;
        RAISE NOTICE 'Renamed mhb.mortgage.maturity_date to matures_on';
    ELSE
        RAISE NOTICE 'Column mhb.mortgage.maturity_date does not exist (already renamed or never existed)';
    END IF;
END $$;

-- ============================================================================
-- Add column comments for documentation
-- ============================================================================

COMMENT ON COLUMN mhb.mortgage.issued_on IS 'Date the mortgage loan was issued';
COMMENT ON COLUMN mhb.mortgage.original_balance IS 'Original principal amount of the mortgage';
COMMENT ON COLUMN mhb.mortgage.matures_on IS 'Date the mortgage loan matures/is fully paid';
COMMENT ON COLUMN mhb.mortgage.current_balance IS 'Current principal balance remaining';
COMMENT ON COLUMN mhb.mortgage.interest_rate IS 'Annual interest rate as percentage (e.g., 3.750)';

-- Add comment on gl_account_code if it exists (added by migration 016)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mhb' 
        AND table_name = 'mortgage' 
        AND column_name = 'gl_account_code'
    ) THEN
        EXECUTE 'COMMENT ON COLUMN mhb.mortgage.gl_account_code IS ''GL account code (e.g., mhb:mortgage:711pine)''';
    END IF;
END $$;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
