-- ============================================================================
-- Migration: Entity Schema Reorganization & Mortgage/Property Management
-- Created: 2026-01-02
-- Description: Reorganizes database schemas to support entity separation
--              (MHB LLC, BGS Consulting, Personal) with shared accounting
--              infrastructure, and implements comprehensive mortgage and
--              property investment management tools.
-- ============================================================================

-- ============================================================================
-- PART 1: CREATE PERSONAL (PER) SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS per;

COMMENT ON SCHEMA per IS 'Personal finances schema - residence, personal mortgage, expenses';

-- ============================================================================
-- PER.RESIDENCE - Personal residence information
-- ============================================================================

CREATE TABLE per.residence (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) DEFAULT 'Sault Ste. Marie',
    state VARCHAR(2) DEFAULT 'MI',
    zip_code VARCHAR(10) DEFAULT '49783',
    purchase_date DATE,
    purchase_price NUMERIC(12,2),
    current_value NUMERIC(12,2),
    square_feet INTEGER,
    bedrooms INTEGER,
    bathrooms NUMERIC(3,1),
    lot_size_sqft INTEGER,
    year_built INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.residence IS 'Personal residence property details';
COMMENT ON COLUMN per.residence.property_code IS 'Unique code (e.g., parnell)';

CREATE INDEX idx_per_residence_code ON per.residence(property_code);

-- ============================================================================
-- PER.MORTGAGE - Personal mortgage details
-- ============================================================================

CREATE TABLE per.mortgage (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) REFERENCES per.residence(property_code),
    gl_account_code VARCHAR(100) NOT NULL,
    lender VARCHAR(200) NOT NULL,
    loan_number VARCHAR(100),
    issued_on DATE NOT NULL,
    original_balance NUMERIC(12,2) NOT NULL,
    current_balance NUMERIC(12,2) NOT NULL,
    interest_rate NUMERIC(6,3) NOT NULL,
    monthly_payment NUMERIC(10,2),
    matures_on DATE NOT NULL,
    escrow_included BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.mortgage IS 'Personal mortgage loans';
COMMENT ON COLUMN per.mortgage.gl_account_code IS 'GL account code (e.g., per:mortgage:parnell)';
COMMENT ON COLUMN per.mortgage.current_balance IS 'Current principal balance';
COMMENT ON COLUMN per.mortgage.interest_rate IS 'Annual interest rate as percentage (e.g., 3.750)';
COMMENT ON COLUMN per.mortgage.escrow_included IS 'Whether payment includes escrow for taxes/insurance';

CREATE INDEX idx_per_mortgage_property ON per.mortgage(property_code);
CREATE INDEX idx_per_mortgage_gl ON per.mortgage(gl_account_code);
CREATE INDEX idx_per_mortgage_status ON per.mortgage(status);

-- ============================================================================
-- PER.MORTGAGE_PAYMENT - Payment history with principal/interest split
-- ============================================================================

