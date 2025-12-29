-- ============================================================================
-- Migration 005: Add Journal Posting System (Part 03)
-- Date: 2025-12-29
-- Description: Creates journal tables, views, and functions for final posting
-- ============================================================================

-- This migration assumes:
-- 1. Core schema (01_core.sql) is already loaded
-- 2. Bank staging (05_bank_staging.sql) is already loaded
-- 3. Trial entry system (06_trial_entry.sql or migration 004) is already loaded

\echo 'Starting Migration 005: Journal Posting System'

-- ============================================================================
-- CHECK PREREQUISITES
-- ============================================================================

DO $$
BEGIN
    -- Check if acc schema exists
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'acc') THEN
        RAISE EXCEPTION 'Schema acc does not exist. Please run 01_core.sql first.';
    END IF;
    
    -- Check if trial_entry table exists
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'acc' AND tablename = 'trial_entry') THEN
        RAISE EXCEPTION 'Table acc.trial_entry does not exist. Please run migration 004 first.';
    END IF;
    
    -- Check if bank_staging table exists
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'acc' AND tablename = 'bank_staging') THEN
        RAISE EXCEPTION 'Table acc.bank_staging does not exist. Please run 05_bank_staging.sql first.';
    END IF;
    
    RAISE NOTICE 'Prerequisites check passed.';
END $$;

-- ============================================================================
-- LOAD JOURNAL SCHEMA
-- ============================================================================

\echo 'Creating journal tables, views, triggers, and functions...'

-- Execute the journal schema file
\ir ../schema/07_journal.sql

-- ============================================================================
-- VERIFY INSTALLATION
-- ============================================================================

\echo 'Verifying journal system installation...'

DO $$
DECLARE
    v_table_count INTEGER;
    v_view_count INTEGER;
    v_function_count INTEGER;
    v_trigger_count INTEGER;
BEGIN
    -- Check tables
    SELECT COUNT(*) INTO v_table_count
    FROM pg_tables 
    WHERE schemaname = 'acc' AND tablename IN ('journal', 'journal_line');
    
    IF v_table_count != 2 THEN
        RAISE EXCEPTION 'Expected 2 journal tables, found %', v_table_count;
    END IF;
    RAISE NOTICE 'Tables created: % ✓', v_table_count;
    
    -- Check views
    SELECT COUNT(*) INTO v_view_count
    FROM pg_views 
    WHERE schemaname = 'acc' AND viewname IN ('vw_journal_entry_balance', 'vw_gl_balances', 'vw_trial_balance');
    
    IF v_view_count != 3 THEN
        RAISE EXCEPTION 'Expected 3 journal views, found %', v_view_count;
    END IF;
    RAISE NOTICE 'Views created: % ✓', v_view_count;
    
    -- Check functions
    SELECT COUNT(*) INTO v_function_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'acc' 
      AND p.proname IN ('fn_post_to_journal', 'fn_reverse_journal_entry', 
                        'fn_prevent_journal_update', 'fn_prevent_journal_delete',
                        'fn_prevent_journal_line_delete');
    
    IF v_function_count < 5 THEN
        RAISE EXCEPTION 'Expected at least 5 journal functions, found %', v_function_count;
    END IF;
    RAISE NOTICE 'Functions created: % ✓', v_function_count;
    
    -- Check triggers
    SELECT COUNT(*) INTO v_trigger_count
    FROM pg_trigger t
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'acc' 
      AND c.relname IN ('journal', 'journal_line')
      AND t.tgname LIKE 'trg_prevent_%';
    
    IF v_trigger_count != 3 THEN
        RAISE EXCEPTION 'Expected 3 immutability triggers, found %', v_trigger_count;
    END IF;
    RAISE NOTICE 'Triggers created: % ✓', v_trigger_count;
    
    RAISE NOTICE '✓ Journal posting system successfully installed!';
END $$;

-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================

\echo ''
\echo '========================================================================='
\echo 'Migration 005 completed successfully!'
\echo '========================================================================='
\echo ''
\echo 'Journal Posting System is now available.'
\echo ''
\echo 'Key functions:'
\echo '  - acc.fn_post_to_journal(entity, posted_by) - Post trial entries to journal'
\echo '  - acc.fn_reverse_journal_entry(journal_id, reason, reversed_by) - Reverse entries'
\echo ''
\echo 'Key views:'
\echo '  - acc.vw_journal_entry_balance - Check journal entry balances'
\echo '  - acc.vw_gl_balances - Current GL account balances'
\echo '  - acc.vw_trial_balance - Trial balance report'
\echo ''
\echo 'Example usage:'
\echo '  SELECT * FROM acc.fn_post_to_journal(''bgs'', ''admin'');'
\echo '  SELECT * FROM acc.vw_journal_entry_balance;'
\echo ''
\echo 'For testing, see: sql/test_journal_posting.sql'
\echo '========================================================================='
