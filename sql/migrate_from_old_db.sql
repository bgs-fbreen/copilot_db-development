-- ============================================================================
-- Migration Script: db_accounts_old → copilot_db
-- Execute this script while connected to copilot_db
-- ============================================================================

\echo '========================================='
\echo 'STEP 1: Migrate CLIENTS'
\echo '========================================='

\c db_accounts_old

-- Create temp table with client data
CREATE TEMP TABLE temp_clients AS
SELECT DISTINCT fk_client FROM bgs.tbl_project WHERE fk_client IS NOT NULL;

\c copilot_db

-- This won't work across databases. Let me use a different approach.
