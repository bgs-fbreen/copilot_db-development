-- ============================================
-- Migration: Fix Client and Project Data for Invoicing
-- ============================================

-- Add missing fields to client table
ALTER TABLE bgs.client 
ADD COLUMN IF NOT EXISTS street_address VARCHAR(200),
ADD COLUMN IF NOT EXISTS street_address2 VARCHAR(200),
ADD COLUMN IF NOT EXISTS contact_title VARCHAR(100),
ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(50),
ADD COLUMN IF NOT EXISTS contact_email VARCHAR(200);

-- Update client table structure comment
COMMENT ON TABLE bgs.client IS 'Client information with complete address for invoicing';

-- Add project location fields (separate from client)
ALTER TABLE bgs.project
ADD COLUMN IF NOT EXISTS project_street VARCHAR(200),
ADD COLUMN IF NOT EXISTS project_city VARCHAR(100),
ADD COLUMN IF NOT EXISTS project_state VARCHAR(2),
ADD COLUMN IF NOT EXISTS project_zip VARCHAR(20),
ADD COLUMN IF NOT EXISTS project_country VARCHAR(50) DEFAULT 'USA';

-- Update project table structure comment
COMMENT ON TABLE bgs.project IS 'Project information including project site location (may differ from client location)';

-- Add invoice header note field for special terms
ALTER TABLE bgs.invoice
ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(100) DEFAULT 'Net 30',
ADD COLUMN IF NOT EXISTS invoice_notes TEXT;

-- Create view for complete invoice data
CREATE OR REPLACE VIEW bgs.vw_invoice_complete AS
SELECT 
    i.invoice_code,
    i.invoice_number,
    i.invoice_date,
    i.due_date,
    i.amount,
    i.paid_amount,
    i.status,
    i.payment_terms,
    i.payment_date,
    i.payment_method,
    i.check_number,
    i.notes,
    i.invoice_notes,
    -- Project info
    p.project_code,
    p.project_name,
    p.project_desc,
    p.client_po,
    p.project_street,
    p.project_city,
    p.project_state,
    p.project_zip,
    p.project_country,
    -- Client info
    c.code as client_code,
    c.name as client_name,
    c.contact_name,
    c.contact_title,
    c.contact_phone,
    c.contact_email,
    c.address as client_address,
    c.street_address as client_street,
    c.street_address2 as client_street2,
    c.city as client_city,
    c.state as client_state,
    c.zip as client_zip
FROM bgs.invoice i
JOIN bgs.project p ON p.project_code = i.project_code
JOIN bgs.client c ON c.code = p.client_code;

COMMENT ON VIEW bgs.vw_invoice_complete IS 'Complete invoice data with all client and project information for invoice generation';

