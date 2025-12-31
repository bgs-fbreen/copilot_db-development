-- ============================================================================
-- Migration: Create Lease Tracking System
-- Created: 2025-12-31
-- Description: Creates comprehensive lease tracking system for rental properties
--              (905brown, 711pine, 819helen) including:
--              - Property and lease management
--              - Tenant and guarantor contact tracking
--              - Projected vs actual income and expense tracking
--              - Vacancy tracking and rent adjustments
--              - P&L comparison views with variance analysis
-- ============================================================================

-- ============================================================================
-- PROPERTIES - Base property information
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.properties (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) DEFAULT 'Pittsburgh',
    state VARCHAR(2) DEFAULT 'PA',
    zip_code VARCHAR(10),
    purchase_date DATE,
    purchase_price NUMERIC(12,2),
    mortgage_amount NUMERIC(12,2),
    mortgage_rate NUMERIC(5,4),
    mortgage_start_date DATE,
    mortgage_term_months INTEGER,
    notes TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.properties IS 'Base property information for rental properties';
COMMENT ON COLUMN acc.properties.property_code IS 'Unique code: 905brown, 711pine, 819helen';
COMMENT ON COLUMN acc.properties.mortgage_rate IS 'Annual interest rate as decimal (e.g., 0.0650 for 6.5%)';

CREATE INDEX IF NOT EXISTS idx_properties_code ON acc.properties(property_code);
CREATE INDEX IF NOT EXISTS idx_properties_active ON acc.properties(active);

-- ============================================================================
-- LEASES - Lease agreements with financial terms
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.leases (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    monthly_rent NUMERIC(10,2) NOT NULL,
    deposit_amount NUMERIC(10,2) DEFAULT 0,
    deposit_applies_to_last_month BOOLEAN DEFAULT false,
    utilities_included TEXT,
    pet_allowed BOOLEAN DEFAULT false,
    pet_deposit NUMERIC(10,2) DEFAULT 0,
    parking_included BOOLEAN DEFAULT false,
    parking_fee NUMERIC(10,2) DEFAULT 0,
    lease_type VARCHAR(50) DEFAULT 'fixed',
    notes TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_lease_dates CHECK (end_date > start_date),
    CONSTRAINT chk_monthly_rent CHECK (monthly_rent > 0),
    CONSTRAINT chk_lease_status CHECK (status IN ('active', 'expired', 'terminated', 'pending'))
);

COMMENT ON TABLE acc.leases IS 'Lease agreements with rental terms and deposit handling';
COMMENT ON COLUMN acc.leases.deposit_applies_to_last_month IS 'If true, deposit covers last month rent (common for student rentals)';
COMMENT ON COLUMN acc.leases.lease_type IS 'fixed, month-to-month, academic';
COMMENT ON COLUMN acc.leases.status IS 'active, expired, terminated, pending';

