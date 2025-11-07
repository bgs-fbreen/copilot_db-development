-- ============================================================================
-- Discovery Script for db_accounts_old.bgs schema
-- ============================================================================

-- List all tables in bgs schema
\echo '========================================='
\echo 'TABLES IN bgs SCHEMA'
\echo '========================================='
SELECT tablename, schemaname 
FROM pg_tables 
WHERE schemaname = 'bgs' 
ORDER BY tablename;

\echo ''
\echo '========================================='
\echo 'RECORD COUNTS'
\echo '========================================='
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'bgs'
ORDER BY tablename;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_client'
\echo '========================================='
\d bgs.tbl_client
SELECT * FROM bgs.tbl_client LIMIT 5;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_project'
\echo '========================================='
\d bgs.tbl_project
SELECT * FROM bgs.tbl_project WHERE project_status = 'active' LIMIT 5;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_res (resources)'
\echo '========================================='
\d bgs.tbl_res
SELECT * FROM bgs.tbl_res LIMIT 5;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_task'
\echo '========================================='
\d bgs.tbl_task
SELECT * FROM bgs.tbl_task LIMIT 10;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_base (baseline)'
\echo '========================================='
\d bgs.tbl_base
SELECT * FROM bgs.tbl_base LIMIT 10;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_ts (timesheets)'
\echo '========================================='
\d bgs.tbl_ts
SELECT * FROM bgs.tbl_ts ORDER BY ts_date DESC LIMIT 10;

\echo ''
\echo '========================================='
\echo 'TABLE: tbl_invoice'
\echo '========================================='
\d bgs.tbl_invoice
SELECT * FROM bgs.tbl_invoice LIMIT 5;
