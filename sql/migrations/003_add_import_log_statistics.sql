-- ============================================================================
-- Migration: Add detailed statistics columns to import_log
-- Created: 2025-12-28
-- Description: Adds columns to store detailed import statistics including
--              date span, transaction counts, and debit/credit summaries
-- ============================================================================

-- Add new columns to import_log table
ALTER TABLE acc.import_log
    ADD COLUMN IF NOT EXISTS date_span_days INTEGER,
    ADD COLUMN IF NOT EXISTS total_count INTEGER,
    ADD COLUMN IF NOT EXISTS debit_count INTEGER,
    ADD COLUMN IF NOT EXISTS credit_count INTEGER,
    ADD COLUMN IF NOT EXISTS debit_total NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS debit_largest NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS debit_smallest NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS debit_average NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS credit_total NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS credit_largest NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS credit_smallest NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS credit_average NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS net_flow NUMERIC(12,2);

-- Add comments to document the new columns
COMMENT ON COLUMN acc.import_log.date_span_days IS 'Number of days between earliest and latest transaction in the import';
COMMENT ON COLUMN acc.import_log.total_count IS 'Total number of transactions imported (excluding duplicates)';
COMMENT ON COLUMN acc.import_log.debit_count IS 'Number of debit transactions (negative amounts)';
COMMENT ON COLUMN acc.import_log.credit_count IS 'Number of credit transactions (positive amounts)';
COMMENT ON COLUMN acc.import_log.debit_total IS 'Total absolute value of all debits';
COMMENT ON COLUMN acc.import_log.debit_largest IS 'Largest single debit (absolute value)';
COMMENT ON COLUMN acc.import_log.debit_smallest IS 'Smallest single debit (absolute value)';
COMMENT ON COLUMN acc.import_log.debit_average IS 'Average debit amount (absolute value)';
COMMENT ON COLUMN acc.import_log.credit_total IS 'Total of all credits';
COMMENT ON COLUMN acc.import_log.credit_largest IS 'Largest single credit';
COMMENT ON COLUMN acc.import_log.credit_smallest IS 'Smallest single credit';
COMMENT ON COLUMN acc.import_log.credit_average IS 'Average credit amount';
COMMENT ON COLUMN acc.import_log.net_flow IS 'Net cash flow (sum of all amounts where debits are negative)';