CREATE INDEX IF NOT EXISTS idx_leases_property ON acc.leases(property_id);
CREATE INDEX IF NOT EXISTS idx_leases_dates ON acc.leases(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_leases_status ON acc.leases(status);

-- ============================================================================
-- LEASE TENANTS - Tenant contact information
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.lease_tenants (
    id SERIAL PRIMARY KEY,
    lease_id INTEGER NOT NULL REFERENCES acc.leases(id) ON DELETE CASCADE,
    tenant_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    is_primary BOOLEAN DEFAULT false,
    is_student BOOLEAN DEFAULT false,
    school_name VARCHAR(255),
    graduation_date DATE,
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(50),
    emergency_contact_relationship VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.lease_tenants IS 'Tenant contact information including student details';
COMMENT ON COLUMN acc.lease_tenants.is_primary IS 'Primary contact for the lease';
COMMENT ON COLUMN acc.lease_tenants.is_student IS 'Student renter flag';

CREATE INDEX IF NOT EXISTS idx_lease_tenants_lease ON acc.lease_tenants(lease_id);
CREATE INDEX IF NOT EXISTS idx_lease_tenants_primary ON acc.lease_tenants(is_primary);

-- ============================================================================
-- LEASE GUARANTORS - Parent/guarantor contact information
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.lease_guarantors (
    id SERIAL PRIMARY KEY,
    lease_id INTEGER NOT NULL REFERENCES acc.leases(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES acc.lease_tenants(id) ON DELETE SET NULL,
    guarantor_name VARCHAR(255) NOT NULL,
    relationship VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.lease_guarantors IS 'Parent/guarantor contact information with full addresses';
COMMENT ON COLUMN acc.lease_guarantors.tenant_id IS 'Optional link to specific tenant if guarantor is for one tenant';
COMMENT ON COLUMN acc.lease_guarantors.relationship IS 'parent, spouse, other';

CREATE INDEX IF NOT EXISTS idx_lease_guarantors_lease ON acc.lease_guarantors(lease_id);
CREATE INDEX IF NOT EXISTS idx_lease_guarantors_tenant ON acc.lease_guarantors(tenant_id);

-- ============================================================================
-- PROPERTY EXPENSES - Projected recurring expenses
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.property_expenses (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    expense_type VARCHAR(50) NOT NULL,
    expense_name VARCHAR(255) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    frequency VARCHAR(20) DEFAULT 'annual',
    due_month INTEGER,
    notes TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_expense_type CHECK (expense_type IN ('summer_tax', 'winter_tax', 'insurance', 'hoa', 'maintenance', 'utilities', 'other')),
    CONSTRAINT chk_frequency CHECK (frequency IN ('monthly', 'quarterly', 'annual', 'one-time')),
    CONSTRAINT chk_due_month CHECK (due_month IS NULL OR (due_month >= 1 AND due_month <= 12))
);

COMMENT ON TABLE acc.property_expenses IS 'Projected recurring property expenses';
COMMENT ON COLUMN acc.property_expenses.expense_type IS 'summer_tax, winter_tax, insurance, hoa, maintenance, utilities, other';
COMMENT ON COLUMN acc.property_expenses.frequency IS 'monthly, quarterly, annual, one-time';
COMMENT ON COLUMN acc.property_expenses.due_month IS 'Month number (1-12) when annual/quarterly expense is due';

CREATE INDEX IF NOT EXISTS idx_property_expenses_property ON acc.property_expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_property_expenses_type ON acc.property_expenses(expense_type);
CREATE INDEX IF NOT EXISTS idx_property_expenses_active ON acc.property_expenses(active);

-- ============================================================================
-- RENT PAYMENTS - Actual rent payments received
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.rent_payments (
    id SERIAL PRIMARY KEY,
    lease_id INTEGER NOT NULL REFERENCES acc.leases(id),
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    for_month DATE NOT NULL,
    payment_method VARCHAR(50),
    payment_status VARCHAR(20) DEFAULT 'received',
    check_number VARCHAR(50),
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('received', 'bounced', 'partial', 'waived', 'pending'))
);

COMMENT ON TABLE acc.rent_payments IS 'Individual rent payments received with status tracking';
COMMENT ON COLUMN acc.rent_payments.for_month IS 'Month this payment applies to (first day of month)';
COMMENT ON COLUMN acc.rent_payments.payment_status IS 'received, bounced, partial, waived, pending';
COMMENT ON COLUMN acc.rent_payments.bank_staging_id IS 'Link to bank_staging for import';

CREATE INDEX IF NOT EXISTS idx_rent_payments_lease ON acc.rent_payments(lease_id);
CREATE INDEX IF NOT EXISTS idx_rent_payments_property ON acc.rent_payments(property_id);
CREATE INDEX IF NOT EXISTS idx_rent_payments_date ON acc.rent_payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_rent_payments_for_month ON acc.rent_payments(for_month);
CREATE INDEX IF NOT EXISTS idx_rent_payments_status ON acc.rent_payments(payment_status);

-- ============================================================================
-- PROPERTY ACTUAL EXPENSES - Actual expenses incurred
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.property_actual_expenses (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    expense_date DATE NOT NULL,
    expense_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    vendor VARCHAR(255),
    check_number VARCHAR(50),
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_actual_expense_type CHECK (expense_type IN ('summer_tax', 'winter_tax', 'insurance', 'hoa', 'repair', 'maintenance', 'utilities', 'mortgage', 'other'))
);

COMMENT ON TABLE acc.property_actual_expenses IS 'Actual property expenses incurred';
COMMENT ON COLUMN acc.property_actual_expenses.expense_type IS 'summer_tax, winter_tax, insurance, hoa, repair, maintenance, utilities, mortgage, other';
COMMENT ON COLUMN acc.property_actual_expenses.bank_staging_id IS 'Link to bank_staging for import';

CREATE INDEX IF NOT EXISTS idx_property_actual_expenses_property ON acc.property_actual_expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_property_actual_expenses_date ON acc.property_actual_expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_property_actual_expenses_type ON acc.property_actual_expenses(expense_type);

-- ============================================================================
-- PROPERTY VACANCY - Vacancy periods tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.property_vacancy (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    expected_monthly_rent NUMERIC(10,2) NOT NULL,
    reason VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_vacancy_dates CHECK (end_date > start_date)
);

COMMENT ON TABLE acc.property_vacancy IS 'Vacancy periods between leases with lost rent calculation';
COMMENT ON COLUMN acc.property_vacancy.expected_monthly_rent IS 'Rent that would have been collected if occupied';
COMMENT ON COLUMN acc.property_vacancy.reason IS 'between_leases, turnover, renovation, other';

CREATE INDEX IF NOT EXISTS idx_property_vacancy_property ON acc.property_vacancy(property_id);
CREATE INDEX IF NOT EXISTS idx_property_vacancy_dates ON acc.property_vacancy(start_date, end_date);

-- ============================================================================
-- RENT ADJUSTMENTS - Late fees, credits, and concessions
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.rent_adjustments (
    id SERIAL PRIMARY KEY,
    lease_id INTEGER NOT NULL REFERENCES acc.leases(id),
    property_id INTEGER NOT NULL REFERENCES acc.properties(id),
    adjustment_date DATE NOT NULL,
    adjustment_type VARCHAR(50) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    for_month DATE,
    description TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_adjustment_type CHECK (adjustment_type IN ('late_fee', 'credit', 'concession', 'damage', 'other'))
);

COMMENT ON TABLE acc.rent_adjustments IS 'Late fees, credits, concessions, and other rent adjustments';
COMMENT ON COLUMN acc.rent_adjustments.adjustment_type IS 'late_fee, credit, concession, damage, other';
COMMENT ON COLUMN acc.rent_adjustments.for_month IS 'Optional: Month this adjustment applies to';
COMMENT ON COLUMN acc.rent_adjustments.amount IS 'Positive for charges, negative for credits';

CREATE INDEX IF NOT EXISTS idx_rent_adjustments_lease ON acc.rent_adjustments(lease_id);
CREATE INDEX IF NOT EXISTS idx_rent_adjustments_property ON acc.rent_adjustments(property_id);
CREATE INDEX IF NOT EXISTS idx_rent_adjustments_date ON acc.rent_adjustments(adjustment_date);
CREATE INDEX IF NOT EXISTS idx_rent_adjustments_type ON acc.rent_adjustments(adjustment_type);

-- ============================================================================
-- VIEWS - Projected Rent Monthly
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_projected_rent_monthly AS
WITH RECURSIVE months AS (
    -- Generate all months from earliest lease to latest lease
    SELECT 
        DATE_TRUNC('month', MIN(start_date))::DATE as month_start
    FROM acc.leases
    UNION ALL
    SELECT 
        (month_start + INTERVAL '1 month')::DATE
    FROM months
    WHERE month_start < (SELECT DATE_TRUNC('month', MAX(end_date))::DATE FROM acc.leases)
)
SELECT 
    p.id as property_id,
    p.property_code,
    l.id as lease_id,
    m.month_start,
    EXTRACT(YEAR FROM m.month_start)::INTEGER as year,
    EXTRACT(MONTH FROM m.month_start)::INTEGER as month,
    l.monthly_rent as projected_rent,
    CASE 
        WHEN l.deposit_applies_to_last_month 
         AND m.month_start = DATE_TRUNC('month', l.end_date)::DATE 
        THEN l.monthly_rent - l.deposit_amount
        ELSE l.monthly_rent
    END as projected_rent_adjusted
FROM months m
CROSS JOIN acc.properties p
LEFT JOIN acc.leases l ON l.property_id = p.id
    AND m.month_start >= DATE_TRUNC('month', l.start_date)::DATE
    AND m.month_start <= DATE_TRUNC('month', l.end_date)::DATE
    AND l.status = 'active'
WHERE p.active = true
ORDER BY p.property_code, m.month_start;

COMMENT ON VIEW acc.v_projected_rent_monthly IS 'Monthly projected rental income by property and lease';

-- ============================================================================
-- VIEWS - Actual Rent Monthly
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_actual_rent_monthly AS
SELECT 
    p.id as property_id,
    p.property_code,
    rp.lease_id,
    DATE_TRUNC('month', rp.for_month)::DATE as month_start,
    EXTRACT(YEAR FROM rp.for_month)::INTEGER as year,
    EXTRACT(MONTH FROM rp.for_month)::INTEGER as month,
    SUM(CASE WHEN rp.payment_status = 'received' THEN rp.amount ELSE 0 END) as actual_rent_received,
    SUM(CASE WHEN rp.payment_status = 'bounced' THEN rp.amount ELSE 0 END) as bounced_checks,
    SUM(CASE WHEN rp.payment_status = 'waived' THEN rp.amount ELSE 0 END) as waived_rent,
    SUM(CASE WHEN rp.payment_status = 'partial' THEN rp.amount ELSE 0 END) as partial_payments,
    COUNT(*) as payment_count
FROM acc.properties p
JOIN acc.rent_payments rp ON rp.property_id = p.id
WHERE p.active = true
GROUP BY p.id, p.property_code, rp.lease_id, DATE_TRUNC('month', rp.for_month)::DATE,
    EXTRACT(YEAR FROM rp.for_month), EXTRACT(MONTH FROM rp.for_month)
ORDER BY p.property_code, month_start;

COMMENT ON VIEW acc.v_actual_rent_monthly IS 'Actual rent received by month with status breakdown';

-- ============================================================================
-- VIEWS - Vacancy Impact Monthly
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_vacancy_monthly AS
WITH RECURSIVE months AS (
    SELECT 
        DATE_TRUNC('month', MIN(start_date))::DATE as month_start
    FROM acc.property_vacancy
    UNION ALL
    SELECT 
        (month_start + INTERVAL '1 month')::DATE
    FROM months
    WHERE month_start < (SELECT DATE_TRUNC('month', MAX(end_date))::DATE FROM acc.property_vacancy)
)
SELECT 
    p.id as property_id,
    p.property_code,
    v.id as vacancy_id,
    m.month_start,
    EXTRACT(YEAR FROM m.month_start)::INTEGER as year,
    EXTRACT(MONTH FROM m.month_start)::INTEGER as month,
    -- Calculate days vacant in this month
    CASE 
        WHEN DATE_TRUNC('month', v.start_date)::DATE = m.month_start 
         AND DATE_TRUNC('month', v.end_date)::DATE = m.month_start
        THEN EXTRACT(DAY FROM v.end_date - v.start_date)::INTEGER + 1
        WHEN DATE_TRUNC('month', v.start_date)::DATE = m.month_start
        THEN EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - v.start_date)::INTEGER
        WHEN DATE_TRUNC('month', v.end_date)::DATE = m.month_start
        THEN EXTRACT(DAY FROM v.end_date - m.month_start)::INTEGER + 1
        ELSE EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - m.month_start)::INTEGER
    END as days_vacant,
    v.expected_monthly_rent,
    -- Calculate lost rent for this month
    ROUND(v.expected_monthly_rent * 
        CASE 
            WHEN DATE_TRUNC('month', v.start_date)::DATE = m.month_start 
             AND DATE_TRUNC('month', v.end_date)::DATE = m.month_start
            THEN (EXTRACT(DAY FROM v.end_date - v.start_date)::INTEGER + 1) / 
                 EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - m.month_start)::NUMERIC
            WHEN DATE_TRUNC('month', v.start_date)::DATE = m.month_start
            THEN EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - v.start_date)::INTEGER / 
                 EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - m.month_start)::NUMERIC
            WHEN DATE_TRUNC('month', v.end_date)::DATE = m.month_start
            THEN (EXTRACT(DAY FROM v.end_date - m.month_start)::INTEGER + 1) / 
                 EXTRACT(DAY FROM (m.month_start + INTERVAL '1 month')::DATE - m.month_start)::NUMERIC
            ELSE 1
        END, 2) as lost_rent
