-- ============================================================================
-- Copilot Accounting System - BGS Schema (CORRECTED)
-- Module: BGS (Breen GeoScience Consulting)
-- Created: 2025-11-06
-- Matches db_accounts_old workflow with tasks, resources, baseline
-- ============================================================================

-- Drop existing tables to rebuild correctly
DROP SCHEMA IF EXISTS bgs CASCADE;
CREATE SCHEMA bgs;

-- ============================================================================
-- CLIENTS
-- ============================================================================

CREATE TABLE bgs.client (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- tbls, textin, olg, etc.
    name VARCHAR(200) NOT NULL,
    contact_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.client IS 'BGS consulting clients';

-- ============================================================================
-- PROJECTS
-- ============================================================================

CREATE TABLE bgs.project (
    project_code VARCHAR(50) PRIMARY KEY,       -- tbls.25.1904
    client_code VARCHAR(50) NOT NULL REFERENCES bgs.client(code),
    project_year INTEGER NOT NULL,              -- 2025
    project_number INTEGER NOT NULL,            -- 1904
    project_name VARCHAR(500),
    project_desc TEXT,
    client_po VARCHAR(100),
    project_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',        -- active, on-hold, completed, invoiced, closed
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.project IS 'BGS consulting projects';
COMMENT ON COLUMN bgs.project.project_code IS 'Format: CLIENT.YY.PROJNO (e.g., tbls.25.1904)';

CREATE INDEX idx_project_client ON bgs.project(client_code);
CREATE INDEX idx_project_status ON bgs.project(status);

-- ============================================================================
-- RESOURCES (You + Subcontractors)
-- ============================================================================

CREATE TABLE bgs.resource (
    id SERIAL PRIMARY KEY,
    res_id VARCHAR(50) UNIQUE NOT NULL,         -- F.Breen, microbac, geode
    res_name VARCHAR(200) NOT NULL,
    res_contact VARCHAR(200),
    res_street01 VARCHAR(200),
    res_street02 VARCHAR(200),
    res_city VARCHAR(100),
    res_state VARCHAR(2),
    res_zip VARCHAR(20),
    res_phone01 VARCHAR(50),
    res_phone02 VARCHAR(50),
    res_email VARCHAR(200),
    res_website VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.resource IS 'Resources: Frank Breen + subcontractors';
COMMENT ON COLUMN bgs.resource.res_id IS 'Resource identifier (e.g., F.Breen, microbac)';

-- ============================================================================
-- TASKS (Tasks and Subtasks for projects)
-- ============================================================================

CREATE TABLE bgs.task (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    task_no VARCHAR(50) NOT NULL,               -- T01, T02, T01:CH01
    task_name VARCHAR(500),
    task_notes TEXT,
    sub_task_no VARCHAR(50),                    -- S01, S02, or 'na'
    sub_task_name VARCHAR(500),
    task_co_no VARCHAR(50),                     -- CH01, CH02 (change orders)
    task_co_name VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_code, task_no, sub_task_no)
);

COMMENT ON TABLE bgs.task IS 'Tasks and subtasks for BGS projects';
COMMENT ON COLUMN bgs.task.task_no IS 'Task number (T01, T02, T01:CH01 for change orders)';
COMMENT ON COLUMN bgs.task.sub_task_no IS 'Subtask (S01, S02) or "na"';

CREATE INDEX idx_task_project ON bgs.task(project_code);

-- ============================================================================
-- BASELINE (Budget tracking with change orders)
-- ============================================================================

CREATE TABLE bgs.baseline (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    task_no VARCHAR(50) NOT NULL,               -- T01, T02, T01:CH01
    sub_task_no VARCHAR(50) NOT NULL,           -- S01 or 'na'
    res_id VARCHAR(50) NOT NULL REFERENCES bgs.resource(res_id),
    base_units NUMERIC(10,2),                   -- budgeted hours
    base_rate NUMERIC(10,2),                    -- billing rate
    base_miles NUMERIC(10,2),                   -- budgeted mileage
    base_expense NUMERIC(10,2),                 -- budgeted expenses
    base_miles_rate NUMERIC(10,2),              -- mileage rate ($/mile)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.baseline IS 'Project baseline - budget with change orders';
COMMENT ON COLUMN bgs.baseline.task_no IS 'Task (T01, T01:CH01 for change order 1)';

CREATE INDEX idx_baseline_project ON bgs.baseline(project_code);
CREATE INDEX idx_baseline_resource ON bgs.baseline(res_id);

-- ============================================================================
-- TIMESHEETS (Time entry matching your bash script)
-- ============================================================================

CREATE TABLE bgs.timesheet (
    id SERIAL PRIMARY KEY,
    yr_mon VARCHAR(4) NOT NULL,                 -- yymm (2511 = Nov 2025)
    project_code VARCHAR(50) NOT NULL REFERENCES bgs.project(project_code),
    task_no VARCHAR(50) NOT NULL,               -- T01, T02
    sub_task_no VARCHAR(50) NOT NULL,           -- S01 or 'na'
    ts_date DATE NOT NULL,
    res_id VARCHAR(50) NOT NULL REFERENCES bgs.resource(res_id),
    ts_units NUMERIC(10,2) NOT NULL,            -- hours worked
    ts_mileage NUMERIC(10,2) DEFAULT 0,
    ts_expense NUMERIC(10,2) DEFAULT 0,
    ts_desc TEXT,
    invoice_code VARCHAR(100),                  -- tbls.25.1904.0001
    task_co_no VARCHAR(50),                     -- change order if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.timesheet IS 'Time tracking for BGS projects';
COMMENT ON COLUMN bgs.timesheet.yr_mon IS 'Year-month (yymm format: 2511 = Nov 2025)';
COMMENT ON COLUMN bgs.timesheet.ts_units IS 'Hours worked';

CREATE INDEX idx_timesheet_project ON bgs.timesheet(project_code);
CREATE INDEX idx_timesheet_date ON bgs.timesheet(ts_date);
CREATE INDEX idx_timesheet_resource ON bgs.timesheet(res_id);
CREATE INDEX idx_timesheet_invoice ON bgs.timesheet(invoice_code);

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
    payment_method VARCHAR(50),
    check_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bgs.invoice IS 'BGS consulting invoices';

CREATE INDEX idx_invoice_project ON bgs.invoice(project_code);
CREATE INDEX idx_invoice_status ON bgs.invoice(status);

-- ============================================================================
-- INVOICE ITEMS
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

CREATE INDEX idx_invoice_item_invoice ON bgs.invoice_item(invoice_code);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Project utilization (baseline vs actual)
CREATE OR REPLACE VIEW bgs.vw_project_utilization AS
SELECT 
    b.project_code,
    p.project_name,
    b.task_no,
    b.sub_task_no,
    b.res_id,
    r.res_name,
    b.base_units as budgeted_hours,
    COALESCE(SUM(t.ts_units), 0) as actual_hours,
    b.base_units - COALESCE(SUM(t.ts_units), 0) as remaining_hours,
    b.base_rate,
    b.base_units * b.base_rate as budgeted_amount,
    COALESCE(SUM(t.ts_units), 0) * b.base_rate as actual_amount
FROM bgs.baseline b
JOIN bgs.project p ON p.project_code = b.project_code
JOIN bgs.resource r ON r.res_id = b.res_id
LEFT JOIN bgs.timesheet t ON t.project_code = b.project_code 
    AND t.task_no = b.task_no 
    AND t.sub_task_no = b.sub_task_no
    AND t.res_id = b.res_id
GROUP BY b.project_code, p.project_name, b.task_no, b.sub_task_no, 
         b.res_id, r.res_name, b.base_units, b.base_rate
ORDER BY b.project_code, b.task_no, b.sub_task_no;

-- Unbilled time
CREATE OR REPLACE VIEW bgs.vw_unbilled_time AS
SELECT 
    t.project_code,
    p.project_name,
    t.ts_date,
    t.task_no,
    t.res_id,
    r.res_name,
    t.ts_units,
    b.base_rate,
    t.ts_units * b.base_rate as amount,
    t.ts_desc
FROM bgs.timesheet t
JOIN bgs.project p ON p.project_code = t.project_code
JOIN bgs.resource r ON r.res_id = t.res_id
LEFT JOIN bgs.baseline b ON b.project_code = t.project_code 
    AND b.task_no = t.task_no 
    AND b.res_id = t.res_id
WHERE t.invoice_code IS NULL
ORDER BY t.ts_date DESC;

-- Outstanding invoices
CREATE OR REPLACE VIEW bgs.vw_outstanding_invoices AS
SELECT 
    i.invoice_code,
    i.project_code,
    p.project_name,
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
