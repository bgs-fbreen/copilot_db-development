-- ============================================================================
-- Part 02: Trial Entry System
-- Created: 2025-12-28
-- Purpose: Trial entry tables for staging bank transactions before journal posting
-- ============================================================================

-- ============================================================================
-- TRIAL ENTRY - Entry Header
-- ============================================================================

CREATE TABLE acc.trial_entry (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL,
    description TEXT,
    entity VARCHAR(50) NOT NULL,
    source_staging_id INTEGER REFERENCES acc.bank_staging(id),
    transfer_match_id INTEGER REFERENCES acc.trial_entry(id),
    check_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.trial_entry IS 'Trial/pending journal entries awaiting validation and posting';
COMMENT ON COLUMN acc.trial_entry.source_staging_id IS 'Reference to bank_staging record that generated this entry';
COMMENT ON COLUMN acc.trial_entry.transfer_match_id IS 'For transfers: links to the matching entry in other account';
COMMENT ON COLUMN acc.trial_entry.check_number IS 'Check number carried from bank_staging';
COMMENT ON COLUMN acc.trial_entry.status IS 'pending=needs review, balanced=ready to post, posted=in journal, error=validation failed';

CREATE INDEX idx_trial_entry_date ON acc.trial_entry(entry_date);
CREATE INDEX idx_trial_entry_entity ON acc.trial_entry(entity);
CREATE INDEX idx_trial_entry_status ON acc.trial_entry(status);
CREATE INDEX idx_trial_entry_staging ON acc.trial_entry(source_staging_id);
CREATE INDEX idx_trial_entry_check ON acc.trial_entry(check_number);

-- ============================================================================
-- TRIAL ENTRY LINE - Debit/Credit Lines
-- ============================================================================

CREATE TABLE acc.trial_entry_line (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES acc.trial_entry(id) ON DELETE CASCADE,
    line_num INTEGER NOT NULL,
    gl_account_code VARCHAR(100) NOT NULL,
    debit NUMERIC(12,2) DEFAULT 0,
    credit NUMERIC(12,2) DEFAULT 0,
    entity VARCHAR(50),
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc.trial_entry_line IS 'Debit and credit lines for trial entries';
COMMENT ON COLUMN acc.trial_entry_line.gl_account_code IS 'GL account code - references acc.bank_account.code';

CREATE INDEX idx_trial_line_entry ON acc.trial_entry_line(entry_id);
CREATE INDEX idx_trial_line_gl ON acc.trial_entry_line(gl_account_code);

-- Constraint: Each line must have debit OR credit, not both
ALTER TABLE acc.trial_entry_line ADD CONSTRAINT chk_debit_or_credit 
    CHECK ((debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0) OR (debit = 0 AND credit = 0));

-- ============================================================================
-- VALIDATION VIEWS
-- ============================================================================

-- Entry balance check
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

-- Entries with invalid GL codes
CREATE OR REPLACE VIEW acc.vw_trial_invalid_gl AS
SELECT 
    e.id as entry_id,
    e.entry_date,
    e.description,
    l.gl_account_code,
    'GL code not found' as error
FROM acc.trial_entry e
JOIN acc.trial_entry_line l ON l.entry_id = e.id
LEFT JOIN acc.bank_account g ON g.code = l.gl_account_code
WHERE g.code IS NULL;

-- Entries ready to post
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

-- Unmatched transfers
CREATE OR REPLACE VIEW acc.vw_unmatched_transfers AS
SELECT 
    s.id as staging_id,
    s.source_account_code,
    s.normalized_date,
    s.description,
    s.amount,
    s.entity,
    s.gl_account_code,
    CASE WHEN s.amount < 0 THEN 'OUTBOUND' ELSE 'INBOUND' END as direction
FROM acc.bank_staging s
WHERE s.gl_account_code ILIKE '%transfer%'
  AND NOT EXISTS (
      SELECT 1 FROM acc.bank_staging m
      WHERE m.amount = -s.amount
        AND m.normalized_date BETWEEN s.normalized_date - 2 AND s.normalized_date + 2
        AND m.entity = s.entity
        AND m.source_account_code != s.source_account_code
        AND m.gl_account_code ILIKE '%transfer%'
  );

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Generate trial entries from bank_staging
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

COMMENT ON FUNCTION acc.fn_generate_trial_entries IS 'Generate trial entries from bank_staging records that have GL codes assigned';

-- Validate and update entry status
CREATE OR REPLACE FUNCTION acc.fn_validate_trial_entries()
RETURNS TABLE(validated INTEGER, errors INTEGER) AS $$
DECLARE
    v_validated INTEGER := 0;
    v_errors INTEGER := 0;
    v_entry RECORD;
BEGIN
    FOR v_entry IN 
        SELECT * FROM acc.vw_trial_entry_balance WHERE status = 'pending'
    LOOP
        IF v_entry.balance_status = 'BALANCED' THEN
            -- Check for invalid GL codes
            IF EXISTS (SELECT 1 FROM acc.vw_trial_invalid_gl WHERE entry_id = v_entry.id) THEN
                UPDATE acc.trial_entry 
                SET status = 'error', error_message = 'Invalid GL account code', updated_at = CURRENT_TIMESTAMP
                WHERE id = v_entry.id;
                v_errors := v_errors + 1;
            ELSE
                UPDATE acc.trial_entry 
                SET status = 'balanced', error_message = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = v_entry.id;
                v_validated := v_validated + 1;
            END IF;
        ELSE
            UPDATE acc.trial_entry 
            SET status = 'error', error_message = 'Entry does not balance: ' || v_entry.difference::TEXT, updated_at = CURRENT_TIMESTAMP
            WHERE id = v_entry.id;
            v_errors := v_errors + 1;
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT v_validated, v_errors;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION acc.fn_validate_trial_entries IS 'Validate pending trial entries and update their status';

-- Match transfer pairs
CREATE OR REPLACE FUNCTION acc.fn_match_transfer_pairs(p_entity VARCHAR(50) DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    v_matched INTEGER := 0;
    v_transfer RECORD;
    v_match_id INTEGER;
BEGIN
    -- Find outbound transfers and match with inbound
    FOR v_transfer IN
        SELECT e.id, e.entry_date, e.entity, 
               (SELECT SUM(credit) FROM acc.trial_entry_line WHERE entry_id = e.id) as amount
        FROM acc.trial_entry e
        WHERE e.transfer_match_id IS NULL
          AND e.status IN ('pending', 'balanced')
          AND (p_entity IS NULL OR e.entity = p_entity)
          AND EXISTS (
              SELECT 1 FROM acc.trial_entry_line l 
              WHERE l.entry_id = e.id AND l.gl_account_code ILIKE '%transfer%'
          )
    LOOP
        -- Find matching entry (opposite direction, same amount, same entity, within 2 days)
        SELECT e2.id INTO v_match_id
        FROM acc.trial_entry e2
        WHERE e2.id != v_transfer.id
          AND e2.transfer_match_id IS NULL
          AND e2.entity = v_transfer.entity
          AND e2.entry_date BETWEEN v_transfer.entry_date - 2 AND v_transfer.entry_date + 2
          AND EXISTS (
              SELECT 1 FROM acc.trial_entry_line l2 
              WHERE l2.entry_id = e2.id 
                AND l2.debit = v_transfer.amount
                AND l2.gl_account_code ILIKE '%transfer%'
          )
        LIMIT 1;
        
        IF v_match_id IS NOT NULL THEN
            -- Link both entries
            UPDATE acc.trial_entry SET transfer_match_id = v_match_id, updated_at = CURRENT_TIMESTAMP WHERE id = v_transfer.id;
            UPDATE acc.trial_entry SET transfer_match_id = v_transfer.id, updated_at = CURRENT_TIMESTAMP WHERE id = v_match_id;
            v_matched := v_matched + 1;
        END IF;
    END LOOP;
    
    RETURN v_matched;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION acc.fn_match_transfer_pairs IS 'Match internal transfer pairs within an entity';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON acc.trial_entry TO frank;
GRANT ALL ON acc.trial_entry_line TO frank;
GRANT ALL ON SEQUENCE acc.trial_entry_id_seq TO frank;
GRANT ALL ON SEQUENCE acc.trial_entry_line_id_seq TO frank;