FROM months m
CROSS JOIN acc.properties p
LEFT JOIN acc.property_vacancy v ON v.property_id = p.id
    AND m.month_start >= DATE_TRUNC('month', v.start_date)::DATE
    AND m.month_start <= DATE_TRUNC('month', v.end_date)::DATE
WHERE p.active = true AND v.id IS NOT NULL
ORDER BY p.property_code, m.month_start;

COMMENT ON VIEW acc.v_vacancy_monthly IS 'Monthly vacancy impact with lost rent calculation';

-- ============================================================================
-- VIEWS - Adjustments Monthly
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_adjustments_monthly AS
SELECT 
    p.id as property_id,
    p.property_code,
    ra.lease_id,
    DATE_TRUNC('month', ra.adjustment_date)::DATE as month_start,
    EXTRACT(YEAR FROM ra.adjustment_date)::INTEGER as year,
    EXTRACT(MONTH FROM ra.adjustment_date)::INTEGER as month,
    SUM(CASE WHEN ra.adjustment_type = 'late_fee' THEN ra.amount ELSE 0 END) as late_fees,
    SUM(CASE WHEN ra.adjustment_type = 'credit' THEN ra.amount ELSE 0 END) as credits,
    SUM(CASE WHEN ra.adjustment_type = 'concession' THEN ra.amount ELSE 0 END) as concessions,
    SUM(CASE WHEN ra.adjustment_type = 'damage' THEN ra.amount ELSE 0 END) as damage_charges,
    SUM(ra.amount) as total_adjustments
