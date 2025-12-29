# Trial Entry System - Part 02

## Overview
The trial entry system is Part 02 of the staging workflow for bank transaction processing. It provides an intermediate step between `bank_staging` (single-sided bank imports) and `journal` (final double-entry records).

## Architecture

### Tables

#### `acc.trial_entry`
Entry header table that stores metadata about each trial journal entry.

**Key Fields:**
- `id` - Primary key
- `entry_date` - Transaction date
- `description` - Description of the transaction
- `entity` - Entity code (e.g., 'bgs', 'mhb')
- `source_staging_id` - Links back to the original `bank_staging` record
- `transfer_match_id` - Links to matching transfer entry (for internal transfers)
- `status` - Entry status: pending, balanced, posted, error
- `error_message` - Validation error details

#### `acc.trial_entry_line`
Debit and credit lines for each trial entry. Each entry has multiple lines that must balance.

**Key Fields:**
- `id` - Primary key
- `entry_id` - Foreign key to `trial_entry`
- `line_num` - Line sequence number
- `gl_account_code` - GL account code (references `acc.bank_account.code`)
- `debit` - Debit amount
- `credit` - Credit amount
- `entity` - Entity code
- `memo` - Line memo/description

**Constraints:**
- Each line must have debit OR credit, not both (enforced via check constraint)
- Debit and credit amounts must be >= 0
- Note: The constraint allows zero-amount lines (both debit and credit = 0) as per specification, though these should be avoided in normal accounting practice

### Views

#### `acc.vw_trial_entry_balance`
Shows the balance status of each trial entry, including total debits, credits, and difference.

**Balance Status Values:**
- `BALANCED` - Debits equal credits and total > 0
- `EMPTY` - No debits or credits
- `UNBALANCED` - Debits don't equal credits

#### `acc.vw_trial_invalid_gl`
Lists trial entries with invalid GL account codes (codes that don't exist in `acc.bank_account`).

#### `acc.vw_trial_ready_to_post`
Shows entries that are balanced, have no errors, and are ready to post to the journal.

#### `acc.vw_unmatched_transfers`
Identifies transfer transactions in `bank_staging` that don't have matching opposite-direction transfers.

### Functions

#### `acc.fn_generate_trial_entries(p_entity, p_date_from, p_date_to)`
Generates trial entries from `bank_staging` records that have GL codes assigned (not 'TODO').

**Parameters:**
- `p_entity` - Optional: Filter by entity code
- `p_date_from` - Optional: Filter by date range start
- `p_date_to` - Optional: Filter by date range end

**Returns:** Table with `entries_created` and `entries_skipped` counts

**Logic:**
- For negative amounts (expenses): Debit GL account, Credit bank account
- For positive amounts (income): Debit bank account, Credit GL account

#### `acc.fn_validate_trial_entries()`
Validates pending trial entries and updates their status.

**Returns:** Table with `validated` and `errors` counts

**Validation Rules:**
- Entry must balance (debits = credits)
- All GL codes must exist in `acc.bank_account`

#### `acc.fn_match_transfer_pairs(p_entity)`
Matches internal transfer pairs within an entity.

**Parameters:**
- `p_entity` - Optional: Filter by entity code

**Returns:** Count of matched transfer pairs

**Matching Criteria:**
- Same entity
- Opposite amounts (debit matches credit)
- Within 2 days of each other
- Both entries have GL codes containing 'transfer'

## Workflow

### Step 1: Import and Categorize
1. Import bank transactions into `acc.bank_staging`
2. Assign GL codes (manually or via pattern matching)

### Step 2: Generate Trial Entries
```sql
SELECT * FROM acc.fn_generate_trial_entries('bgs');
```

### Step 3: Validate Entries
```sql
SELECT * FROM acc.fn_validate_trial_entries();
```

### Step 4: Match Transfers
```sql
SELECT acc.fn_match_transfer_pairs('bgs');
```

### Step 5: Review and Correct
- Check `acc.vw_trial_entry_balance` for unbalanced entries
- Check `acc.vw_trial_invalid_gl` for invalid GL codes
- Check `acc.vw_unmatched_transfers` for missing transfer pairs

### Step 6: Post to Journal
- Query `acc.vw_trial_ready_to_post` for entries ready to post
- Post balanced entries to the journal table (Part 03)

## Installation

### New Database
Run the schema file:
```bash
psql -h your_host -U your_user -d copilot_db -f sql/schema/06_trial_entry.sql
```

### Existing Database
Run the migration:
```bash
psql -h your_host -U your_user -d copilot_db -f sql/migrations/004_add_trial_entry.sql
```

## Testing

A comprehensive test script is provided:
```bash
psql -h your_host -U your_user -d copilot_db -f sql/test_trial_entry.sql
```

The test script includes:
- Sample data setup
- All function tests
- All view tests
- Error handling tests

## Example Usage

### Generate and validate entries for a specific month
```sql
-- Generate entries for January 2025
SELECT * FROM acc.fn_generate_trial_entries('bgs', '2025-01-01', '2025-01-31');

-- Validate all pending entries
SELECT * FROM acc.fn_validate_trial_entries();

-- Check results
SELECT * FROM acc.vw_trial_entry_balance 
WHERE entry_date BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY entry_date;
```

### Find and match transfers
```sql
-- Find unmatched transfers
SELECT * FROM acc.vw_unmatched_transfers;

-- Match transfer pairs
SELECT acc.fn_match_transfer_pairs('bgs');
```

### Review entries ready to post
```sql
SELECT * FROM acc.vw_trial_ready_to_post
ORDER BY entry_date;
```

## Notes

- GL codes are validated against `acc.bank_account.code`, not a separate GL accounts table
- The system uses the existing `acc.bank_account` table for both bank accounts and GL accounts
- Transfer matching is performed within the same entity only
- The 2-day window for transfer matching accommodates timing differences between accounts
