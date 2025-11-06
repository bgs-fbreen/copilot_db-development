-- ============================================================================
-- Copilot Accounting System - MHB Schema
-- Module: MHB (Rental Properties)
-- Created: 2025-11-06
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS mhb;

-- ============================================================================
-- PROPERTIES
-- ============================================================================

CREATE TABLE mhb.property (
    code VARCHAR(50) PRIMARY KEY,               -- 711pine, 905brown, 819helen
    address VARCHAR(200) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(20),
    property_type VARCHAR(50),                  -- single_family, duplex, apartment
    purchase_date DATE,
    purchase_price NUMERIC(12,2),
    current_value NUMERIC(12,2),
    status VARCHAR(20) DEFAULT 'active',        -- active, sold, inactive
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.property IS 'MHB rental properties';

-- ============================================================================
-- TENANTS
-- ============================================================================

CREATE TABLE mhb.tenant (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(200),
    phone VARCHAR(50),
    emergency_contact VARCHAR(200),
    emergency_phone VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.tenant IS 'Tenants across all MHB properties';

-- ============================================================================
-- LEASES
-- ============================================================================

CREATE TABLE mhb.lease (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    tenant_id INTEGER NOT NULL REFERENCES mhb.tenant(id),
    lease_start DATE NOT NULL,
    lease_end DATE,
    monthly_rent NUMERIC(10,2) NOT NULL,
    security_deposit NUMERIC(10,2),
    deposit_returned BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active',        -- active, expired, terminated
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.lease IS 'Rental leases for MHB properties';

CREATE INDEX idx_lease_property ON mhb.lease(property_code);
CREATE INDEX idx_lease_tenant ON mhb.lease(tenant_id);
CREATE INDEX idx_lease_status ON mhb.lease(status);

-- ============================================================================
-- RENT PAYMENTS
-- ============================================================================

CREATE TABLE mhb.rent_payment (
    id SERIAL PRIMARY KEY,
    lease_id INTEGER NOT NULL REFERENCES mhb.lease(id),
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    payment_date DATE NOT NULL,
    period_start DATE NOT NULL,                 -- rent period start
    period_end DATE NOT NULL,                   -- rent period end
    amount NUMERIC(10,2) NOT NULL,
    payment_method VARCHAR(50),                 -- check, cash, ach, venmo
    reference_number VARCHAR(100),              -- check number, transaction ID
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.rent_payment IS 'Rent payments received from tenants';

CREATE INDEX idx_rent_lease ON mhb.rent_payment(lease_id);
CREATE INDEX idx_rent_property ON mhb.rent_payment(property_code);
CREATE INDEX idx_rent_date ON mhb.rent_payment(payment_date);

-- ============================================================================
-- MORTGAGES
-- ============================================================================

CREATE TABLE mhb.mortgage (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    lender VARCHAR(200) NOT NULL,
    loan_number VARCHAR(100),
    original_amount NUMERIC(12,2) NOT NULL,
    current_balance NUMERIC(12,2),
    interest_rate NUMERIC(5,3),
    monthly_payment NUMERIC(10,2),
    start_date DATE,
    maturity_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.mortgage IS 'Mortgages on MHB properties';

CREATE INDEX idx_mortgage_property ON mhb.mortgage(property_code);

-- ============================================================================
-- PROPERTY EXPENSES
-- ============================================================================

CREATE TABLE mhb.property_expense (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    expense_date DATE NOT NULL,
    expense_type VARCHAR(100),                  -- maintenance, repair, tax, insurance, utility
    vendor VARCHAR(200),
    amount NUMERIC(10,2) NOT NULL,
    description TEXT,
    paid BOOLEAN DEFAULT false,
    payment_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.property_expense IS 'Expenses for MHB properties';

CREATE INDEX idx_propexp_property ON mhb.property_expense(property_code);
CREATE INDEX idx_propexp_date ON mhb.property_expense(expense_date);
CREATE INDEX idx_propexp_type ON mhb.property_expense(expense_type);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Property summary with income/expenses
CREATE OR REPLACE VIEW mhb.vw_property_summary AS
SELECT 
    p.code,
    p.address,
    p.status,
    COUNT(DISTINCT l.id) as lease_count,
    COUNT(DISTINCT CASE WHEN l.status = 'active' THEN l.id END) as active_leases,
    COALESCE(MAX(l.monthly_rent), 0) as current_rent,
    COALESCE(SUM(rp.amount), 0) as total_rent_received,
    COALESCE(SUM(pe.amount), 0) as total_expenses,
    COALESCE(SUM(rp.amount), 0) - COALESCE(SUM(pe.amount), 0) as net_income
FROM mhb.property p
LEFT JOIN mhb.lease l ON l.property_code = p.code
LEFT JOIN mhb.rent_payment rp ON rp.property_code = p.code
LEFT JOIN mhb.property_expense pe ON pe.property_code = p.code
GROUP BY p.code, p.address, p.status
ORDER BY p.code;

-- Active leases
CREATE OR REPLACE VIEW mhb.vw_active_leases AS
SELECT 
    l.id as lease_id,
    p.code as property_code,
    p.address,
    t.first_name || ' ' || t.last_name as tenant_name,
    t.phone,
    t.email,
    l.lease_start,
    l.lease_end,
    l.monthly_rent,
    l.security_deposit
FROM mhb.lease l
JOIN mhb.property p ON p.code = l.property_code
JOIN mhb.tenant t ON t.id = l.tenant_id
WHERE l.status = 'active'
ORDER BY p.code;

-- Rent roll (expected vs received)
CREATE OR REPLACE VIEW mhb.vw_rent_roll AS
SELECT 
    DATE_TRUNC('month', generate_series)::DATE as month,
    p.code as property_code,
    p.address,
    l.monthly_rent as expected_rent,
    COALESCE(SUM(rp.amount), 0) as received_rent,
    l.monthly_rent - COALESCE(SUM(rp.amount), 0) as shortfall
FROM generate_series(
    DATE_TRUNC('year', CURRENT_DATE),
    CURRENT_DATE,
    '1 month'::interval
) 
CROSS JOIN mhb.property p
LEFT JOIN mhb.lease l ON l.property_code = p.code AND l.status = 'active'
LEFT JOIN mhb.rent_payment rp ON rp.property_code = p.code 
    AND DATE_TRUNC('month', rp.payment_date) = DATE_TRUNC('month', generate_series)
WHERE p.status = 'active'
GROUP BY DATE_TRUNC('month', generate_series), p.code, p.address, l.monthly_rent
ORDER BY month DESC, p.code;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON SCHEMA mhb TO frank;
GRANT ALL ON ALL TABLES IN SCHEMA mhb TO frank;
GRANT ALL ON ALL SEQUENCES IN SCHEMA mhb TO frank;
