-- ============================================================================
-- Copilot Accounting System - Core Schema
-- Module: ACC (Core Accounting)
-- Created: 2025-11-06
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS acc;

-- ============================================================================
-- BANK ACCOUNTS
-- ============================================================================

CREATE TABLE acc.bank_account (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    institution VARCHAR(200),
    account_number VARCHAR(50),
    opening_balance NUMERIC(12,2) DEFAULT 0,
    opening_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.bank_account IS 'Bank accounts across all entities';

-- ============================================================================
-- CHART OF ACCOUNTS / CATEGORIES
-- ============================================================================

CREATE TABLE acc.category (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    parent_id INTEGER REFERENCES acc.category(id),
    account_type VARCHAR(50) NOT NULL,
    entity VARCHAR(50),
    is_taxable BOOLEAN DEFAULT true,
    description TEXT,
    sort_order INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.category IS 'Chart of accounts - hierarchical category structure';

CREATE INDEX idx_category_parent ON acc.category(parent_id);
CREATE INDEX idx_category_entity ON acc.category(entity);
CREATE INDEX idx_category_type ON acc.category(account_type);

-- ============================================================================
-- TRANSACTIONS
-- ============================================================================

CREATE TABLE acc.transaction (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) NOT NULL REFERENCES acc.bank_account(code),
    trans_date DATE NOT NULL,
    post_date DATE,
    payee TEXT,
    memo TEXT,
    amount NUMERIC(12,2) NOT NULL,
    category_id INTEGER REFERENCES acc.category(id),
    allocation VARCHAR(500),
    entity VARCHAR(50),
    project_code VARCHAR(50),
    invoice_code VARCHAR(100),
    property_code VARCHAR(50),
    reconciled BOOLEAN DEFAULT false,
    source VARCHAR(50) DEFAULT 'manual',
    import_id VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.transaction IS 'All bank transactions across all accounts';
COMMENT ON COLUMN acc.transaction.amount IS 'Positive = income/deposit, Negative = expense/payment';
COMMENT ON COLUMN acc.transaction.project_code IS 'Format: CLIENT.YY.PROJNO (e.g., tbls.25.1904)';
COMMENT ON COLUMN acc.transaction.invoice_code IS 'Format: CLIENT.YY.PROJNO.INVNO (e.g., tbls.25.1904.0001)';
COMMENT ON COLUMN acc.transaction.allocation IS 'Legacy allocation string from old system';

CREATE INDEX idx_trans_account ON acc.transaction(account_code);
CREATE INDEX idx_trans_date ON acc.transaction(trans_date);
CREATE INDEX idx_trans_category ON acc.transaction(category_id);
CREATE INDEX idx_trans_entity ON acc.transaction(entity);
CREATE INDEX idx_trans_project ON acc.transaction(project_code);
CREATE INDEX idx_trans_invoice ON acc.transaction(invoice_code);
CREATE INDEX idx_trans_reconciled ON acc.transaction(reconciled);
CREATE INDEX idx_trans_import ON acc.transaction(import_id);

-- ============================================================================
-- IMPORT LOG
-- ============================================================================

CREATE TABLE acc.import_log (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) NOT NULL REFERENCES acc.bank_account(code),
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name VARCHAR(500),
    file_hash VARCHAR(64),
    records_imported INTEGER,
    records_skipped INTEGER,
    date_range_start DATE,
    date_range_end DATE,
    notes TEXT
);

COMMENT ON TABLE acc.import_log IS 'Track bank statement imports to prevent duplicates';

CREATE INDEX idx_import_hash ON acc.import_log(file_hash);

-- ============================================================================
-- PAYEE ALIASES
-- ============================================================================

CREATE TABLE acc.payee_alias (
    id SERIAL PRIMARY KEY,
    payee_pattern TEXT NOT NULL,
    normalized_name VARCHAR(200) NOT NULL,
    default_category_id INTEGER REFERENCES acc.category(id),
    entity VARCHAR(50),
    confidence INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.payee_alias IS 'Payee name patterns for auto-categorization';

CREATE INDEX idx_payee_pattern ON acc.payee_alias(payee_pattern);

-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW acc.vw_account_balance AS
SELECT 
    ba.code,
    ba.name,
    ba.account_type,
    ba.opening_balance,
    COALESCE(SUM(t.amount), 0) as total_transactions,
    ba.opening_balance + COALESCE(SUM(t.amount), 0) as current_balance,
    MAX(t.trans_date) as last_transaction_date
FROM acc.bank_account ba
LEFT JOIN acc.transaction t ON t.account_code = ba.code
WHERE ba.status = 'active'
GROUP BY ba.code, ba.name, ba.account_type, ba.opening_balance
ORDER BY ba.code;

CREATE OR REPLACE VIEW acc.vw_uncategorized AS
SELECT 
    id,
    account_code,
    trans_date,
    payee,
    amount,
    memo,
    allocation
FROM acc.transaction
WHERE category_id IS NULL
  AND reconciled = false
ORDER BY trans_date DESC;

CREATE OR REPLACE VIEW acc.vw_monthly_summary AS
SELECT 
    DATE_TRUNC('month', trans_date)::DATE as month,
    c.name as category,
    c.account_type,
    entity,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount
FROM acc.transaction t
LEFT JOIN acc.category c ON c.id = t.category_id
GROUP BY DATE_TRUNC('month', trans_date), c.name, c.account_type, entity
ORDER BY month DESC, total_amount DESC;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON SCHEMA acc TO frank;
GRANT ALL ON ALL TABLES IN SCHEMA acc TO frank;
GRANT ALL ON ALL SEQUENCES IN SCHEMA acc TO frank;
