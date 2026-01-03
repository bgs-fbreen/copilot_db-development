-- ============================================================================
-- Migration: Create Property Tax Tracking System
-- Created: 2026-01-03
-- Description: Creates comprehensive property tax tracking system for rental
--              properties (905brown, 711pine, 819helen) including:
--              - Tax bill tracking with assessment values
--              - Payment history with partial payment support
--              - Foreclosure risk analysis (3+ years delinquent)
--              - Payment priority recommendations
--              - Assessment and tax trend analysis
-- ============================================================================

-- ============================================================================
-- PROPERTY_TAX_BILL - Tax bills for rental properties
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.property_tax_bill (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL,
    tax_year INTEGER NOT NULL,
    tax_season VARCHAR(20) NOT NULL,
    assessed_value NUMERIC(12,2),
    taxable_value NUMERIC(12,2),
    pre_pct NUMERIC(5,2) DEFAULT 0,
    millage_rate NUMERIC(8,4),
    total_due NUMERIC(12,2) NOT NULL,
    total_paid NUMERIC(12,2) DEFAULT 0,
    balance_due NUMERIC(12,2) NOT NULL,
    due_date DATE,
    paid_date DATE,
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    late_fees NUMERIC(10,2) DEFAULT 0,
    interest_charges NUMERIC(10,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_tax_season CHECK (tax_season IN ('Summer', 'Winter')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('unpaid', 'partial', 'paid', 'delinquent')),
    CONSTRAINT chk_pre_pct CHECK (pre_pct >= 0 AND pre_pct <= 100),
    CONSTRAINT chk_balance CHECK (balance_due >= 0),
    CONSTRAINT uk_tax_bill UNIQUE (property_code, tax_year, tax_season)
);

COMMENT ON TABLE acc.property_tax_bill IS 'Property tax bills with assessment values and payment tracking';
COMMENT ON COLUMN acc.property_tax_bill.property_code IS 'Property code: 905brown, 711pine, 819helen';
COMMENT ON COLUMN acc.property_tax_bill.tax_season IS 'Summer (July) or Winter (December)';
COMMENT ON COLUMN acc.property_tax_bill.assessed_value IS 'Full assessed property value';
COMMENT ON COLUMN acc.property_tax_bill.taxable_value IS 'Taxable value (may be capped)';
COMMENT ON COLUMN acc.property_tax_bill.pre_pct IS 'Principal Residence Exemption percentage (0-100)';
COMMENT ON COLUMN acc.property_tax_bill.millage_rate IS 'Mill rate applied to taxable value';
COMMENT ON COLUMN acc.property_tax_bill.total_due IS 'Total amount due including fees';
COMMENT ON COLUMN acc.property_tax_bill.total_paid IS 'Total amount paid so far';
COMMENT ON COLUMN acc.property_tax_bill.balance_due IS 'Remaining balance';
COMMENT ON COLUMN acc.property_tax_bill.payment_status IS 'unpaid, partial, paid, delinquent';

CREATE INDEX IF NOT EXISTS idx_property_tax_property ON acc.property_tax_bill(property_code);
CREATE INDEX IF NOT EXISTS idx_property_tax_year ON acc.property_tax_bill(tax_year);
CREATE INDEX IF NOT EXISTS idx_property_tax_season ON acc.property_tax_bill(tax_season);
CREATE INDEX IF NOT EXISTS idx_property_tax_status ON acc.property_tax_bill(payment_status);
CREATE INDEX IF NOT EXISTS idx_property_tax_balance ON acc.property_tax_bill(balance_due) WHERE balance_due > 0;

-- ============================================================================
-- PROPERTY_TAX_PAYMENT - Individual tax payments
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.property_tax_payment (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER NOT NULL REFERENCES acc.property_tax_bill(id) ON DELETE CASCADE,
    payment_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(50),
    check_number VARCHAR(50),
    confirmation_number VARCHAR(100),
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_amount CHECK (amount > 0)
);

COMMENT ON TABLE acc.property_tax_payment IS 'Individual tax payments applied to bills';
COMMENT ON COLUMN acc.property_tax_payment.tax_bill_id IS 'Foreign key to property_tax_bill';
COMMENT ON COLUMN acc.property_tax_payment.bank_staging_id IS 'Link to bank_staging for import';

CREATE INDEX IF NOT EXISTS idx_property_tax_payment_bill ON acc.property_tax_payment(tax_bill_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_payment_date ON acc.property_tax_payment(payment_date);

-- ============================================================================
-- VIEW: Foreclosure Risk Analysis
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_property_tax_foreclosure_risk AS
SELECT 
    b.property_code,
    b.tax_year,
    b.tax_season,
    b.total_due,
    b.balance_due,
    EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year as years_delinquent,
    CASE 
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 5 THEN 'CRITICAL'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 3 THEN 'HIGH'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 2 THEN 'MEDIUM'
        ELSE 'LOW'
    END as risk_level
FROM acc.property_tax_bill b
WHERE b.balance_due > 0
  AND EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 3
ORDER BY b.tax_year, b.property_code;

COMMENT ON VIEW acc.v_property_tax_foreclosure_risk IS 'Properties at risk of tax foreclosure (3+ years delinquent)';

-- ============================================================================
-- VIEW: Payment Priority Recommendations
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_property_tax_priority AS
SELECT 
    b.property_code,
    b.tax_year,
    b.tax_season,
    b.total_due,
    b.total_paid,
    b.balance_due,
    EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year as years_delinquent,
    CASE 
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 5 THEN 1
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 3 THEN 2
        WHEN b.total_paid > 0 AND b.balance_due > 0 THEN 3  -- Partial payments
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 2 THEN 4
        ELSE 5
    END as priority_rank,
    CASE 
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 5 THEN 'CRITICAL - Foreclosure imminent'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 3 THEN 'HIGH - Foreclosure risk'
        WHEN b.total_paid > 0 AND b.balance_due > 0 THEN 'MEDIUM - Partial payment'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - b.tax_year >= 2 THEN 'MEDIUM - 2 years delinquent'
        ELSE 'LOW - Recent'
    END as priority_reason
FROM acc.property_tax_bill b
WHERE b.balance_due > 0
ORDER BY priority_rank, b.tax_year, b.tax_season;

COMMENT ON VIEW acc.v_property_tax_priority IS 'Payment priority recommendations based on foreclosure risk';

-- ============================================================================
-- VIEW: Assessment and Tax Trends
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_property_tax_trends AS
SELECT 
    b.property_code,
    b.tax_year,
    MAX(b.assessed_value) as assessed_value,
    MAX(b.taxable_value) as taxable_value,
    MAX(b.pre_pct) as pre_pct,
    SUM(b.total_due) as annual_tax,
    SUM(b.total_paid) as annual_paid,
    SUM(b.balance_due) as annual_balance,
    LAG(MAX(b.assessed_value)) OVER (PARTITION BY b.property_code ORDER BY b.tax_year) as prev_assessed,
    LAG(SUM(b.total_due)) OVER (PARTITION BY b.property_code ORDER BY b.tax_year) as prev_tax
FROM acc.property_tax_bill b
GROUP BY b.property_code, b.tax_year
ORDER BY b.property_code, b.tax_year;

COMMENT ON VIEW acc.v_property_tax_trends IS 'Historical assessment and tax trends with year-over-year comparisons';

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT ALL ON TABLE acc.property_tax_bill TO frank;
GRANT ALL ON SEQUENCE acc.property_tax_bill_id_seq TO frank;

GRANT ALL ON TABLE acc.property_tax_payment TO frank;
GRANT ALL ON SEQUENCE acc.property_tax_payment_id_seq TO frank;

-- Views automatically inherit permissions from underlying tables

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
