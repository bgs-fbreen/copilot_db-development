-- ============================================================================
-- Copilot Accounting System - BGS Schema
-- Module: BGS (Breen GeoScience Consulting)
-- Created: 2025-11-06
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS bgs;

-- ============================================================================
-- CLIENTS
-- ============================================================================

CREATE TABLE bgs.client (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- tbls, textin, olg, etc.
    name VARCHAR(200) NOT NULL,                 -- "TBLS Engineers"
    contact_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',        -- active, inactive
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.client IS 'BGS consulting clients';
COMMENT ON COLUMN bgs.client.code IS 'Client code used in project numbers (e.g., tbls)';

-- ============================================================================
-- PROJECTS
-- ============================================================================

CREATE TABLE bgs.project (
    project_code VARCHAR(50) PRIMARY KEY,       -- tbls.25.1904
    client_code VARCHAR(50) NOT NULL REFERENCES bgs.client(code),
    project_year INTEGER NOT NULL,              -- 2025 (from 25)
    project_number INTEGER NOT NULL,            -- 1904
    title VARCHAR(500) NOT NULL,
    description TEXT,
    project_type VARCHAR(50),                   -- consulting, fieldwork, report
    status VARCHAR(50) DEFAULT 'active',        -- active, on-hold, completed, invoiced, closed
    start_date DATE,
    end_date DATE,
    budget_hours NUMERIC(10,2),
    budget_amount NUMERIC(12,2),
    hourly_rate NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.project IS 'BGS consulting projects';
COMMENT ON COLUMN bgs.project.project_code IS 'Format: CLIENT.YY.PROJNO (e.g., tbls.25.1904)';

CREATE INDEX idx_project_client ON bgs.project(client_code);
CREATE INDEX idx_project_status ON bgs.project(status);
CREATE INDEX idx_project_year ON bgs.project(project_year);

-- ============================================================================
-- INVOICES
-- ============================================================================

CREATE TABLE bgs.invoice (
    invoice_code VARCHAR(100) PRIMARY KEY,      -- tbls.25.1904.0001
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    invoice_number INTEGER NOT NULL,            -- 0001, 0002, etc.
    invoice_date DATE NOT NULL,
    due_date DATE,
    amount NUMERIC(12,2) NOT NULL,
    paid_amount NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'draft',         -- draft, sent, partial, paid, overdue, cancelled
    payment_date DATE,
    payment_method VARCHAR(50),                 -- check, ach, wire, credit_card
    check_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.invoice IS 'BGS consulting invoices';
COMMENT ON COLUMN bgs.invoice.invoice_code IS 'Format: CLIENT.YY.PROJNO.INVNO (e.g., tbls.25.1904.0001)';

CREATE INDEX idx_invoice_project ON bgs.invoice(project_code);
CREATE INDEX idx_invoice_status ON bgs.invoice(status);
CREATE INDEX idx_invoice_date ON bgs.invoice(invoice_date);
CREATE INDEX idx_invoice_payment ON bgs.invoice(payment_date);

-- ============================================================================
-- INVOICE ITEMS (Line items on invoices)
-- ============================================================================

CREATE TABLE bgs.invoice_item (
    id SERIAL PRIMARY KEY,
    invoice_code VARCHAR(100) NOT NULL REFERENCES bgs.invoice(invoice_code),
    line_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC(10,2),
    unit_price NUMERIC(10,2),
    amount NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.invoice_item IS 'Line items for BGS invoices';

CREATE INDEX idx_invoice_item_invoice ON bgs.invoice_item(invoice_code);

-- ============================================================================
-- TIMESHEETS
-- ============================================================================

CREATE TABLE bgs.timesheet (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    work_date DATE NOT NULL,
    hours NUMERIC(5,2) NOT NULL,
    description TEXT,
    task_type VARCHAR(50),                      -- fieldwork, analysis, reporting, meeting
    billable BOOLEAN DEFAULT true,
    invoiced BOOLEAN DEFAULT false,
    invoice_code VARCHAR(100) REFERENCES bgs.invoice(invoice_code),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.timesheet IS 'Time tracking for BGS projects';

CREATE INDEX idx_timesheet_project ON bgs.timesheet(project_code);
CREATE INDEX idx_timesheet_date ON bgs.timesheet(work_date);
CREATE INDEX idx_timesheet_invoice ON bgs.timesheet(invoice_code);
CREATE INDEX idx_timesheet_billable ON bgs.timesheet(billable, invoiced);

-- ============================================================================
-- SUBCONTRACTORS
-- ============================================================================

CREATE TABLE bgs.subcontractor (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    address TEXT,
    tax_id VARCHAR(50),                         -- EIN or SSN
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.subcontractor IS 'Subcontractors used on BGS projects';

-- ============================================================================
-- SUBCONTRACTOR EXPENSES (AP for subs)
-- ============================================================================

CREATE TABLE bgs.subcontractor_expense (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    subcontractor_id INTEGER NOT NULL REFERENCES bgs.subcontractor(id),
    expense_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    description TEXT,
    invoice_number VARCHAR(100),
    paid BOOLEAN DEFAULT false,
    payment_date DATE,
    check_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.subcontractor_expense IS 'Subcontractor expenses (accounts payable)';

CREATE INDEX idx_subexp_project ON bgs.subcontractor_expense(project_code);
CREATE INDEX idx_subexp_sub ON bgs.subcontractor_expense(subcontractor_id);
CREATE INDEX idx_subexp_paid ON bgs.subcontractor_expense(paid);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Project summary with hours and invoicing
CREATE OR REPLACE VIEW bgs.vw_project_summary AS
SELECT 
    p.project_code,
    p.title,
    c.name as client_name,
    p.status,
    p.start_date,
    p.budget_hours,
    COALESCE(SUM(t.hours), 0) as hours_worked,
    p.budget_hours - COALESCE(SUM(t.hours), 0) as hours_remaining,
    COUNT(DISTINCT i.invoice_code) as invoice_count,
    COALESCE(SUM(i.amount), 0) as invoiced_total,
    COALESCE(SUM(i.paid_amount), 0) as paid_total
FROM bgs.project p
LEFT JOIN bgs.client c ON c.code = p.client_code
LEFT JOIN bgs.timesheet t ON t.project_code = p.project_code
LEFT JOIN bgs.invoice i ON i.project_code = p.project_code
GROUP BY p.project_code, p.title, c.name, p.status, p.start_date, p.budget_hours
ORDER BY p.project_code DESC;

-- Unbilled hours
CREATE OR REPLACE VIEW bgs.vw_unbilled_hours AS
SELECT 
    t.project_code,
    p.title,
    c.name as client_name,
    t.work_date,
    t.hours,
    t.description,
    p.hourly_rate,
    t.hours * p.hourly_rate as billable_amount
FROM bgs.timesheet t
JOIN bgs.project p ON p.project_code = t.project_code
JOIN bgs.client c ON c.code = p.client_code
WHERE t.billable = true 
  AND t.invoiced = false
ORDER BY t.work_date DESC;

-- Outstanding invoices (AR)
CREATE OR REPLACE VIEW bgs.vw_outstanding_invoices AS
SELECT 
    i.invoice_code,
    i.project_code,
    p.title,
    c.name as client_name,
    i.invoice_date,
    i.due_date,
    i.amount,
    i.paid_amount,
    i.amount - i.paid_amount as balance_due,
    CURRENT_DATE - i.due_date as days_overdue,
    i.status
FROM bgs.invoice i
JOIN bgs.project p ON p.project_code = i.project_code
JOIN bgs.client c ON c.code = p.client_code
WHERE i.status IN ('sent', 'partial', 'overdue')
  AND i.amount > i.paid_amount
ORDER BY i.due_date ASC;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON SCHEMA bgs TO frank;
GRANT ALL ON ALL TABLES IN SCHEMA bgs TO frank;
GRANT ALL ON ALL SEQUENCES IN SCHEMA bgs TO frank;
