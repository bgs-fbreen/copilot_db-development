-- ============================================================================
-- Test Script for Trial Entry System
-- Purpose: Demonstrates the usage of trial entry tables, views, and functions
-- ============================================================================

-- This script assumes you have:
-- 1. Already run sql/schema/01_core.sql
-- 2. Already run sql/schema/05_bank_staging.sql
-- 3. Already run sql/migrations/004_add_trial_entry.sql

-- ============================================================================
-- SAMPLE DATA SETUP (Optional - for testing)
-- ============================================================================

-- Ensure we have some test bank accounts
INSERT INTO acc.bank_account (code, name, account_type, status)
VALUES 
    ('bgs.checking', 'BGS Checking Account', 'checking', 'active'),
    ('bgs.savings', 'BGS Savings Account', 'savings', 'active'),
    ('exp.office', 'Office Expenses', 'expense', 'active'),
    ('inc.consulting', 'Consulting Income', 'income', 'active'),
    ('transfer.internal', 'Internal Transfers', 'asset', 'active')
ON CONFLICT (code) DO NOTHING;

-- Sample bank_staging records with GL codes assigned
INSERT INTO acc.bank_staging 
    (source_account_code, normalized_date, description, amount, entity, gl_account_code, match_method, match_confidence)
VALUES
    ('bgs.checking', '2025-01-15', 'Office supplies purchase', -150.00, 'bgs', 'exp.office', 'manual', 100),
    ('bgs.checking', '2025-01-16', 'Consulting payment received', 5000.00, 'bgs', 'inc.consulting', 'manual', 100),
    ('bgs.checking', '2025-01-17', 'Transfer to savings', -1000.00, 'bgs', 'transfer.internal', 'manual', 100),
    ('bgs.savings', '2025-01-17', 'Transfer from checking', 1000.00, 'bgs', 'transfer.internal', 'manual', 100)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- TEST 1: Generate trial entries for bgs entity
-- ============================================================================

SELECT * FROM acc.fn_generate_trial_entries('bgs');

-- Expected output: entries_created | entries_skipped
--                  4              | 0

-- ============================================================================
-- TEST 2: View trial entry balance status
-- ============================================================================

SELECT 
    id,
    entry_date,
    description,
    entity,
    status,
    line_count,
    total_debit,
    total_credit,
    difference,
    balance_status
FROM acc.vw_trial_entry_balance
ORDER BY entry_date;

-- Expected: All entries should show balance_status = 'BALANCED'
-- Each entry should have total_debit = total_credit

-- ============================================================================
-- TEST 3: Validate entries
-- ============================================================================

SELECT * FROM acc.fn_validate_trial_entries();

-- Expected output: validated | errors
--                  4         | 0

-- ============================================================================
-- TEST 4: Check entries ready to post
-- ============================================================================

SELECT 
    id,
    entry_date,
    description,
    entity,
    total_debit,
    total_credit
FROM acc.vw_trial_ready_to_post
ORDER BY entry_date;

-- Expected: 4 entries (all should be balanced and validated)

-- ============================================================================
-- TEST 5: Find unmatched transfers (should be empty after all setup)
-- ============================================================================

SELECT 
    staging_id,
    source_account_code,
    normalized_date,
    description,
    amount,
    direction
FROM acc.vw_unmatched_transfers;

-- Expected: 0 rows (transfers are matched in pairs)

-- ============================================================================
-- TEST 6: Match transfer pairs
-- ============================================================================

SELECT acc.fn_match_transfer_pairs('bgs');

-- Expected: 1 (one pair of transfers matched)

-- ============================================================================
-- TEST 7: Verify transfer matching
-- ============================================================================

SELECT 
    e1.id as entry1_id,
    e1.entry_date,
    e1.description as entry1_desc,
    e1.transfer_match_id as matches_entry2_id,
    e2.description as entry2_desc
FROM acc.trial_entry e1
LEFT JOIN acc.trial_entry e2 ON e1.transfer_match_id = e2.id
WHERE e1.transfer_match_id IS NOT NULL;

-- Expected: 2 rows showing the matched transfer pair

-- ============================================================================
-- TEST 8: View entry lines detail
-- ============================================================================

SELECT 
    e.id as entry_id,
    e.entry_date,
    e.description,
    l.line_num,
    l.gl_account_code,
    l.debit,
    l.credit,
    l.memo
FROM acc.trial_entry e
JOIN acc.trial_entry_line l ON l.entry_id = e.id
ORDER BY e.entry_date, l.line_num;

-- Expected: Each entry has 2 lines, debits = credits for each entry

-- ============================================================================
-- TEST 9: Check for invalid GL codes (should be empty)
-- ============================================================================

SELECT 
    entry_id,
    entry_date,
    description,
    gl_account_code,
    error
FROM acc.vw_trial_invalid_gl;

-- Expected: 0 rows (all GL codes are valid)

-- ============================================================================
-- TEST 10: Test error handling - invalid GL code
-- ============================================================================

-- Insert a staging record with invalid GL code
INSERT INTO acc.bank_staging 
    (source_account_code, normalized_date, description, amount, entity, gl_account_code, match_method)
VALUES
    ('bgs.checking', '2025-01-18', 'Test invalid GL', -100.00, 'bgs', 'invalid.account', 'manual');

-- Generate trial entry for this record
SELECT * FROM acc.fn_generate_trial_entries('bgs', '2025-01-18', '2025-01-18');

-- Validate (should mark as error)
SELECT * FROM acc.fn_validate_trial_entries();

-- Check the error
SELECT id, description, status, error_message 
FROM acc.trial_entry 
WHERE description = 'Test invalid GL';

-- Expected: status = 'error', error_message = 'Invalid GL account code'

-- ============================================================================
-- CLEANUP (Optional)
-- ============================================================================

-- Uncomment to clean up test data:
-- DELETE FROM acc.trial_entry WHERE entity = 'bgs';
-- DELETE FROM acc.bank_staging WHERE entity = 'bgs';
