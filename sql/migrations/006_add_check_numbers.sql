-- ============================================================================
-- Migration 006: Add Check Number Tracking
-- Date: 2025-12-29
-- Description: Adds check_number column to bank_staging, trial_entry, and journal tables
-- ============================================================================

\echo 'Starting Migration 006: Add Check Number Tracking'

-- ============================================================================
-- ADD CHECK_NUMBER TO BANK_STAGING
-- ============================================================================

\echo '  Adding check_number to acc.bank_staging...'

ALTER TABLE acc.bank_staging ADD COLUMN IF NOT EXISTS check_number VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_staging_check ON acc.bank_staging(check_number);
COMMENT ON COLUMN acc.bank_staging.check_number IS 'Check number for check transactions';

-- ============================================================================
-- ADD CHECK_NUMBER TO TRIAL_ENTRY
-- ============================================================================

\echo '  Adding check_number to acc.trial_entry...'

ALTER TABLE acc.trial_entry ADD COLUMN IF NOT EXISTS check_number VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_trial_entry_check ON acc.trial_entry(check_number);
COMMENT ON COLUMN acc.trial_entry.check_number IS 'Check number carried from bank_staging';

-- ============================================================================
-- ADD CHECK_NUMBER TO JOURNAL
-- ============================================================================

\echo '  Adding check_number to acc.journal...'

ALTER TABLE acc.journal ADD COLUMN IF NOT EXISTS check_number VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_journal_check ON acc.journal(check_number);
COMMENT ON COLUMN acc.journal.check_number IS 'Check number for check transactions';

-- ============================================================================
-- UPDATE VIEWS
-- ============================================================================

\echo '  Updating views to include check_number...'

-- Update vw_trial_entry_balance
CREATE OR REPLACE VIEW acc.vw_trial_entry_balance AS
SELECT 
    e.id,
    e.entry_date,
    e.description,
    e.entity,
    e.status,
    e.source_staging_id,
    e.check_number,
    COUNT(l.id) as line_count,
    SUM(l.debit) as total_debit,
    SUM(l.credit) as total_credit,
    SUM(l.debit) - SUM(l.credit) as difference,
    CASE 
        WHEN SUM(l.debit) = SUM(l.credit) AND SUM(l.debit) > 0 THEN 'BALANCED'
        WHEN SUM(l.debit) = 0 AND SUM(l.credit) = 0 THEN 'EMPTY'
        ELSE 'UNBALANCED' 
    END as balance_status
FROM acc.trial_entry e
LEFT JOIN acc.trial_entry_line l ON l.entry_id = e.id
GROUP BY e.id, e.entry_date, e.description, e.entity, e.status, e.source_staging_id, e.check_number;

-- Update vw_trial_ready_to_post
CREATE OR REPLACE VIEW acc.vw_trial_ready_to_post AS
SELECT 
    b.id,
    b.entry_date,
    b.description,
    b.entity,
    b.check_number,
    b.total_debit,
    b.total_credit
FROM acc.vw_trial_entry_balance b
WHERE b.balance_status = 'BALANCED'
  AND b.status = 'balanced'
  AND NOT EXISTS (
      SELECT 1 FROM acc.vw_trial_invalid_gl inv WHERE inv.entry_id = b.id
  );

-- Update vw_journal_entry_balance
CREATE OR REPLACE VIEW acc.vw_journal_entry_balance AS
SELECT 
    j.id,
    j.entry_date,
    j.description,
    j.entity,
    j.reference_num,
    j.check_number,
    j.posted_at,
    COUNT(l.id) as line_count,
    SUM(l.debit) as total_debit,
    SUM(l.credit) as total_credit,
    SUM(l.debit) - SUM(l.credit) as difference,
    CASE 
        WHEN SUM(l.debit) = SUM(l.credit) AND SUM(l.debit) > 0 THEN 'BALANCED'
        WHEN SUM(l.debit) = 0 AND SUM(l.credit) = 0 THEN 'EMPTY'
        ELSE 'UNBALANCED' 
    END as balance_status
