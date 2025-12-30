-- Add entity column to bank_account
ALTER TABLE acc.bank_account ADD COLUMN IF NOT EXISTS entity VARCHAR(50);

-- Auto-populate from code prefix for existing accounts
UPDATE acc.bank_account SET entity = 'bgs' WHERE code LIKE 'bgs:%' AND entity IS NULL;
UPDATE acc.bank_account SET entity = 'mhb' WHERE code LIKE 'mhb:%' AND entity IS NULL;
UPDATE acc.bank_account SET entity = 'per' WHERE code LIKE 'per:%' AND entity IS NULL;
UPDATE acc.bank_account SET entity = 'csb' WHERE code LIKE 'csb:%' AND entity IS NULL;

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_bank_account_entity ON acc.bank_account(entity);