FROM acc.properties p
JOIN acc.rent_adjustments ra ON ra.property_id = p.id
WHERE p.active = true
GROUP BY p.id, p.property_code, ra.lease_id, DATE_TRUNC('month', ra.adjustment_date)::DATE,
    EXTRACT(YEAR FROM ra.adjustment_date), EXTRACT(MONTH FROM ra.adjustment_date)
ORDER BY p.property_code, month_start;

COMMENT ON VIEW acc.v_adjustments_monthly IS 'Monthly rent adjustments by type';

-- ============================================================================
-- VIEWS - Property Monthly Comparison (Income)
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_property_monthly_comparison AS
WITH all_months AS (
    SELECT DISTINCT property_id, property_code, month_start, year, month
    FROM acc.v_projected_rent_monthly
),
projected_income AS (
    SELECT 
        property_id, 
        property_code, 
        month_start,
        year,
        month,
        SUM(projected_rent_adjusted) as projected_rent
    FROM acc.v_projected_rent_monthly
    GROUP BY property_id, property_code, month_start, year, month
),
actual_income AS (
    SELECT 
        property_id,
        property_code,
        month_start,
        year,
        month,
        COALESCE(SUM(actual_rent_received), 0) as actual_rent,
        COALESCE(SUM(bounced_checks), 0) as bounced_checks,
        COALESCE(SUM(waived_rent), 0) as waived_rent
    FROM acc.v_actual_rent_monthly
    GROUP BY property_id, property_code, month_start, year, month
),
vacancy_impact AS (
    SELECT 
        property_id,
        property_code,
        month_start,
        year,
        month,
        COALESCE(SUM(lost_rent), 0) as vacancy_loss
    FROM acc.v_vacancy_monthly
    GROUP BY property_id, property_code, month_start, year, month
),
adjustments AS (
    SELECT 
        property_id,
        property_code,
        month_start,
        year,
        month,
        COALESCE(SUM(total_adjustments), 0) as adjustments
    FROM acc.v_adjustments_monthly
    GROUP BY property_id, property_code, month_start, year, month
)
SELECT 
    am.property_id,
    am.property_code,
    am.month_start,
    am.year,
    am.month,
    COALESCE(pi.projected_rent, 0) as projected_rent,
    COALESCE(ai.actual_rent, 0) as actual_rent,
    COALESCE(ai.bounced_checks, 0) as bounced_checks,
    COALESCE(ai.waived_rent, 0) as waived_rent,
    COALESCE(vi.vacancy_loss, 0) as vacancy_loss,
    COALESCE(adj.adjustments, 0) as adjustments,
    COALESCE(ai.actual_rent, 0) + COALESCE(adj.adjustments, 0) as total_actual_income,
    COALESCE(pi.projected_rent, 0) - (COALESCE(ai.actual_rent, 0) + COALESCE(adj.adjustments, 0)) as income_variance