FROM acc.journal j
LEFT JOIN acc.journal_line l ON l.journal_id = j.id
GROUP BY j.id, j.entry_date, j.description, j.entity, j.reference_num, j.check_number, j.posted_at;

-- ============================================================================
-- UPDATE FUNCTIONS
-- ============================================================================

\echo '  Updating functions to handle check_number...'

-- Update fn_generate_trial_entries to copy check_number
CREATE OR REPLACE FUNCTION acc.fn_generate_trial_entries(
    p_entity VARCHAR(50) DEFAULT NULL,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL
)
RETURNS TABLE(entries_created INTEGER, entries_skipped INTEGER) AS $$
DECLARE
    v_created INTEGER := 0;
    v_skipped INTEGER := 0;
    v_entry_id INTEGER;
    v_staging RECORD;
BEGIN
    FOR v_staging IN 
        SELECT * FROM acc.bank_staging s
        WHERE (p_entity IS NULL OR s.entity = p_entity)
          AND (p_date_from IS NULL OR s.normalized_date >= p_date_from)
          AND (p_date_to IS NULL OR s.normalized_date <= p_date_to)
          AND s.gl_account_code != 'TODO'
          AND NOT EXISTS (
              SELECT 1 FROM acc.trial_entry t WHERE t.source_staging_id = s.id
          )
    LOOP
        -- Create trial entry header
        INSERT INTO acc.trial_entry (entry_date, description, entity, source_staging_id, status, check_number)
        VALUES (v_staging.normalized_date, v_staging.description, v_staging.entity, v_staging.id, 'pending', v_staging.check_number)
        RETURNING id INTO v_entry_id;
        
        -- Create debit/credit lines based on amount sign
        IF v_staging.amount < 0 THEN
            -- Expense/outflow: Debit the GL account, Credit the bank account
            INSERT INTO acc.trial_entry_line (entry_id, line_num, gl_account_code, debit, credit, entity, memo)
            VALUES (v_entry_id, 1, v_staging.gl_account_code, ABS(v_staging.amount), 0, v_staging.entity, v_staging.description);
            
            INSERT INTO acc.trial_entry_line (entry_id, line_num, gl_account_code, debit, credit, entity, memo)
            VALUES (v_entry_id, 2, v_staging.source_account_code, 0, ABS(v_staging.amount), v_staging.entity, v_staging.description);
        ELSE
            -- Income/inflow: Debit the bank account, Credit the GL account
            INSERT INTO acc.trial_entry_line (entry_id, line_num, gl_account_code, debit, credit, entity, memo)
            VALUES (v_entry_id, 1, v_staging.source_account_code, v_staging.amount, 0, v_staging.entity, v_staging.description);
            
            INSERT INTO acc.trial_entry_line (entry_id, line_num, gl_account_code, debit, credit, entity, memo)
            VALUES (v_entry_id, 2, v_staging.gl_account_code, 0, v_staging.amount, v_staging.entity, v_staging.description);
        END IF;
        
        v_created := v_created + 1;
    END LOOP;
    
    -- Count skipped (TODO or already processed)
    SELECT COUNT(*) INTO v_skipped
    FROM acc.bank_staging s
    WHERE (p_entity IS NULL OR s.entity = p_entity)
      AND (p_date_from IS NULL OR s.normalized_date >= p_date_from)
      AND (p_date_to IS NULL OR s.normalized_date <= p_date_to)
      AND (s.gl_account_code = 'TODO' OR EXISTS (
          SELECT 1 FROM acc.trial_entry t WHERE t.source_staging_id = s.id
      ));
    
    RETURN QUERY SELECT v_created, v_skipped;
END;
$$ LANGUAGE plpgsql;