CREATE TABLE per.mortgage_payment (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES per.mortgage(id),
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    escrow NUMERIC(10,2) DEFAULT 0,
    balance_after NUMERIC(12,2) NOT NULL,
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.mortgage_payment IS 'Personal mortgage payment history with P&I split';
COMMENT ON COLUMN per.mortgage_payment.principal IS 'Principal portion of payment';
COMMENT ON COLUMN per.mortgage_payment.interest IS 'Interest portion of payment';
COMMENT ON COLUMN per.mortgage_payment.escrow IS 'Escrow portion if applicable';
COMMENT ON COLUMN per.mortgage_payment.balance_after IS 'Principal balance after this payment';

CREATE INDEX idx_per_payment_mortgage ON per.mortgage_payment(mortgage_id);
CREATE INDEX idx_per_payment_date ON per.mortgage_payment(payment_date);
CREATE INDEX idx_per_payment_staging ON per.mortgage_payment(bank_staging_id);

-- ============================================================================
-- PER.MORTGAGE_ESCROW - Escrow tracking for taxes and insurance
-- ============================================================================

CREATE TABLE per.mortgage_escrow (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES per.mortgage(id),
    disbursement_date DATE NOT NULL,
    expense_type VARCHAR(50) NOT NULL,
    payee VARCHAR(200) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.mortgage_escrow IS 'Escrow disbursements for taxes and insurance';
COMMENT ON COLUMN per.mortgage_escrow.expense_type IS 'property_tax, homeowners_insurance, flood_insurance, pmi, etc.';

CREATE INDEX idx_per_escrow_mortgage ON per.mortgage_escrow(mortgage_id);
CREATE INDEX idx_per_escrow_date ON per.mortgage_escrow(disbursement_date);
CREATE INDEX idx_per_escrow_type ON per.mortgage_escrow(expense_type);

-- ============================================================================
-- PER.MORTGAGE_PROJECTION - Amortization schedule
-- ============================================================================

CREATE TABLE per.mortgage_projection (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES per.mortgage(id),
    projection_date TIMESTAMP NOT NULL,
    payment_number INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    balance_after NUMERIC(12,2) NOT NULL,
    cumulative_interest NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE per.mortgage_projection IS 'Projected amortization schedule for personal mortgages';
COMMENT ON COLUMN per.mortgage_projection.projection_date IS 'When this projection was calculated';
COMMENT ON COLUMN per.mortgage_projection.payment_number IS 'Sequential payment number (1, 2, 3...)';
COMMENT ON COLUMN per.mortgage_projection.cumulative_interest IS 'Total interest paid through this payment';

CREATE INDEX idx_per_projection_mortgage ON per.mortgage_projection(mortgage_id);
CREATE INDEX idx_per_projection_date ON per.mortgage_projection(payment_date);
CREATE UNIQUE INDEX idx_per_projection_unique ON per.mortgage_projection(mortgage_id, projection_date, payment_number);

-- ============================================================================
-- PART 2: ENHANCE MHB SCHEMA - Add mortgage and property management tables
-- ============================================================================

-- Add gl_account_code column to existing mhb.mortgage table
ALTER TABLE mhb.mortgage ADD COLUMN IF NOT EXISTS gl_account_code VARCHAR(100);

COMMENT ON COLUMN mhb.mortgage.gl_account_code IS 'GL account code (e.g., mhb:mortgage:711pine)';

CREATE INDEX IF NOT EXISTS idx_mortgage_gl ON mhb.mortgage(gl_account_code);

-- ============================================================================
-- MHB.MORTGAGE_PAYMENT - Payment history with principal/interest split
-- ============================================================================

CREATE TABLE mhb.mortgage_payment (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES mhb.mortgage(id),
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    escrow NUMERIC(10,2) DEFAULT 0,
    balance_after NUMERIC(12,2) NOT NULL,
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.mortgage_payment IS 'MHB mortgage payment history with P&I split';
COMMENT ON COLUMN mhb.mortgage_payment.principal IS 'Principal portion of payment';
COMMENT ON COLUMN mhb.mortgage_payment.interest IS 'Interest portion of payment';
COMMENT ON COLUMN mhb.mortgage_payment.escrow IS 'Escrow portion if applicable';
COMMENT ON COLUMN mhb.mortgage_payment.balance_after IS 'Principal balance after this payment';

CREATE INDEX idx_mhb_payment_mortgage ON mhb.mortgage_payment(mortgage_id);
CREATE INDEX idx_mhb_payment_date ON mhb.mortgage_payment(payment_date);
CREATE INDEX idx_mhb_payment_staging ON mhb.mortgage_payment(bank_staging_id);

-- ============================================================================
-- MHB.MORTGAGE_PROJECTION - Amortization schedule
-- ============================================================================

CREATE TABLE mhb.mortgage_projection (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES mhb.mortgage(id),
    projection_date TIMESTAMP NOT NULL,
    payment_number INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    balance_after NUMERIC(12,2) NOT NULL,
    cumulative_interest NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.mortgage_projection IS 'Projected amortization schedule for MHB mortgages';
COMMENT ON COLUMN mhb.mortgage_projection.projection_date IS 'When this projection was calculated';
COMMENT ON COLUMN mhb.mortgage_projection.payment_number IS 'Sequential payment number (1, 2, 3...)';
COMMENT ON COLUMN mhb.mortgage_projection.cumulative_interest IS 'Total interest paid through this payment';

CREATE INDEX idx_mhb_projection_mortgage ON mhb.mortgage_projection(mortgage_id);
CREATE INDEX idx_mhb_projection_date ON mhb.mortgage_projection(payment_date);
CREATE UNIQUE INDEX idx_mhb_projection_unique ON mhb.mortgage_projection(mortgage_id, projection_date, payment_number);

-- ============================================================================
-- MHB.MORTGAGE_ESCROW - Escrow tracking for taxes and insurance
-- ============================================================================

CREATE TABLE mhb.mortgage_escrow (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER NOT NULL REFERENCES mhb.mortgage(id),
    disbursement_date DATE NOT NULL,
    expense_type VARCHAR(50) NOT NULL,
    payee VARCHAR(200) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.mortgage_escrow IS 'Escrow disbursements for taxes and insurance';
COMMENT ON COLUMN mhb.mortgage_escrow.expense_type IS 'property_tax, property_insurance, flood_insurance, etc.';

CREATE INDEX idx_mhb_escrow_mortgage ON mhb.mortgage_escrow(mortgage_id);
CREATE INDEX idx_mhb_escrow_date ON mhb.mortgage_escrow(disbursement_date);
CREATE INDEX idx_mhb_escrow_type ON mhb.mortgage_escrow(expense_type);

-- ============================================================================
-- MHB.PROPERTY_VALUATION - Property value tracking over time
-- ============================================================================

CREATE TABLE mhb.property_valuation (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    valuation_date DATE NOT NULL,
    valuation_type VARCHAR(50) NOT NULL,
    value NUMERIC(12,2) NOT NULL,
    source VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.property_valuation IS 'Property value assessments over time';
COMMENT ON COLUMN mhb.property_valuation.valuation_type IS 'assessed, appraised, market, zillow, etc.';
COMMENT ON COLUMN mhb.property_valuation.source IS 'Source of valuation (e.g., County Assessor, Zillow, Appraisal)';

CREATE INDEX idx_mhb_valuation_property ON mhb.property_valuation(property_code);
CREATE INDEX idx_mhb_valuation_date ON mhb.property_valuation(valuation_date);
CREATE INDEX idx_mhb_valuation_type ON mhb.property_valuation(valuation_type);

-- ============================================================================
-- MHB.PROPERTY_TAX - Property tax history by year
-- ============================================================================

CREATE TABLE mhb.property_tax (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    tax_year INTEGER NOT NULL,
    tax_period VARCHAR(20) NOT NULL,
    assessed_value NUMERIC(12,2),
    taxable_value NUMERIC(12,2),
    tax_amount NUMERIC(10,2) NOT NULL,
    due_date DATE,
    paid_date DATE,
    paid BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.property_tax IS 'Property tax history by year and period';
COMMENT ON COLUMN mhb.property_tax.tax_period IS 'summer, winter, annual, quarterly';
COMMENT ON COLUMN mhb.property_tax.assessed_value IS 'Full assessed value';
COMMENT ON COLUMN mhb.property_tax.taxable_value IS 'Taxable value (may differ from assessed)';

CREATE INDEX idx_mhb_tax_property ON mhb.property_tax(property_code);
CREATE INDEX idx_mhb_tax_year ON mhb.property_tax(tax_year);
CREATE INDEX idx_mhb_tax_period ON mhb.property_tax(tax_period);
CREATE INDEX idx_mhb_tax_paid ON mhb.property_tax(paid);

-- ============================================================================
-- MHB.MARKET_RENT_COMP - Market rent comparables for analysis
-- ============================================================================

CREATE TABLE mhb.market_rent_comp (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL REFERENCES mhb.property(code),
    comp_date DATE NOT NULL,
    comp_address VARCHAR(255),
    bedrooms INTEGER,
    bathrooms NUMERIC(3,1),
    square_feet INTEGER,
    monthly_rent NUMERIC(10,2) NOT NULL,
    distance_miles NUMERIC(4,2),
    source VARCHAR(100),
    url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mhb.market_rent_comp IS 'Comparable rental properties for market analysis';
COMMENT ON COLUMN mhb.market_rent_comp.source IS 'Zillow, Craigslist, Realtor.com, etc.';
COMMENT ON COLUMN mhb.market_rent_comp.distance_miles IS 'Distance from subject property';

CREATE INDEX idx_mhb_comp_property ON mhb.market_rent_comp(property_code);
CREATE INDEX idx_mhb_comp_date ON mhb.market_rent_comp(comp_date);

-- ============================================================================
-- PART 3: DATA MIGRATION - Move data from ACC to entity schemas
-- ============================================================================

-- Note: Migration assumes existing data structure.
-- Properties and mortgages data needs to be inserted based on problem statement.

-- Insert properties into MHB schema (if they exist in acc.properties)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'acc' AND table_name = 'properties') THEN
        -- Migrate MHB properties from acc.properties to mhb.property
        INSERT INTO mhb.property (code, address, city, state, zip, property_type, purchase_date, purchase_price, current_value, status, notes, created_at)
        SELECT 
            property_code,
            address,
            COALESCE(city, 'Sault Ste. Marie'),
            COALESCE(state, 'MI'),
            COALESCE(zip_code, '49783'),
            'rental',
            purchase_date,
            purchase_price,
            purchase_price,
            CASE WHEN active THEN 'active' ELSE 'inactive' END,
            notes,
            created_at
        FROM acc.properties
        WHERE property_code IN ('711pine', '819helen', '905brown')
        ON CONFLICT (code) DO NOTHING;
        
        RAISE NOTICE 'Migrated properties from acc.properties to mhb.property';
    END IF;
END $$;

-- Insert MHB mortgages (based on problem statement data)
DO $$
BEGIN
    -- Insert 711 Pine Street mortgage
    IF NOT EXISTS (SELECT 1 FROM mhb.mortgage WHERE property_code = '711pine') THEN
        INSERT INTO mhb.mortgage (property_code, gl_account_code, lender, original_balance, current_balance, interest_rate, issued_on, matures_on, status)
        VALUES (
            '711pine',
            'mhb:mortgage:711pine',
            'Central Savings Bank',
            66621.85,
            66621.85,
            8.500,
            '2020-04-14',
            '2040-04-17',
            'active'
        );
        RAISE NOTICE 'Inserted mortgage for 711pine';
    END IF;
    
    -- Insert 905 Brown Street mortgage
    IF NOT EXISTS (SELECT 1 FROM mhb.mortgage WHERE property_code = '905brown') THEN
        INSERT INTO mhb.mortgage (property_code, gl_account_code, lender, original_balance, current_balance, interest_rate, issued_on, matures_on, status)
        VALUES (
            '905brown',
            'mhb:mortgage:905brown',
            'Central Savings Bank',
            36620.00,
            36620.00,
            7.950,
            '2019-08-16',
            '2039-08-16',
            'active'
        );
        RAISE NOTICE 'Inserted mortgage for 905brown';
    END IF;
    
    -- Insert 819 Helen Street mortgage
    IF NOT EXISTS (SELECT 1 FROM mhb.mortgage WHERE property_code = '819helen') THEN
        INSERT INTO mhb.mortgage (property_code, gl_account_code, lender, original_balance, current_balance, interest_rate, issued_on, matures_on, status)
        VALUES (
            '819helen',
            'mhb:mortgage:819helen',
            'Central Savings Bank',
            67014.00,
            67014.00,
            8.250,
            '2021-03-19',
            '2041-03-19',
            'active'
        );
        RAISE NOTICE 'Inserted mortgage for 819helen';
    END IF;
    
    RAISE NOTICE 'Inserted MHB mortgage records';
END $$;

-- Insert personal residence
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM per.residence WHERE property_code = 'parnell') THEN
        INSERT INTO per.residence (property_code, address, city, state, zip_code, purchase_date, purchase_price)
        VALUES (
            'parnell',
            '1108 Parnell Street',
            'Sault Ste. Marie',
            'MI',
            '49783',
            '2015-01-16',
            180000.00
        );
        RAISE NOTICE 'Inserted residence for parnell';
    END IF;
END $$;

-- Insert personal mortgage
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM per.mortgage WHERE property_code = 'parnell') THEN
        INSERT INTO per.mortgage (property_code, gl_account_code, lender, issued_on, original_balance, current_balance, interest_rate, matures_on, status)
        VALUES (
            'parnell',
            'per:mortgage:parnell',
            'Central Savings Bank',
            '2015-01-16',
            180000.00,
            180000.00,
            3.750,
            '2045-02-01',
            'active'
        );
        RAISE NOTICE 'Inserted mortgage for parnell';
    END IF;
END $$;

-- ============================================================================
-- PART 4: DEPRECATION NOTICES
-- ============================================================================

-- Add deprecation comments to acc schema property/lease tables
COMMENT ON TABLE acc.properties IS 'DEPRECATED: Properties migrated to mhb.property (MHB) and per.residence (Personal). Keep for historical reference only.';
COMMENT ON TABLE acc.leases IS 'Lease data - Consider migrating to mhb schema in future for entity separation';

-- ============================================================================
-- PART 5: GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON SCHEMA per TO frank;
GRANT ALL ON ALL TABLES IN SCHEMA per TO frank;
GRANT ALL ON ALL SEQUENCES IN SCHEMA per TO frank;

GRANT ALL ON ALL TABLES IN SCHEMA mhb TO frank;
GRANT ALL ON ALL SEQUENCES IN SCHEMA mhb TO frank;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