FROM all_months am
LEFT JOIN projected_income pi USING (property_id, property_code, month_start, year, month)
LEFT JOIN actual_income ai USING (property_id, property_code, month_start, year, month)
LEFT JOIN vacancy_impact vi USING (property_id, property_code, month_start, year, month)
LEFT JOIN adjustments adj USING (property_id, property_code, month_start, year, month)
ORDER BY am.property_code, am.month_start;

COMMENT ON VIEW acc.v_property_monthly_comparison IS 'Monthly comparison of projected vs actual income with variance analysis';

-- ============================================================================
-- VIEWS - Property P&L Comparison
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_property_pnl_comparison AS
WITH income_summary AS (
    SELECT 
        property_id,
        property_code,
        year,
        SUM(projected_rent) as total_projected_rent,
        SUM(actual_rent) as total_actual_rent,
        SUM(bounced_checks) as total_bounced,
        SUM(waived_rent) as total_waived,
        SUM(vacancy_loss) as total_vacancy_loss,
        SUM(adjustments) as total_adjustments,
        SUM(total_actual_income) as total_actual_income,
        SUM(income_variance) as total_income_variance
    FROM acc.v_property_monthly_comparison
    GROUP BY property_id, property_code, year
),
projected_expenses AS (
    SELECT 
        pe.property_id,
        p.property_code,
        EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER as year,
        SUM(pe.amount) as total_projected_expenses
    FROM acc.property_expenses pe
    JOIN acc.properties p ON p.id = pe.property_id
    WHERE pe.active = true
    GROUP BY pe.property_id, p.property_code
),
actual_expenses AS (
    SELECT 
        property_id,
        p.property_code,
        EXTRACT(YEAR FROM expense_date)::INTEGER as year,
        SUM(amount) as total_actual_expenses
    FROM acc.property_actual_expenses pae
    JOIN acc.properties p ON p.id = pae.property_id
    GROUP BY property_id, p.property_code, EXTRACT(YEAR FROM expense_date)
)
SELECT 
    is_data.property_id,
    is_data.property_code,
    is_data.year,
    -- Income
    is_data.total_projected_rent,
    is_data.total_actual_rent,
    is_data.total_adjustments,
    is_data.total_actual_income,
    is_data.total_vacancy_loss,
    is_data.total_bounced,
    is_data.total_waived,
    -- Expenses
    COALESCE(pe.total_projected_expenses, 0) as total_projected_expenses,
    COALESCE(ae.total_actual_expenses, 0) as total_actual_expenses,
    COALESCE(pe.total_projected_expenses, 0) - COALESCE(ae.total_actual_expenses, 0) as expense_variance,
    -- Net Income
    is_data.total_projected_rent - COALESCE(pe.total_projected_expenses, 0) as projected_net_income,
    is_data.total_actual_income - COALESCE(ae.total_actual_expenses, 0) as actual_net_income,
    (is_data.total_actual_income - COALESCE(ae.total_actual_expenses, 0)) - 
        (is_data.total_projected_rent - COALESCE(pe.total_projected_expenses, 0)) as net_income_variance
