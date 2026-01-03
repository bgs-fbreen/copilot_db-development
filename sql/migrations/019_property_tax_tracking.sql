-- ============================================================================
-- Migration: Create Property Tax Tracking System
-- Created: 2026-01-03
-- Description: Creates comprehensive property tax tracking system including:
--              - Tax bills with assessment information
--              - Millage breakdown details per taxing authority
--              - Payment history with interest/penalty tracking
--              - Automatic balance updates via triggers
--              - Views for outstanding balances and tax history
-- ============================================================================

-- ============================================================================
-- PER.PROPERTY_TAX_BILL - Personal property tax bills
-- ============================================================================

CREATE TABLE IF NOT EXISTS per.property_tax_bill (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL,
    tax_year INTEGER NOT NULL,
    tax_season VARCHAR(10) NOT NULL,  -- 'summer' or 'winter'
    
    -- Assessment Info
    school_district VARCHAR(20),
    property_class VARCHAR(20),       -- '401' = residential
    pre_pct NUMERIC(7,4),             -- Principal Residence Exemption %
    assessed_value NUMERIC(12,2),     -- SEV
    taxable_value NUMERIC(12,2),
    
    -- Bill Amounts
    total_millage NUMERIC(10,6),
    base_tax NUMERIC(10,2) NOT NULL,
    admin_fee NUMERIC(10,2) DEFAULT 0,
    total_due NUMERIC(10,2) NOT NULL,
    
    -- Due Date & Status
    due_date DATE,
    
    -- Payment Tracking (updated by triggers)
    total_paid NUMERIC(10,2) DEFAULT 0,
    interest_paid NUMERIC(10,2) DEFAULT 0,
    balance_due NUMERIC(10,2),  -- Calculated as total_due - total_paid
    status VARCHAR(20) DEFAULT 'unpaid',  -- 'unpaid', 'partial', 'paid', 'delinquent'
    
    -- Metadata
    bill_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(property_code, tax_year, tax_season),
    CONSTRAINT chk_per_tax_season CHECK (tax_season IN ('summer', 'winter')),
    CONSTRAINT chk_per_tax_status CHECK (status IN ('unpaid', 'partial', 'paid', 'delinquent'))
);

COMMENT ON TABLE per.property_tax_bill IS 'Personal property tax bills with assessment and payment tracking';
COMMENT ON COLUMN per.property_tax_bill.tax_season IS 'summer or winter billing cycle';
COMMENT ON COLUMN per.property_tax_bill.property_class IS '401 = residential, etc.';
COMMENT ON COLUMN per.property_tax_bill.pre_pct IS 'Principal Residence Exemption percentage (e.g., 0.1800 for 18%)';
COMMENT ON COLUMN per.property_tax_bill.total_millage IS 'Total millage rate applied';
COMMENT ON COLUMN per.property_tax_bill.balance_due IS 'Automatically calculated: total_due - total_paid';

CREATE INDEX IF NOT EXISTS idx_per_tax_bill_property ON per.property_tax_bill(property_code);
CREATE INDEX IF NOT EXISTS idx_per_tax_bill_year ON per.property_tax_bill(tax_year);
CREATE INDEX IF NOT EXISTS idx_per_tax_bill_status ON per.property_tax_bill(status);

-- ============================================================================
-- PER.PROPERTY_TAX_DETAIL - Personal property tax millage breakdown
-- ============================================================================

CREATE TABLE IF NOT EXISTS per.property_tax_detail (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER NOT NULL REFERENCES per.property_tax_bill(id) ON DELETE CASCADE,
    
    taxing_authority VARCHAR(100) NOT NULL,  -- 'STATE ED', 'CITY OPERATING', etc.
    millage_rate NUMERIC(10,6) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    amount_paid NUMERIC(10,2) DEFAULT 0,
    
    UNIQUE(tax_bill_id, taxing_authority)
);

COMMENT ON TABLE per.property_tax_detail IS 'Millage breakdown by taxing authority for each tax bill';
COMMENT ON COLUMN per.property_tax_detail.taxing_authority IS 'Tax authority name (STATE ED, CITY OPERATING, etc.)';
COMMENT ON COLUMN per.property_tax_detail.millage_rate IS 'Millage rate for this authority';

CREATE INDEX IF NOT EXISTS idx_per_tax_detail_bill ON per.property_tax_detail(tax_bill_id);

-- ============================================================================
-- PER.PROPERTY_TAX_PAYMENT - Personal property tax payment history
-- ============================================================================

