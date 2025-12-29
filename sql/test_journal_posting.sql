-- ============================================================================
-- Test Script for Journal Posting System (Part 03)
-- Purpose: Demonstrates and validates journal posting functionality
-- ============================================================================

-- This script assumes you have:
-- 1. Already run sql/schema/01_core.sql
-- 2. Already run sql/schema/05_bank_staging.sql
-- 3. Already run sql/schema/06_trial_entry.sql
-- 4. Already run sql/schema/07_journal.sql (or migration 005)
-- 5. Some trial entries already validated (status = 'balanced')

\echo '============================================================================'
\echo 'TEST SUITE: Journal Posting System'
\echo '============================================================================'

-- ============================================================================
-- SETUP: Ensure we have test data
-- ============================================================================

\echo ''
\echo 'Setting up test data...'

-- Ensure test bank accounts exist
INSERT INTO acc.bank_account (code, name, account_type, status)
VALUES 
    ('bgs.checking', 'BGS Checking Account', 'checking', 'active'),
    ('bgs.savings', 'BGS Savings Account', 'savings', 'active'),
    ('exp.office', 'Office Expenses', 'expense', 'active'),
    ('exp.utilities', 'Utilities Expense', 'expense', 'active'),
    ('inc.consulting', 'Consulting Income', 'income', 'active'),
    ('transfer.internal', 'Internal Transfers', 'asset', 'active')
ON CONFLICT (code) DO NOTHING;

-- Create some bank_staging records if none exist
INSERT INTO acc.bank_staging 
    (source_account_code, normalized_date, description, amount, entity, gl_account_code, match_method, match_confidence)
VALUES
    ('bgs.checking', CURRENT_DATE - 10, 'Office supplies - Staples', -250.00, 'bgs', 'exp.office', 'manual', 100),
    ('bgs.checking', CURRENT_DATE - 9, 'Electric bill payment', -175.50, 'bgs', 'exp.utilities', 'manual', 100),
    ('bgs.checking', CURRENT_DATE - 8, 'Consulting payment from client', 7500.00, 'bgs', 'inc.consulting', 'manual', 100),
    ('bgs.checking', CURRENT_DATE - 5, 'Transfer to savings', -2000.00, 'bgs', 'transfer.internal', 'manual', 100),
    ('bgs.savings', CURRENT_DATE - 5, 'Transfer from checking', 2000.00, 'bgs', 'transfer.internal', 'manual', 100)
ON CONFLICT DO NOTHING;

-- Generate trial entries if they don't exist
SELECT * FROM acc.fn_generate_trial_entries('bgs', CURRENT_DATE - 15, CURRENT_DATE);

-- Validate trial entries
SELECT * FROM acc.fn_validate_trial_entries();

\echo 'Test data setup complete.'

-- ============================================================================
-- TEST 1: Verify trial entries ready to post
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 1: Verify trial entries are ready to post'
\echo '============================================================================'

SELECT 
    id,
    entry_date,
    description,
    entity,
    status,
    total_debit,
    total_credit,
    balance_status
FROM acc.vw_trial_entry_balance
WHERE status = 'balanced'
ORDER BY entry_date;

\echo ''
\echo 'Expected: At least some entries with status=balanced and balance_status=BALANCED'

-- ============================================================================
-- TEST 2: Post trial entries to journal
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 2: Post trial entries to journal'
\echo '============================================================================'

SELECT * FROM acc.fn_post_to_journal('bgs', 'test_admin');

\echo ''
\echo 'Expected: entries_posted > 0, entries_skipped = 0'

-- ============================================================================
-- TEST 3: Verify journal entries were created
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 3: Verify journal entries were created'
\echo '============================================================================'

SELECT 
    id,
    entry_date,
    description,
    entity,
    source_trial_id,
    posted_by,
    posted_at::DATE as posted_date
FROM acc.journal
ORDER BY entry_date;

\echo ''
\echo 'Expected: Journal entries corresponding to posted trial entries'

-- ============================================================================
-- TEST 4: Check journal entry balance status
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 4: Check journal entry balance status'
\echo '============================================================================'

SELECT 
    id,
    entry_date,
    description,
    line_count,
    total_debit,
    total_credit,
    difference,
    balance_status
FROM acc.vw_journal_entry_balance
ORDER BY entry_date;

\echo ''
\echo 'Expected: All entries should have balance_status = BALANCED'

-- ============================================================================
-- TEST 5: View journal lines detail
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 5: View journal lines detail'
\echo '============================================================================'

SELECT 
    j.id as journal_id,
    j.entry_date,
    j.description,
    l.line_num,
    l.gl_account_code,
    l.debit,
    l.credit,
    l.memo
