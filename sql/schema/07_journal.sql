-- ============================================================================
-- Part 03: Journal Posting System
-- Created: 2025-12-29
-- Purpose: Final, immutable journal entries - the permanent accounting record
-- ============================================================================

-- ============================================================================
-- JOURNAL TABLE - Entry Header
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.journal (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL,
    description TEXT,
    entity VARCHAR(50) NOT NULL,
    source_trial_id INTEGER REFERENCES acc.trial_entry(id),
    reference_num VARCHAR(50),
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_by VARCHAR(100),
    reversal_of INTEGER REFERENCES acc.journal(id),
    reversed_by INTEGER REFERENCES acc.journal(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.journal IS 'Final, immutable journal entries - the permanent accounting record';
COMMENT ON COLUMN acc.journal.source_trial_id IS 'Reference to trial_entry that was posted';
COMMENT ON COLUMN acc.journal.reversal_of IS 'If this is a reversal entry, points to the original';
COMMENT ON COLUMN acc.journal.reversed_by IS 'If this entry was reversed, points to the reversal entry';

CREATE INDEX IF NOT EXISTS idx_journal_date ON acc.journal(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_entity ON acc.journal(entity);
CREATE INDEX IF NOT EXISTS idx_journal_trial ON acc.journal(source_trial_id);
CREATE INDEX IF NOT EXISTS idx_journal_reference ON acc.journal(reference_num);

-- ============================================================================
-- JOURNAL LINE TABLE - Debit/Credit Lines
-- ============================================================================

CREATE TABLE IF NOT EXISTS acc.journal_line (
    id SERIAL PRIMARY KEY,
    journal_id INTEGER NOT NULL REFERENCES acc.journal(id) ON DELETE RESTRICT,
    line_num INTEGER NOT NULL,
    gl_account_code VARCHAR(100) NOT NULL,
    debit NUMERIC(12,2) DEFAULT 0,
    credit NUMERIC(12,2) DEFAULT 0,
    entity VARCHAR(50),
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.journal_line IS 'Debit and credit lines for journal entries';

CREATE INDEX IF NOT EXISTS idx_journal_line_journal ON acc.journal_line(journal_id);
CREATE INDEX IF NOT EXISTS idx_journal_line_gl ON acc.journal_line(gl_account_code);

-- Constraint: Each line must have debit OR credit, not both
ALTER TABLE acc.journal_line DROP CONSTRAINT IF EXISTS chk_journal_debit_or_credit;
ALTER TABLE acc.journal_line ADD CONSTRAINT chk_journal_debit_or_credit 
    CHECK ((debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0) OR (debit = 0 AND credit = 0));

-- ============================================================================
-- TRIGGER: PREVENT JOURNAL LINE DELETION
-- ============================================================================

CREATE OR REPLACE FUNCTION acc.fn_prevent_journal_line_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Journal lines cannot be deleted. Use reversal entries instead.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_journal_line_delete ON acc.journal_line;
CREATE TRIGGER trg_prevent_journal_line_delete
    BEFORE DELETE ON acc.journal_line
    FOR EACH ROW
    EXECUTE FUNCTION acc.fn_prevent_journal_line_delete();

COMMENT ON TRIGGER trg_prevent_journal_line_delete ON acc.journal_line IS 
    'Prevents deletion of journal lines to maintain immutability';

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View 1: Journal entry balance check
CREATE OR REPLACE VIEW acc.vw_journal_entry_balance AS
SELECT 
    j.id,
    j.entry_date,
    j.description,
    j.entity,
    j.reference_num,
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
GROUP BY j.id, j.entry_date, j.description, j.entity, j.reference_num, j.posted_at;

COMMENT ON VIEW acc.vw_journal_entry_balance IS 'Shows balance status for each journal entry';

-- View 2: GL Account balances
CREATE OR REPLACE VIEW acc.vw_gl_balances AS
SELECT 
    l.gl_account_code,
    l.entity,
    SUM(l.debit) as total_debit,
    SUM(l.credit) as total_credit,
    SUM(l.debit) - SUM(l.credit) as balance
FROM acc.journal_line l
JOIN acc.journal j ON j.id = l.journal_id
WHERE j.reversed_by IS NULL  -- Exclude reversed entries
GROUP BY l.gl_account_code, l.entity
ORDER BY l.gl_account_code;

COMMENT ON VIEW acc.vw_gl_balances IS 'Shows current balances for each GL account excluding reversed entries';

-- View 3: Trial balance report
CREATE OR REPLACE VIEW acc.vw_trial_balance AS
SELECT 
    gl_account_code,
    entity,
    CASE WHEN balance > 0 THEN balance ELSE 0 END as debit_balance,
    CASE WHEN balance < 0 THEN ABS(balance) ELSE 0 END as credit_balance
FROM acc.vw_gl_balances
ORDER BY gl_account_code;

COMMENT ON VIEW acc.vw_trial_balance IS 'Trial balance report with debit/credit columns';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function 1: Post trial entries to journal
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
        INSERT INTO acc.journal (entry_date, description, entity, source_trial_id, posted_by)
        VALUES (v_trial.entry_date, v_trial.description, v_trial.entity, v_trial.id, p_posted_by)
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

COMMENT ON FUNCTION acc.fn_post_to_journal IS 'Post validated trial entries to the journal';

-- Function 2: Create reversal entry
CREATE OR REPLACE FUNCTION acc.fn_reverse_journal_entry(
    p_journal_id INTEGER,
    p_reason TEXT DEFAULT 'Reversal',
    p_reversed_by VARCHAR(100) DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_original RECORD;
    v_reversal_id INTEGER;
BEGIN
    -- Get original entry
    SELECT * INTO v_original FROM acc.journal WHERE id = p_journal_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Journal entry % not found', p_journal_id;
    END IF;
    
    IF v_original.reversed_by IS NOT NULL THEN
        RAISE EXCEPTION 'Journal entry % has already been reversed by entry %', p_journal_id, v_original.reversed_by;
    END IF;
    
    -- Create reversal entry (swap debits and credits)
    INSERT INTO acc.journal (entry_date, description, entity, reversal_of, posted_by)
    VALUES (CURRENT_DATE, 'REVERSAL: ' || COALESCE(v_original.description, '') || ' - ' || p_reason, 
            v_original.entity, p_journal_id, p_reversed_by)
    RETURNING id INTO v_reversal_id;
    
    -- Copy lines with debits and credits swapped
    INSERT INTO acc.journal_line (journal_id, line_num, gl_account_code, debit, credit, entity, memo)
    SELECT v_reversal_id, line_num, gl_account_code, credit, debit, entity, 'REVERSAL: ' || COALESCE(memo, '')
    FROM acc.journal_line
    WHERE journal_id = p_journal_id;
    
    -- Link original to reversal
    UPDATE acc.journal SET reversed_by = v_reversal_id WHERE id = p_journal_id;
    
    RETURN v_reversal_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION acc.fn_reverse_journal_entry IS 'Create a reversal entry for an existing journal entry';

-- ============================================================================
-- TRIGGERS: PREVENT JOURNAL ENTRY MODIFICATION
-- ============================================================================

-- Trigger 1: Prevent journal entry updates (except reversed_by)
CREATE OR REPLACE FUNCTION acc.fn_prevent_journal_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow only reversed_by to be updated (for linking reversals)
    IF OLD.reversed_by IS NULL AND NEW.reversed_by IS NOT NULL THEN
        RETURN NEW;
    END IF;
    
    RAISE EXCEPTION 'Journal entries cannot be modified. Use reversal entries instead.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_journal_update ON acc.journal;
CREATE TRIGGER trg_prevent_journal_update
    BEFORE UPDATE ON acc.journal
    FOR EACH ROW
    EXECUTE FUNCTION acc.fn_prevent_journal_update();

COMMENT ON TRIGGER trg_prevent_journal_update ON acc.journal IS 
    'Prevents modification of journal entries except for reversed_by field';

-- Trigger 2: Prevent journal entry deletion
CREATE OR REPLACE FUNCTION acc.fn_prevent_journal_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Journal entries cannot be deleted. Use reversal entries instead.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_journal_delete ON acc.journal;
CREATE TRIGGER trg_prevent_journal_delete
    BEFORE DELETE ON acc.journal
    FOR EACH ROW
    EXECUTE FUNCTION acc.fn_prevent_journal_delete();

COMMENT ON TRIGGER trg_prevent_journal_delete ON acc.journal IS 
    'Prevents deletion of journal entries to maintain immutability';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON acc.journal TO frank;
GRANT ALL ON acc.journal_line TO frank;
GRANT ALL ON SEQUENCE acc.journal_id_seq TO frank;
GRANT ALL ON SEQUENCE acc.journal_line_id_seq TO frank;