CREATE TABLE IF NOT EXISTS per.property_tax_payment (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER NOT NULL REFERENCES per.property_tax_bill(id),
    
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    interest_amount NUMERIC(10,2) DEFAULT 0,
    penalty_amount NUMERIC(10,2) DEFAULT 0,
    total_payment NUMERIC(10,2) NOT NULL,
    
    receipt_number VARCHAR(50),
    payment_method VARCHAR(50),  -- 'check', 'online', 'escrow'
    paid_from VARCHAR(100),      -- 'escrow', 'direct', account code
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE per.property_tax_payment IS 'Payment history for property tax bills';
COMMENT ON COLUMN per.property_tax_payment.payment_method IS 'check, online, escrow, etc.';
COMMENT ON COLUMN per.property_tax_payment.paid_from IS 'Payment source: escrow, direct, or account code';

CREATE INDEX IF NOT EXISTS idx_per_tax_payment_bill ON per.property_tax_payment(tax_bill_id);
CREATE INDEX IF NOT EXISTS idx_per_tax_payment_date ON per.property_tax_payment(payment_date);

-- ============================================================================
-- MHB.PROPERTY_TAX_BILL - MHB property tax bills
-- ============================================================================

CREATE TABLE IF NOT EXISTS mhb.property_tax_bill (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL,
    tax_year INTEGER NOT NULL,
    tax_season VARCHAR(10) NOT NULL,  -- 'summer' or 'winter'
    
    -- Assessment Info
    school_district VARCHAR(20),
    property_class VARCHAR(20),       -- '401' = residential
    pre_pct NUMERIC(7,4),             -- Principal Residence Exemption %
    assessed_value NUMERIC(12,2),     -- SEV
    taxable_value NUMERIC(12,2),
    
    -- Bill Amounts
    total_millage NUMERIC(10,6),
    base_tax NUMERIC(10,2) NOT NULL,
    admin_fee NUMERIC(10,2) DEFAULT 0,
    total_due NUMERIC(10,2) NOT NULL,
    
    -- Due Date & Status
    due_date DATE,
    
    -- Payment Tracking (updated by triggers)
    total_paid NUMERIC(10,2) DEFAULT 0,
    interest_paid NUMERIC(10,2) DEFAULT 0,
    balance_due NUMERIC(10,2),  -- Calculated as total_due - total_paid
    status VARCHAR(20) DEFAULT 'unpaid',  -- 'unpaid', 'partial', 'paid', 'delinquent'
    
    -- Metadata
    bill_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(property_code, tax_year, tax_season),
    CONSTRAINT chk_mhb_tax_season CHECK (tax_season IN ('summer', 'winter')),
    CONSTRAINT chk_mhb_tax_status CHECK (status IN ('unpaid', 'partial', 'paid', 'delinquent'))
);

COMMENT ON TABLE mhb.property_tax_bill IS 'MHB property tax bills with assessment and payment tracking';
COMMENT ON COLUMN mhb.property_tax_bill.tax_season IS 'summer or winter billing cycle';
COMMENT ON COLUMN mhb.property_tax_bill.property_class IS '401 = residential, etc.';
COMMENT ON COLUMN mhb.property_tax_bill.pre_pct IS 'Principal Residence Exemption percentage (e.g., 0.1800 for 18%)';
COMMENT ON COLUMN mhb.property_tax_bill.total_millage IS 'Total millage rate applied';
COMMENT ON COLUMN mhb.property_tax_bill.balance_due IS 'Automatically calculated: total_due - total_paid';

CREATE INDEX IF NOT EXISTS idx_mhb_tax_bill_property ON mhb.property_tax_bill(property_code);
CREATE INDEX IF NOT EXISTS idx_mhb_tax_bill_year ON mhb.property_tax_bill(tax_year);
CREATE INDEX IF NOT EXISTS idx_mhb_tax_bill_status ON mhb.property_tax_bill(status);

-- ============================================================================
-- MHB.PROPERTY_TAX_DETAIL - MHB property tax millage breakdown
-- ============================================================================

CREATE TABLE IF NOT EXISTS mhb.property_tax_detail (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER NOT NULL REFERENCES mhb.property_tax_bill(id) ON DELETE CASCADE,
    
    taxing_authority VARCHAR(100) NOT NULL,  -- 'STATE ED', 'CITY OPERATING', etc.
    millage_rate NUMERIC(10,6) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    amount_paid NUMERIC(10,2) DEFAULT 0,
    
    UNIQUE(tax_bill_id, taxing_authority)
);

COMMENT ON TABLE mhb.property_tax_detail IS 'Millage breakdown by taxing authority for each tax bill';
COMMENT ON COLUMN mhb.property_tax_detail.taxing_authority IS 'Tax authority name (STATE ED, CITY OPERATING, etc.)';
COMMENT ON COLUMN mhb.property_tax_detail.millage_rate IS 'Millage rate for this authority';

CREATE INDEX IF NOT EXISTS idx_mhb_tax_detail_bill ON mhb.property_tax_detail(tax_bill_id);

-- ============================================================================
-- MHB.PROPERTY_TAX_PAYMENT - MHB property tax payment history
-- ============================================================================

CREATE TABLE IF NOT EXISTS mhb.property_tax_payment (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER NOT NULL REFERENCES mhb.property_tax_bill(id),
    
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    interest_amount NUMERIC(10,2) DEFAULT 0,
    penalty_amount NUMERIC(10,2) DEFAULT 0,
    total_payment NUMERIC(10,2) NOT NULL,
    
    receipt_number VARCHAR(50),
    payment_method VARCHAR(50),  -- 'check', 'online', 'escrow'
    paid_from VARCHAR(100),      -- 'escrow', 'direct', account code
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE mhb.property_tax_payment IS 'Payment history for property tax bills';
COMMENT ON COLUMN mhb.property_tax_payment.payment_method IS 'check, online, escrow, etc.';
COMMENT ON COLUMN mhb.property_tax_payment.paid_from IS 'Payment source: escrow, direct, or account code';

CREATE INDEX IF NOT EXISTS idx_mhb_tax_payment_bill ON mhb.property_tax_payment(tax_bill_id);
CREATE INDEX IF NOT EXISTS idx_mhb_tax_payment_date ON mhb.property_tax_payment(payment_date);

-- ============================================================================
-- TRIGGERS - PER schema
-- ============================================================================

CREATE OR REPLACE FUNCTION per.fn_update_tax_bill_on_payment()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the tax bill totals
    UPDATE per.property_tax_bill
    SET 
        total_paid = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM per.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        interest_paid = (
            SELECT COALESCE(SUM(interest_amount), 0) 
            FROM per.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        balance_due = total_due - (
            SELECT COALESCE(SUM(amount), 0) 
            FROM per.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        status = CASE 
            WHEN total_due <= (
                SELECT COALESCE(SUM(amount), 0) 
                FROM per.property_tax_payment 
                WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
            ) THEN 'paid'
            WHEN (
                SELECT COALESCE(SUM(amount), 0) 
                FROM per.property_tax_payment 
                WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
            ) > 0 THEN 'partial'
            ELSE 'unpaid'
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION per.fn_update_tax_bill_on_payment() IS 'Updates tax bill totals and status when payments are inserted, updated, or deleted';

CREATE TRIGGER trg_update_tax_bill_on_payment
    AFTER INSERT OR UPDATE OR DELETE ON per.property_tax_payment
    FOR EACH ROW
    EXECUTE FUNCTION per.fn_update_tax_bill_on_payment();

-- ============================================================================
-- TRIGGERS - MHB schema
-- ============================================================================

CREATE OR REPLACE FUNCTION mhb.fn_update_tax_bill_on_payment()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the tax bill totals
    UPDATE mhb.property_tax_bill
    SET 
        total_paid = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM mhb.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        interest_paid = (
            SELECT COALESCE(SUM(interest_amount), 0) 
            FROM mhb.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        balance_due = total_due - (
            SELECT COALESCE(SUM(amount), 0) 
            FROM mhb.property_tax_payment 
            WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
        ),
        status = CASE 
            WHEN total_due <= (
                SELECT COALESCE(SUM(amount), 0) 
                FROM mhb.property_tax_payment 
                WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
            ) THEN 'paid'
            WHEN (
                SELECT COALESCE(SUM(amount), 0) 
                FROM mhb.property_tax_payment 
                WHERE tax_bill_id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id)
            ) > 0 THEN 'partial'
            ELSE 'unpaid'
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.tax_bill_id, OLD.tax_bill_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mhb.fn_update_tax_bill_on_payment() IS 'Updates tax bill totals and status when payments are inserted, updated, or deleted';

CREATE TRIGGER trg_update_tax_bill_on_payment
    AFTER INSERT OR UPDATE OR DELETE ON mhb.property_tax_payment
    FOR EACH ROW
    EXECUTE FUNCTION mhb.fn_update_tax_bill_on_payment();

-- ============================================================================
-- VIEWS - PER schema
-- ============================================================================

-- Outstanding tax balances view
CREATE OR REPLACE VIEW per.v_property_tax_outstanding AS
SELECT 
    b.property_code,
    b.tax_year,
    b.tax_season,
    b.total_due,
    b.total_paid,
    b.balance_due,
    b.status,
    b.due_date,
    CASE 
        WHEN b.balance_due > 0 AND b.due_date < CURRENT_DATE THEN 'OVERDUE'
        WHEN b.balance_due > 0 THEN 'DUE'
        ELSE 'PAID'
    END as payment_status,
    CASE 
        WHEN b.due_date < CURRENT_DATE THEN CURRENT_DATE - b.due_date 
        ELSE 0 
    END as days_overdue
FROM per.property_tax_bill b
WHERE b.balance_due > 0 OR b.balance_due IS NULL
ORDER BY b.due_date, b.property_code;

COMMENT ON VIEW per.v_property_tax_outstanding IS 'Outstanding property tax balances with overdue status';

-- Tax history summary view
CREATE OR REPLACE VIEW per.v_property_tax_history AS
SELECT 
    b.property_code,
    b.tax_year,
    SUM(CASE WHEN b.tax_season = 'summer' THEN b.total_due ELSE 0 END) as summer_tax,
    SUM(CASE WHEN b.tax_season = 'winter' THEN b.total_due ELSE 0 END) as winter_tax,
    SUM(b.total_due) as annual_tax,
    SUM(b.total_paid) as annual_paid,
    SUM(b.balance_due) as annual_balance,
    MAX(b.assessed_value) as assessed_value,
    MAX(b.taxable_value) as taxable_value
FROM per.property_tax_bill b
GROUP BY b.property_code, b.tax_year
ORDER BY b.property_code, b.tax_year DESC;

COMMENT ON VIEW per.v_property_tax_history IS 'Annual property tax history summary by property';

-- ============================================================================
-- VIEWS - MHB schema
-- ============================================================================

-- Outstanding tax balances view
CREATE OR REPLACE VIEW mhb.v_property_tax_outstanding AS
SELECT 
    b.property_code,
    b.tax_year,
    b.tax_season,
    b.total_due,
    b.total_paid,
    b.balance_due,
    b.status,
    b.due_date,
    CASE 
        WHEN b.balance_due > 0 AND b.due_date < CURRENT_DATE THEN 'OVERDUE'
        WHEN b.balance_due > 0 THEN 'DUE'
        ELSE 'PAID'
    END as payment_status,
    CASE 
        WHEN b.due_date < CURRENT_DATE THEN CURRENT_DATE - b.due_date 
        ELSE 0 
    END as days_overdue
FROM mhb.property_tax_bill b
WHERE b.balance_due > 0 OR b.balance_due IS NULL
ORDER BY b.due_date, b.property_code;

COMMENT ON VIEW mhb.v_property_tax_outstanding IS 'Outstanding property tax balances with overdue status';

-- Tax history summary view
CREATE OR REPLACE VIEW mhb.v_property_tax_history AS
SELECT 
    b.property_code,
    b.tax_year,
    SUM(CASE WHEN b.tax_season = 'summer' THEN b.total_due ELSE 0 END) as summer_tax,
    SUM(CASE WHEN b.tax_season = 'winter' THEN b.total_due ELSE 0 END) as winter_tax,
    SUM(b.total_due) as annual_tax,
    SUM(b.total_paid) as annual_paid,
    SUM(b.balance_due) as annual_balance,
    MAX(b.assessed_value) as assessed_value,
    MAX(b.taxable_value) as taxable_value
FROM mhb.property_tax_bill b
GROUP BY b.property_code, b.tax_year
ORDER BY b.property_code, b.tax_year DESC;

COMMENT ON VIEW mhb.v_property_tax_history IS 'Annual property tax history summary by property';

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT ALL ON TABLE per.property_tax_bill TO frank;
GRANT ALL ON SEQUENCE per.property_tax_bill_id_seq TO frank;
GRANT ALL ON TABLE per.property_tax_detail TO frank;
GRANT ALL ON SEQUENCE per.property_tax_detail_id_seq TO frank;
GRANT ALL ON TABLE per.property_tax_payment TO frank;
GRANT ALL ON SEQUENCE per.property_tax_payment_id_seq TO frank;

GRANT ALL ON TABLE mhb.property_tax_bill TO frank;
GRANT ALL ON SEQUENCE mhb.property_tax_bill_id_seq TO frank;
GRANT ALL ON TABLE mhb.property_tax_detail TO frank;
GRANT ALL ON SEQUENCE mhb.property_tax_detail_id_seq TO frank;
GRANT ALL ON TABLE mhb.property_tax_payment TO frank;
GRANT ALL ON SEQUENCE mhb.property_tax_payment_id_seq TO frank;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
