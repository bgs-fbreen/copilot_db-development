-- ============================================================================
-- LEASE TRACKING SYSTEM - SAMPLE DATA DEMO
-- ============================================================================
-- This script demonstrates how to use the lease tracking system with sample data
-- for property 711pine
-- ============================================================================

-- Step 1: Add a property
-- (Assuming properties are already added, but here's an example INSERT)
/*
INSERT INTO acc.properties (property_code, address, city, state, zip_code, purchase_date, purchase_price)
VALUES ('711pine', '711 Pine Street', 'Pittsburgh', 'PA', '15213', '2020-01-15', 175000);
*/

-- Step 2: Add projected expenses for the property
-- Get the property_id first
WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
INSERT INTO acc.property_expenses (property_id, expense_type, expense_name, amount, frequency, due_month)
SELECT 
    prop.id,
    expense_type,
    expense_name,
    amount,
    frequency,
    due_month
FROM prop, (VALUES
    ('summer_tax', 'Summer Property Tax', 1200.00, 'annual', 7),
    ('winter_tax', 'Winter Property Tax', 1800.00, 'annual', 12),
    ('insurance', 'Homeowners Insurance', 1200.00, 'annual', 1),
    ('maintenance', 'Regular Maintenance Reserve', 1200.00, 'annual', NULL)
) AS expenses(expense_type, expense_name, amount, frequency, due_month);

-- Step 3: Add a lease for academic year 2024-2025
WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
INSERT INTO acc.leases (property_id, start_date, end_date, monthly_rent, deposit_amount, deposit_applies_to_last_month, lease_type, status)
SELECT 
    prop.id,
    '2024-06-01',
    '2025-05-31',
    850.00,
    850.00,
    true,  -- Deposit covers last month (May 2025)
    'academic',
    'active'
FROM prop;

-- Step 4: Add tenants to the lease
-- Get the lease_id
WITH lease AS (
    SELECT l.id 
    FROM acc.leases l
    JOIN acc.properties p ON p.id = l.property_id
    WHERE p.property_code = '711pine'
    AND l.start_date = '2024-06-01'
)
INSERT INTO acc.lease_tenants (lease_id, tenant_name, email, phone, is_primary, is_student, school_name, graduation_date)
SELECT 
    lease.id,
    tenant_name,
    email,
    phone,
    is_primary,
    is_student,
    school_name,
    graduation_date
FROM lease, (VALUES
    ('John Smith', 'john.smith@cmu.edu', '412-555-1234', true, true, 'Carnegie Mellon University', '2025-05-15'),
    ('Jane Doe', 'jane.doe@cmu.edu', '412-555-5678', false, true, 'Carnegie Mellon University', '2025-05-15')
) AS tenants(tenant_name, email, phone, is_primary, is_student, school_name, graduation_date);

-- Step 5: Add guarantors
WITH lease AS (
    SELECT l.id 
    FROM acc.leases l
    JOIN acc.properties p ON p.id = l.property_id
    WHERE p.property_code = '711pine'
    AND l.start_date = '2024-06-01'
)
INSERT INTO acc.lease_guarantors (lease_id, guarantor_name, relationship, email, phone, address_line1, city, state, zip_code)
SELECT 
    lease.id,
    guarantor_name,
    relationship,
    email,
    phone,
    address_line1,
    city,
    state,
    zip_code
FROM lease, (VALUES
    ('Robert Smith', 'parent', 'robert.smith@email.com', '555-123-4567', '123 Main Street', 'Philadelphia', 'PA', '19103'),
    ('Mary Doe', 'parent', 'mary.doe@email.com', '555-987-6543', '456 Oak Avenue', 'New York', 'NY', '10001')
) AS guarantors(guarantor_name, relationship, email, phone, address_line1, city, state, zip_code);

-- Step 6: Record rent payments
WITH lease AS (
    SELECT l.id, p.id as property_id
    FROM acc.leases l
    JOIN acc.properties p ON p.id = l.property_id
    WHERE p.property_code = '711pine'
    AND l.start_date = '2024-06-01'
)
INSERT INTO acc.rent_payments (lease_id, property_id, payment_date, amount, for_month, payment_method, payment_status, check_number)
SELECT 
    lease.id,
    lease.property_id,
    payment_date,
    amount,
    for_month,
    payment_method,
    payment_status,
    check_number
FROM lease, (VALUES
    ('2024-06-05', 850.00, '2024-06-01', 'check', 'received', '1001'),
    ('2024-07-02', 850.00, '2024-07-01', 'check', 'received', '1002'),
    ('2024-08-03', 850.00, '2024-08-01', 'check', 'received', '1003'),
    ('2024-09-01', 850.00, '2024-09-01', 'check', 'received', '1004'),
    ('2024-10-05', 850.00, '2024-10-01', 'check', 'received', '1005')
) AS payments(payment_date, amount, for_month, payment_method, payment_status, check_number);

-- Step 7: Record actual expenses
WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
INSERT INTO acc.property_actual_expenses (property_id, expense_date, expense_type, description, amount, vendor, check_number)
SELECT 
    prop.id,
    expense_date,
    expense_type,
    description,
    amount,
    vendor,
    check_number
FROM prop, (VALUES
    ('2024-07-15', 'summer_tax', 'Summer 2024 Property Tax', 1200.00, 'Allegheny County', '2001'),
    ('2024-08-20', 'repair', 'Plumbing repair - bathroom sink', 350.00, 'Joe''s Plumbing', '2002'),
    ('2024-09-10', 'maintenance', 'Lawn mowing service', 120.00, 'Green Lawn Services', '2003')
) AS expenses(expense_date, expense_type, description, amount, vendor, check_number);

-- Step 8: Record a late fee adjustment
WITH lease AS (
    SELECT l.id, p.id as property_id
    FROM acc.leases l
    JOIN acc.properties p ON p.id = l.property_id
    WHERE p.property_code = '711pine'
    AND l.start_date = '2024-06-01'
)
INSERT INTO acc.rent_adjustments (lease_id, property_id, adjustment_date, adjustment_type, amount, description, for_month)
SELECT 
    lease.id,
    lease.property_id,
    '2024-10-06',
    'late_fee',
    50.00,
    'Late payment fee - rent received after 5th',
    '2024-10-01'
FROM lease;

-- ============================================================================
-- QUERIES TO VIEW THE DATA
-- ============================================================================

-- View lease details
SELECT * FROM acc.v_lease_details WHERE property_code = '711pine';

-- View contact directory
SELECT * FROM acc.v_lease_contact_directory WHERE property_code = '711pine';

-- View monthly comparison for 2024
SELECT 
    property_code,
    month_start,
    projected_rent,
    actual_rent,
    adjustments,
    total_actual_income,
    income_variance
FROM acc.v_property_monthly_comparison 
WHERE property_code = '711pine' 
AND year = 2024
ORDER BY month_start;

-- View P&L comparison for 2024
SELECT * FROM acc.v_property_pnl_comparison 
WHERE property_code = '711pine' 
AND year = 2024;

-- View projected expenses
SELECT 
    expense_type,
    expense_name,
    amount,
    frequency,
    CASE WHEN due_month IS NOT NULL THEN to_char(to_date(due_month::text, 'MM'), 'Month') ELSE 'N/A' END as due_month
FROM acc.property_expenses pe
JOIN acc.properties p ON p.id = pe.property_id
WHERE p.property_code = '711pine'
AND pe.active = true
ORDER BY expense_type;

-- View actual expenses
SELECT 
    expense_date,
    expense_type,
    description,
    amount,
    vendor
FROM acc.property_actual_expenses pae
JOIN acc.properties p ON p.id = pae.property_id
WHERE p.property_code = '711pine'
ORDER BY expense_date DESC;

-- ============================================================================
-- CLEANUP (Optional - uncomment to reset demo data)
-- ============================================================================
/*
WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
),
leases AS (
    SELECT l.id FROM acc.leases l WHERE l.property_id = (SELECT id FROM prop)
)
DELETE FROM acc.rent_adjustments WHERE lease_id IN (SELECT id FROM leases);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
),
leases AS (
    SELECT l.id FROM acc.leases l WHERE l.property_id = (SELECT id FROM prop)
)
DELETE FROM acc.rent_payments WHERE lease_id IN (SELECT id FROM leases);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
DELETE FROM acc.property_actual_expenses WHERE property_id = (SELECT id FROM prop);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
),
leases AS (
    SELECT l.id FROM acc.leases l WHERE l.property_id = (SELECT id FROM prop)
)
DELETE FROM acc.lease_guarantors WHERE lease_id IN (SELECT id FROM leases);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
),
leases AS (
    SELECT l.id FROM acc.leases l WHERE l.property_id = (SELECT id FROM prop)
)
DELETE FROM acc.lease_tenants WHERE lease_id IN (SELECT id FROM leases);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
DELETE FROM acc.leases WHERE property_id = (SELECT id FROM prop);

WITH prop AS (
    SELECT id FROM acc.properties WHERE property_code = '711pine'
)
DELETE FROM acc.property_expenses WHERE property_id = (SELECT id FROM prop);
*/