-- Update fn_post_to_journal to copy check_number
CREATE OR REPLACE FUNCTION acc.fn_post_to_journal(
    p_entity VARCHAR(50) DEFAULT NULL,
    p_posted_by VARCHAR(100) DEFAULT 'system'
)
RETURNS TABLE(entries_posted INTEGER, entries_skipped INTEGER) AS $$
DECLARE
    v_posted INTEGER := 0;
    v_skipped INTEGER := 0;
    v_journal_id INTEGER;
    v_trial RECORD;
    v_line RECORD;
BEGIN
    -- Process all balanced trial entries that haven't been posted
    FOR v_trial IN 
        SELECT e.* 
        FROM acc.trial_entry e
        WHERE e.status = 'balanced'
          AND (p_entity IS NULL OR e.entity = p_entity)
          AND NOT EXISTS (SELECT 1 FROM acc.journal j WHERE j.source_trial_id = e.id)
    LOOP
        -- Verify entry is still balanced (double-check)
        IF NOT EXISTS (
            SELECT 1 FROM acc.vw_trial_entry_balance b 
            WHERE b.id = v_trial.id AND b.balance_status = 'BALANCED'
        ) THEN
            v_skipped := v_skipped + 1;
            CONTINUE;
        END IF;
        
        -- Create journal entry
        INSERT INTO acc.journal (entry_date, description, entity, source_trial_id, posted_by, check_number)
        VALUES (v_trial.entry_date, v_trial.description, v_trial.entity, v_trial.id, p_posted_by, v_trial.check_number)
        RETURNING id INTO v_journal_id;
        
        -- Copy lines from trial entry
        INSERT INTO acc.journal_line (journal_id, line_num, gl_account_code, debit, credit, entity, memo)
        SELECT v_journal_id, line_num, gl_account_code, debit, credit, entity, memo
        FROM acc.trial_entry_line
        WHERE entry_id = v_trial.id;
        
        -- Update trial entry status
        UPDATE acc.trial_entry 
        SET status = 'posted', updated_at = CURRENT_TIMESTAMP
        WHERE id = v_trial.id;
        
        -- Update bank_staging as reconciled
        UPDATE acc.bank_staging
        SET reconciled = true, updated_at = CURRENT_TIMESTAMP
        WHERE id = v_trial.source_staging_id;
        
        v_posted := v_posted + 1;
    END LOOP;
    
    RETURN QUERY SELECT v_posted, v_skipped;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

\echo '  Verifying check_number columns...'

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verify bank_staging column
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns 
    WHERE table_schema = 'acc' 
      AND table_name = 'bank_staging' 
      AND column_name = 'check_number';
    
    IF v_count = 0 THEN
        RAISE EXCEPTION 'check_number column not found in acc.bank_staging';
    END IF;
    
    -- Verify trial_entry column
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns 
    WHERE table_schema = 'acc' 
      AND table_name = 'trial_entry' 
      AND column_name = 'check_number';
    
    IF v_count = 0 THEN
        RAISE EXCEPTION 'check_number column not found in acc.trial_entry';
    END IF;
    
    -- Verify journal column
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns 
    WHERE table_schema = 'acc' 
      AND table_name = 'journal' 
      AND column_name = 'check_number';
    
    IF v_count = 0 THEN
        RAISE EXCEPTION 'check_number column not found in acc.journal';
    END IF;
    
    RAISE NOTICE '✓ All check_number columns verified';
END $$;

-- ============================================================================
-- COMPLETION
-- ============================================================================

\echo ''
\echo '========================================================================='
\echo 'Migration 006 completed successfully!'
\echo '========================================================================='
\echo ''
\echo 'Check number tracking is now available across:'
\echo '  - acc.bank_staging'
\echo '  - acc.trial_entry'
\echo '  - acc.journal'
\echo ''
\echo 'Updated functions:'
\echo '  - acc.fn_generate_trial_entries() - Copies check_number from staging'
\echo '  - acc.fn_post_to_journal() - Copies check_number to journal'
\echo ''
\echo 'Updated views:'
\echo '  - acc.vw_trial_entry_balance'
\echo '  - acc.vw_trial_ready_to_post'
\echo '  - acc.vw_journal_entry_balance'
\echo '========================================================================='