FROM income_summary is_data
LEFT JOIN projected_expenses pe ON pe.property_id = is_data.property_id AND pe.year = is_data.year
LEFT JOIN actual_expenses ae ON ae.property_id = is_data.property_id AND ae.year = is_data.year
ORDER BY is_data.property_code, is_data.year;

COMMENT ON VIEW acc.v_property_pnl_comparison IS 'Annual P&L comparison by property with variance analysis';

-- ============================================================================
-- VIEWS - Lease Details Summary
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_lease_details AS
SELECT 
    l.id as lease_id,
    p.property_code,
    p.address,
    l.start_date,
    l.end_date,
    l.monthly_rent,
    l.deposit_amount,
    l.deposit_applies_to_last_month,
    l.status as lease_status,
    l.lease_type,
    COUNT(DISTINCT lt.id) as tenant_count,
    COUNT(DISTINCT lg.id) as guarantor_count,
    STRING_AGG(DISTINCT lt.tenant_name, ', ' ORDER BY lt.tenant_name) as tenant_names,
    MAX(CASE WHEN lt.is_primary THEN lt.tenant_name END) as primary_tenant,
    MAX(CASE WHEN lt.is_primary THEN lt.email END) as primary_email,
    MAX(CASE WHEN lt.is_primary THEN lt.phone END) as primary_phone
