-- ============================================================================
-- Migration: Add Mortgage Rate History Support for Variable Rate Mortgages
-- Created: 2026-01-03
-- Description: Adds mortgage_rate_history table to track interest rate changes
--              over time for variable/adjustable rate mortgages (e.g., 711pine,
--              819helen). This enables accurate projections using the most
--              recent interest rate.
-- ============================================================================

-- ============================================================================
-- PER.MORTGAGE_RATE_HISTORY - Personal mortgage rate change history
-- ============================================================================

CREATE TABLE IF NOT EXISTS per.mortgage_rate_history (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES per.mortgage(id) ON DELETE CASCADE,
    effective_date DATE NOT NULL,
    interest_rate NUMERIC(6,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.mortgage_rate_history IS 'Interest rate change history for variable rate mortgages';
COMMENT ON COLUMN per.mortgage_rate_history.mortgage_id IS 'Foreign key to per.mortgage';
COMMENT ON COLUMN per.mortgage_rate_history.effective_date IS 'Date when the new interest rate became effective';
COMMENT ON COLUMN per.mortgage_rate_history.interest_rate IS 'Annual interest rate as percentage (e.g., 8.2500 for 8.25%)';

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_per_rate_history_mortgage ON per.mortgage_rate_history(mortgage_id);
CREATE INDEX IF NOT EXISTS idx_per_rate_history_date ON per.mortgage_rate_history(effective_date);

-- Ensure unique rate per mortgage per date (prevents duplicate rate changes)
CREATE UNIQUE INDEX IF NOT EXISTS idx_per_rate_history_unique ON per.mortgage_rate_history(mortgage_id, effective_date);

-- ============================================================================
-- MHB.MORTGAGE_RATE_HISTORY - MHB mortgage rate change history
-- ============================================================================

CREATE TABLE IF NOT EXISTS mhb.mortgage_rate_history (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES mhb.mortgage(id) ON DELETE CASCADE,
    effective_date DATE NOT NULL,
    interest_rate NUMERIC(6,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.mortgage_rate_history IS 'Interest rate change history for variable rate mortgages';
COMMENT ON COLUMN mhb.mortgage_rate_history.mortgage_id IS 'Foreign key to mhb.mortgage';
COMMENT ON COLUMN mhb.mortgage_rate_history.effective_date IS 'Date when the new interest rate became effective';
COMMENT ON COLUMN mhb.mortgage_rate_history.interest_rate IS 'Annual interest rate as percentage (e.g., 8.2500 for 8.25%)';

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_mhb_rate_history_mortgage ON mhb.mortgage_rate_history(mortgage_id);
CREATE INDEX IF NOT EXISTS idx_mhb_rate_history_date ON mhb.mortgage_rate_history(effective_date);

-- Ensure unique rate per mortgage per date (prevents duplicate rate changes)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mhb_rate_history_unique ON mhb.mortgage_rate_history(mortgage_id, effective_date);

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT ALL ON TABLE per.mortgage_rate_history TO frank;
GRANT ALL ON SEQUENCE per.mortgage_rate_history_id_seq TO frank;

GRANT ALL ON TABLE mhb.mortgage_rate_history TO frank;
GRANT ALL ON SEQUENCE mhb.mortgage_rate_history_id_seq TO frank;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
