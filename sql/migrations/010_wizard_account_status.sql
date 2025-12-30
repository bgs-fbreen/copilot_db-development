-- Track account status decisions made in allocation wizard
CREATE TABLE IF NOT EXISTS acc.wizard_account_status (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    period VARCHAR(10) NOT NULL,  -- '2024', '2024-Q1', '2024-01'
    status VARCHAR(20) NOT NULL,  -- 'skipped', 'verified', 'pending'
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_code, period)
);

CREATE INDEX IF NOT EXISTS idx_wizard_account_status_entity_period 
    ON acc.wizard_account_status(entity, period);

COMMENT ON TABLE acc.wizard_account_status IS 'Tracks account status decisions made during allocation wizard sessions';
