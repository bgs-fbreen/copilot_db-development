# Staging to Journal Workflow

Complete guide for processing bank transactions from import through final journal posting.

## Overview

The accounting workflow consists of three parts:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PART 01       │     │   PART 02       │     │   PART 03       │
│   bank_staging  │ →   │  trial_entry    │ →   │   journal       │
│                 │     │                 │     │                 │
│  • Import CSV   │     │  • Build DR/CR  │     │  • Permanent    │
│  • Fuzzy match  │     │  • Validate     │     │  • Immutable    │
│  • Assign GL    │     │  • Flag issues  │     │  • Auditable    │
│  • Manual fixes │     │  • Match xfers  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       ↑                        ↑                        ↑
   Editable               Review/Fix               Locked
   "Working"              "Pending"               "Posted"
```

## Part 01: Bank Staging

### Purpose
Import bank CSV files and allocate transactions to GL accounts.

### Tables
- `acc.bank_staging` - Imported bank transactions with GL allocation

### Import Process

```bash
# Import a bank CSV file
copilot import csv ~/Downloads/bank_statement.csv --account bgs:checking

# List recent imports
copilot import list
```

### GL Code Assignment

Transactions are assigned GL codes through:

1. **Pattern Matching** - Automatic matching based on `acc.bank_patterns`
2. **Manual Assignment** - User assigns GL code directly

```bash
# View transactions needing GL assignment
copilot staging todos --entity bgs

# Assign GL code manually
copilot staging assign 123 expense:office

# View staging summary
copilot staging summary --entity bgs
```

### Commands

| Command | Description |
|---------|-------------|
| `copilot staging list` | List staged transactions |
| `copilot staging todos` | Show transactions needing GL assignment |
| `copilot staging assign <id> <gl_code>` | Assign GL code to transaction |
| `copilot staging summary` | Summary by entity and status |
| `copilot staging transfers` | Show unmatched transfers |

### Double-Entry Logic

Bank staging provides ONE side of the transaction:

```
Bank CSV:  -$500  "OFFICE DEPOT"
           ↓
bank_staging:
  source_account_code: bgs:checking    ← CREDIT (cash out)
  amount: -$500
  gl_account_code: expense:office      ← DEBIT (expense)
```

---

## Part 02: Trial Entry

### Purpose
Generate double-entry trial entries from bank staging for review before posting.

### Tables
- `acc.trial_entry` - Entry headers with status tracking
- `acc.trial_entry_line` - Debit/credit lines

### Status Flow

```
pending → balanced → posted
            ↓
          error
```

### Generate Trial Entries

```bash
# Preview what will be generated
copilot trial generate --entity bgs --dry-run

# Generate trial entries
copilot trial generate --entity bgs

# Generate for date range
copilot trial generate --entity bgs --date-from 2024-01-01 --date-to 2024-12-31
```

### Validate Entries

```bash
# Validate all pending entries
copilot trial validate

# View validation errors
copilot trial errors --entity bgs

# View entries ready to post
copilot trial ready --entity bgs
```

### Transfer Matching

Internal transfers between accounts create duplicate entries. The system matches these:

```bash
# Match transfer pairs
copilot trial match-transfers --entity bgs

# View unmatched transfers
copilot staging transfers --entity bgs
```

### Commands

| Command | Description |
|---------|-------------|
| `copilot trial generate` | Generate trial entries from staging |
| `copilot trial validate` | Validate pending entries |
| `copilot trial list` | List trial entries |
| `copilot trial errors` | Show entries with errors |
| `copilot trial match-transfers` | Match internal transfer pairs |
| `copilot trial summary` | Summary by entity and status |
| `copilot trial ready` | Show entries ready to post |

### Views

| View | Description |
|------|-------------|
| `acc.vw_trial_entry_balance` | Entry balance validation |
| `acc.vw_trial_invalid_gl` | Entries with invalid GL codes |
| `acc.vw_trial_ready_to_post` | Validated entries ready for journal |
| `acc.vw_unmatched_transfers` | Orphaned transfer transactions |

### SQL Functions

```sql
-- Generate trial entries
SELECT * FROM acc.fn_generate_trial_entries('bgs', '2024-01-01', '2024-12-31');

-- Validate entries
SELECT * FROM acc.fn_validate_trial_entries();

-- Match transfer pairs
SELECT acc.fn_match_transfer_pairs('bgs');
```

---

## Part 03: Journal

### Purpose
Final, immutable record of all accounting transactions.

### Tables
- `acc.journal` - Entry headers with reversal tracking
- `acc.journal_line` - Debit/credit lines (immutable)

### Immutability Rules

1. **No Updates** - Journal entries cannot be modified
2. **No Deletes** - Journal entries cannot be deleted
3. **Reversals Only** - Errors are corrected by creating reversal entries

### Post to Journal

```bash
# Preview what will be posted
copilot journal post --entity bgs --dry-run

# Post validated entries
copilot journal post --entity bgs

# Post with user tracking
copilot journal post --entity bgs --posted-by admin
```

### View Journal

```bash
# List journal entries
copilot journal list --entity bgs