FROM acc.leases l
JOIN acc.properties p ON p.id = l.property_id
LEFT JOIN acc.lease_tenants lt ON lt.lease_id = l.id
LEFT JOIN acc.lease_guarantors lg ON lg.lease_id = l.id
GROUP BY l.id, p.property_code, p.address, l.start_date, l.end_date, 
    l.monthly_rent, l.deposit_amount, l.deposit_applies_to_last_month, 
    l.status, l.lease_type
ORDER BY p.property_code, l.start_date DESC;

COMMENT ON VIEW acc.v_lease_details IS 'Lease summary with tenant information';

-- ============================================================================
-- VIEWS - Lease Contact Directory
-- ============================================================================

CREATE OR REPLACE VIEW acc.v_lease_contact_directory AS
SELECT 
    p.property_code,
    l.id as lease_id,
    l.start_date,
    l.end_date,
    l.status as lease_status,
    'tenant' as contact_type,
    lt.tenant_name as contact_name,
    lt.email,
    lt.phone,
    lt.is_primary,
    lt.is_student,
    lt.school_name,
    NULL as relationship,
    NULL as address_line1,
    NULL as city,
    NULL as state,
    NULL as zip_code
FROM acc.leases l
JOIN acc.properties p ON p.id = l.property_id
JOIN acc.lease_tenants lt ON lt.lease_id = l.id
WHERE l.status = 'active'

UNION ALL

SELECT 
    p.property_code,
    l.id as lease_id,
    l.start_date,
    l.end_date,
    l.status as lease_status,
    'guarantor' as contact_type,
    lg.guarantor_name as contact_name,
    lg.email,
    lg.phone,
    false as is_primary,
    false as is_student,
    NULL as school_name,
    lg.relationship,
    lg.address_line1,
    lg.city,
    lg.state,
    lg.zip_code
FROM acc.leases l
JOIN acc.properties p ON p.id = l.property_id
JOIN acc.lease_guarantors lg ON lg.lease_id = l.id
WHERE l.status = 'active'

ORDER BY property_code, lease_id, contact_type, is_primary DESC, contact_name;

COMMENT ON VIEW acc.v_lease_contact_directory IS 'Complete contact directory for active leases';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
