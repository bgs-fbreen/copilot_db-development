-- ============================================================================
-- Migration: Add source_institution column to bank_staging
-- Created: 2025-12-29
-- Purpose: Track the source bank institution for imported transactions
-- ============================================================================

-- Add source_institution column to bank_staging table
ALTER TABLE acc.bank_staging 
ADD COLUMN IF NOT EXISTS source_institution VARCHAR(200);

COMMENT ON COLUMN acc.bank_staging.source_institution IS 'Bank institution name from source account';

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_staging_source_institution ON acc.bank_staging(source_institution);
