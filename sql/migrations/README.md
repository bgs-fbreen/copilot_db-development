# Database Migrations

This directory contains SQL migration scripts to update the Copilot database schema and data.

## Running Migrations

To run a migration, use `psql` to execute the SQL file against your database:

```bash
# Using environment variables from .env (recommended)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/migrations/011_add_wizard_account_status_unique_constraint.sql

# Or with explicit connection details (replace with your values)
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DATABASE -f sql/migrations/011_add_wizard_account_status_unique_constraint.sql
```

## Migration 011: Fix wizard_account_status Unique Constraint

**Issue:** The `copilot allocate wizard` command was failing with "no unique or exclusion constraint matching ON CONFLICT" when trying to skip accounts with `s 8`.

**Fix:** This migration adds the missing unique constraint on `(account_code, entity, period)` to the `acc.wizard_account_status` table.

**Safe to run:** Yes, this migration is idempotent and can be run multiple times safely. It will:
- Remove any duplicate rows (keeping the first one)
- Add the unique constraint if it doesn't exist
- Skip if the constraint already exists

**Required for:** Skip/unskip account functionality in the allocation wizard

## All Migrations

| Migration | Description | Required |
|-----------|-------------|----------|
| 002 | Fix invoice data | Yes |
| 003 | Add import log statistics | Yes |
| 004 | Add trial entry system | Yes |
| 005 | Add journal posting | Yes |
| 006 | Add check numbers | Yes |
| 007 | Add source institution | Yes |
| 008 | Add pattern notes | Yes |
| 009 | Add bank account entity | Yes |
| 010 | Create wizard_account_status table | Yes |
| 011 | Add wizard_account_status unique constraint | Yes |

## Notes

- All migrations are designed to be idempotent (safe to run multiple times)
- Migrations use `IF NOT EXISTS` and `DO $$ BEGIN ... END $$` blocks for safety
- Always backup your database before running migrations on production