# View specific entry with lines
copilot journal view 123

# Filter by date
copilot journal list --entity bgs --date-from 2024-01-01 --date-to 2024-12-31
```

### Reversals

```bash
# Reverse an entry
copilot journal reverse 123 --reason "Incorrect amount"

# View reversed entries
copilot journal list --entity bgs  # Status shows REVERSED or REVERSAL
```

### Reports

```bash
# GL account balances
copilot journal balances --entity bgs

# Trial balance report
copilot journal trial-balance --entity bgs

# Journal summary
copilot journal summary --entity bgs
```

### Commands

| Command | Description |
|---------|-------------|
| `copilot journal post` | Post validated trial entries |
| `copilot journal list` | List journal entries |
| `copilot journal view <id>` | View entry with lines |
| `copilot journal reverse <id>` | Create reversal entry |
| `copilot journal balances` | Show GL account balances |
| `copilot journal trial-balance` | Show trial balance report |
| `copilot journal summary` | Show journal statistics |

### Views

| View | Description |
|------|-------------|
| `acc.vw_journal_entry_balance` | Entry balance validation |
| `acc.vw_gl_balances` | GL account balances (excludes reversed) |
| `acc.vw_trial_balance` | Debit/credit trial balance |

### SQL Functions

```sql
-- Post to journal
SELECT * FROM acc.fn_post_to_journal('bgs', 'admin');

-- Reverse an entry
SELECT acc.fn_reverse_journal_entry(123, 'Incorrect amount', 'admin');
```

---

## Complete Workflow Example

### Step 1: Import Bank Data

```bash
# Import CSV files for all accounts
copilot import csv ~/Downloads/bgs_checking_2024.csv --account bgs:checking
copilot import csv ~/Downloads/bgs_savings_2024.csv --account bgs:savings

# Check for unassigned transactions
copilot staging todos --entity bgs
```

### Step 2: Assign GL Codes

```bash
# Assign GL codes to TODO transactions
copilot staging assign 101 expense:utilities
copilot staging assign 102 expense:supplies
copilot staging assign 103 income:sales

# Verify all assigned
copilot staging summary --entity bgs
```

### Step 3: Generate Trial Entries

```bash
# Generate trial entries
copilot trial generate --entity bgs

# Validate
copilot trial validate

# Check for errors
copilot trial errors --entity bgs
```

### Step 4: Match Transfers

```bash
# Match internal transfers
copilot trial match-transfers --entity bgs

# Review unmatched
copilot staging transfers --entity bgs
```

### Step 5: Post to Journal

```bash
# Preview
copilot journal post --entity bgs --dry-run

# Post
copilot journal post --entity bgs --posted-by admin
```

### Step 6: Verify

```bash
# Check trial balance
copilot journal trial-balance --entity bgs

# Should show BALANCED with equal debits/credits
```

---

## Troubleshooting

### TODO Transactions Won't Generate

**Problem:** `copilot trial generate` skips transactions

**Solution:** Assign GL codes first
```bash
copilot staging todos --entity bgs
copilot staging assign <id> <gl_code>
```

### Unbalanced Trial Entry

**Problem:** Entry shows UNBALANCED in `vw_trial_entry_balance`

**Solution:** Check the original staging transaction
```sql
-- Replace {staging_id} with the actual ID from the trial entry
SELECT * FROM acc.bank_staging WHERE id = {staging_id};
```
If the source data is correct, the entry may need manual correction in the staging table.

### Invalid GL Codes

**Problem:** Entry appears in `vw_trial_invalid_gl`

**Solution:** Update GL code in staging
```bash
copilot staging assign <id> <valid_gl_code>
# Then regenerate the trial entry
```

### Unmatched Transfers

**Problem:** Transfers show in `vw_unmatched_transfers`

**Solution:** Verify both sides of the transfer exist
```bash
copilot staging transfers --entity bgs
# Check if opposite transaction was imported
# If missing, import the other bank account's CSV
```

### Cannot Post Entry

**Problem:** Entry not in `vw_trial_ready_to_post`

**Solution:** Check validation status
```bash
copilot trial errors --entity bgs
```
Fix any balance or GL code issues, then validate again.

---

## CLI Command Reference

### Part 01: Staging
```bash
# Import commands
copilot import csv
copilot import list

# Staging commands
copilot staging list
copilot staging todos
copilot staging assign
copilot staging summary
copilot staging transfers
```

### Part 02: Trial
```bash
copilot trial generate
copilot trial validate
copilot trial list
copilot trial errors
copilot trial match-transfers
copilot trial summary
copilot trial ready
```

### Part 03: Journal
```bash
copilot journal post
copilot journal list
copilot journal view
copilot journal reverse
copilot journal balances
copilot journal trial-balance
copilot journal summary
```

### Status Progression

```
bank_staging (gl_account_code)
  TODO → pattern/manual
           ↓
trial_entry (status)
  pending → balanced → posted
              ↓
            error
           ↓
journal (immutable)
  ACTIVE → REVERSED (via reversal entry)
```