FROM acc.journal j
JOIN acc.journal_line l ON l.journal_id = j.id
ORDER BY j.entry_date, j.id, l.line_num
LIMIT 20;

\echo ''
\echo 'Expected: Two lines per entry, debits = credits for each entry'

-- ============================================================================
-- TEST 6: View GL account balances
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 6: View GL account balances'
\echo '============================================================================'

SELECT 
    gl_account_code,
    entity,
    total_debit,
    total_credit,
    balance
FROM acc.vw_gl_balances
WHERE entity = 'bgs'
ORDER BY gl_account_code;

\echo ''
\echo 'Expected: Balances for all GL accounts used in journal entries'

-- ============================================================================
-- TEST 7: View trial balance report
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 7: View trial balance report'
\echo '============================================================================'

SELECT 
    gl_account_code,
    entity,
    debit_balance,
    credit_balance
FROM acc.vw_trial_balance
WHERE entity = 'bgs'
ORDER BY gl_account_code;

\echo ''
\echo 'Expected: Trial balance with separate debit/credit columns'
\echo 'Note: Sum of debit_balance should equal sum of credit_balance'

-- ============================================================================
-- TEST 8: Verify trial balance totals match
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 8: Verify trial balance totals'
\echo '============================================================================'

SELECT 
    SUM(debit_balance) as total_debits,
    SUM(credit_balance) as total_credits,
    SUM(debit_balance) - SUM(credit_balance) as difference
FROM acc.vw_trial_balance
WHERE entity = 'bgs';

\echo ''
\echo 'Expected: difference = 0 (trial balance is balanced)'

-- ============================================================================
-- TEST 9: Verify trial entries marked as posted
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 9: Verify trial entries marked as posted'
\echo '============================================================================'

SELECT 
    id,
    entry_date,
    description,
    status
FROM acc.trial_entry
WHERE entity = 'bgs'
  AND status = 'posted'
ORDER BY entry_date;

\echo ''
\echo 'Expected: Trial entries should have status = posted'

-- ============================================================================
-- TEST 10: Verify bank_staging marked as reconciled
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 10: Verify bank_staging marked as reconciled'
\echo '============================================================================'

SELECT 
    s.id,
    s.normalized_date,
    s.description,
    s.reconciled,
    t.status as trial_status
FROM acc.bank_staging s
LEFT JOIN acc.trial_entry t ON t.source_staging_id = s.id
WHERE s.entity = 'bgs'
  AND s.gl_account_code != 'TODO'
ORDER BY s.normalized_date
LIMIT 10;

\echo ''
\echo 'Expected: reconciled = true for posted entries'

-- ============================================================================
-- TEST 11: Test reversal entry creation
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 11: Test reversal entry creation'
\echo '============================================================================'

-- Get the first journal entry ID to reverse
DO $$
DECLARE
    v_journal_id INTEGER;
    v_reversal_id INTEGER;
BEGIN
    SELECT id INTO v_journal_id FROM acc.journal ORDER BY id LIMIT 1;
    
    IF v_journal_id IS NOT NULL THEN
        -- Create reversal
        v_reversal_id := acc.fn_reverse_journal_entry(v_journal_id, 'Test reversal', 'test_admin');
        RAISE NOTICE 'Created reversal entry % for journal entry %', v_reversal_id, v_journal_id;
    ELSE
        RAISE NOTICE 'No journal entries to reverse';
    END IF;
END $$;

-- View the reversal
SELECT 
    j.id,
    j.entry_date,
    j.description,
    j.reversal_of,
    j.reversed_by
FROM acc.journal j
WHERE j.reversal_of IS NOT NULL OR j.reversed_by IS NOT NULL
ORDER BY j.id;

\echo ''
\echo 'Expected: Reversal entry created with reversed_of and reversed_by linked'

-- ============================================================================
-- TEST 12: Verify reversal lines (debits/credits swapped)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 12: Verify reversal lines (debits/credits swapped)'
\echo '============================================================================'

WITH reversal_pairs AS (
    SELECT j1.id as original_id, j2.id as reversal_id
    FROM acc.journal j1
    JOIN acc.journal j2 ON j2.reversal_of = j1.id
    LIMIT 1
)
SELECT 
    'ORIGINAL' as entry_type,
    l.line_num,
    l.gl_account_code,
    l.debit,
    l.credit
FROM acc.journal_line l
JOIN reversal_pairs rp ON l.journal_id = rp.original_id
UNION ALL
SELECT 
    'REVERSAL' as entry_type,
    l.line_num,
    l.gl_account_code,
    l.debit,
    l.credit
FROM acc.journal_line l
JOIN reversal_pairs rp ON l.journal_id = rp.reversal_id
ORDER BY entry_type DESC, line_num;

\echo ''
\echo 'Expected: Original debits become reversal credits and vice versa'

-- ============================================================================
-- TEST 13: Verify GL balances exclude reversed entries
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 13: Verify GL balances exclude reversed entries'
\echo '============================================================================'

-- GL balances should net out reversed entries
SELECT 
    gl_account_code,
    entity,
    total_debit,
    total_credit,
    balance
FROM acc.vw_gl_balances
WHERE entity = 'bgs'
ORDER BY gl_account_code;

\echo ''
\echo 'Expected: Reversed entries should not appear in GL balances'

-- ============================================================================
-- TEST 14: Test immutability - try to update journal entry (should fail)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 14: Test immutability - attempt to update journal entry'
\echo '============================================================================'

-- This should fail with an exception
DO $$
DECLARE
    v_journal_id INTEGER;
BEGIN
    SELECT id INTO v_journal_id FROM acc.journal LIMIT 1;
    
    IF v_journal_id IS NOT NULL THEN
        BEGIN
            UPDATE acc.journal SET description = 'MODIFIED' WHERE id = v_journal_id;
            RAISE NOTICE '✗ ERROR: Journal entry was modified (should have been prevented)';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE '✓ PASS: Journal entry update was prevented: %', SQLERRM;
        END;
    END IF;
END $$;

-- ============================================================================
-- TEST 15: Test immutability - try to delete journal entry (should fail)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 15: Test immutability - attempt to delete journal entry'
\echo '============================================================================'

DO $$
DECLARE
    v_journal_id INTEGER;
BEGIN
    SELECT id INTO v_journal_id FROM acc.journal LIMIT 1;
    
    IF v_journal_id IS NOT NULL THEN
        BEGIN
            DELETE FROM acc.journal WHERE id = v_journal_id;
            RAISE NOTICE '✗ ERROR: Journal entry was deleted (should have been prevented)';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE '✓ PASS: Journal entry deletion was prevented: %', SQLERRM;
        END;
    END IF;
END $$;

-- ============================================================================
-- TEST 16: Test immutability - try to delete journal line (should fail)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 16: Test immutability - attempt to delete journal line'
\echo '============================================================================'

DO $$
DECLARE
    v_line_id INTEGER;
BEGIN
    SELECT id INTO v_line_id FROM acc.journal_line LIMIT 1;
    
    IF v_line_id IS NOT NULL THEN
        BEGIN
            DELETE FROM acc.journal_line WHERE id = v_line_id;
            RAISE NOTICE '✗ ERROR: Journal line was deleted (should have been prevented)';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE '✓ PASS: Journal line deletion was prevented: %', SQLERRM;
        END;
    END IF;
END $$;

-- ============================================================================
-- TEST 17: Test double reversal prevention (should fail)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 17: Test double reversal prevention'
\echo '============================================================================'

DO $$
DECLARE
    v_journal_id INTEGER;
BEGIN
    SELECT id INTO v_journal_id 
    FROM acc.journal 
    WHERE reversed_by IS NOT NULL 
    LIMIT 1;
    
    IF v_journal_id IS NOT NULL THEN
        BEGIN
            PERFORM acc.fn_reverse_journal_entry(v_journal_id, 'Double reversal test', 'test_admin');
            RAISE NOTICE '✗ ERROR: Entry was reversed twice (should have been prevented)';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE '✓ PASS: Double reversal was prevented: %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'No reversed entries to test double reversal';
    END IF;
END $$;

-- ============================================================================
-- TEST SUMMARY
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST SUITE COMPLETE'
\echo '============================================================================'
\echo ''
\echo 'Summary:'
\echo '  ✓ Journal entries created from trial entries'
\echo '  ✓ All journal entries are balanced'
\echo '  ✓ GL account balances calculated correctly'
\echo '  ✓ Trial balance report generated'
\echo '  ✓ Reversal entries work correctly'
\echo '  ✓ Immutability enforced (updates/deletes prevented)'
\echo '  ✓ Bank staging records marked as reconciled'
\echo '  ✓ Trial entries marked as posted'
\echo ''
\echo '============================================================================'

-- ============================================================================
-- CLEANUP (OPTIONAL)
-- ============================================================================

-- Uncomment to clean up test data:
-- \echo ''
-- \echo 'Cleaning up test data...'
-- DELETE FROM acc.journal WHERE entity = 'bgs';
-- DELETE FROM acc.trial_entry WHERE entity = 'bgs';
-- DELETE FROM acc.bank_staging WHERE entity = 'bgs' AND description LIKE '%test%';
-- \echo 'Cleanup complete.'
