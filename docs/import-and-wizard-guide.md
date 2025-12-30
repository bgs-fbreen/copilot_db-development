# Import and Allocation Wizard Guide

## Table of Contents

1. [Overview](#overview)
2. [Import Command](#import-command)
3. [Import CSV Subcommand](#import-csv-subcommand)
4. [Allocation Wizard](#allocation-wizard)
5. [Complete Workflow Examples](#complete-workflow-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

The **Import and Allocation Wizard** provides a streamlined workflow for:
1. **Importing bank transactions** from CSV files into the `bank_staging` table
2. **Allocating transactions** to appropriate GL accounts through an intelligent guided wizard
3. **Categorizing transactions** using pattern matching and manual assignment

This two-step process ensures accurate financial data entry while minimizing manual effort through automation and smart detection.

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Import & Allocation Flow                  │
└─────────────────────────────────────────────────────────────┘

  Step 1: Import Bank Data
  ┌──────────────────────┐
  │  CSV Files           │
  │  (Bank Statements)   │
  └──────────┬───────────┘
             │
             ↓
  ┌──────────────────────┐
  │  copilot import csv  │
  │  --account <code>    │
  └──────────┬───────────┘
             │
             ↓
  ┌──────────────────────┐
  │  bank_staging table  │
  │  (GL: 'TODO')        │
  └──────────┬───────────┘

  Step 2: Allocate Transactions
             │
             ↓
  ┌─────────────────────────────┐
  │  copilot allocate wizard    │
  │  --period <year>            │
  └─────────┬───────────────────┘
            │
            ├─→ Import Status Check
            ├─→ Intercompany Detection
            ├─→ Loan/Mortgage Detection
            ├─→ Recurring Vendor Detection
            └─→ Manual Assignment (staging)
                    │
                    ↓
            ┌──────────────────┐
            │  bank_staging    │
            │  (GL: assigned)  │
            └──────────────────┘

  Step 3: Generate Accounting Entries
                    │
                    ↓
            ┌──────────────────┐
            │  copilot trial   │
            │  generate        │
            └──────────────────┘
```

---

## Import Command

### Running Without Arguments

When you run `copilot import` without any subcommand, it displays comprehensive help information:

```bash
copilot import
```

**What It Shows:**

1. **Syntax Reference** - Command format and options
2. **Period Format Guide** - How to specify date ranges
3. **Available Accounts** - Active bank accounts from your database
4. **CSV Files** - Files in current directory with sizes
5. **Workflow Steps** - Complete process guide

**Example Output:**

```
═══════════════════════════════════════════════════════════════
   Bank Transaction Import
═══════════════════════════════════════════════════════════════

SYNTAX:
  copilot import csv <file> --account <code> [--period <period>] [--dry-run]

PERIOD FORMAT:
  YYYY       Year (e.g., 2024)
  YYYY-QN    Quarter (e.g., 2024-Q4)
  YYYY-MM    Month (e.g., 2024-12)

AVAILABLE ACCOUNTS:
  bgs:checking      BGS Checking Account (Wells Fargo)
  bgs:savings       BGS Savings Account (Wells Fargo)
  mhb:checking      MHB Operating Account (Chase)

CSV FILES IN CURRENT DIRECTORY:
  statement_jan.csv (45.2 KB)
  statement_feb.csv (48.7 KB)

WORKFLOW:
  1. Check available accounts above
  2. Preview import: copilot import csv <file> --account <code> --dry-run
  3. Review the transaction preview
  4. Run without --dry-run to import: copilot import csv <file> --account <code>
  5. Optional: Add --period to filter transactions (e.g., --period 2024-Q4)
  6. Run allocation wizard: copilot allocate wizard --period <year>
```

---

## Import CSV Subcommand

### Full Syntax

```bash
copilot import csv <file> --account <code> [--period <period>] [--dry-run]
```

### Parameters

#### Required

- **`<file>`** - Path to CSV file containing bank transactions
  - Example: `~/Downloads/statement.csv`
  - Must exist and be readable
  - Supports UTF-8 encoding with or without BOM

- **`--account <code>`** or **`-a <code>`** - Bank account code
  - Must match an active account in `acc.bank_account`
  - Format: `entity:account_name`
  - Example: `bgs:checking`, `mhb:savings`

#### Optional

- **`--period <period>`** or **`-p <period>`** - Filter transactions by date
  - **Year**: `YYYY` (e.g., `2024`)
    - Includes Jan 1 to Dec 31
  - **Quarter**: `YYYY-QN` (e.g., `2024-Q4`)
    - Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec
  - **Month**: `YYYY-MM` (e.g., `2024-12`)
    - Includes first to last day of month

- **`--dry-run`** - Preview import without saving
  - Shows detailed statistics
  - Identifies duplicates
  - No database changes made

### CSV Format Detection

The import command **automatically detects** CSV column formats. It recognizes common patterns for:

#### Date Columns
- `date`, `transaction date`, `trans date`, `posting date`

#### Amount Columns
- **Single amount column**: `amount`, `transaction amount`, `value`
- **Debit/Credit columns**: `debit`, `credit`, `withdrawal`, `deposit`

#### Description Columns
- `payee`, `description`, `merchant`, `name`, `details`
- `memo`, `note`, `comment`

#### Check Number Columns
- `check number`, `check #`, `check no`, `reference`

#### Date Formats Supported
- ISO: `2024-01-15` (YYYY-MM-DD)
- US: `01/15/2024` (MM/DD/YYYY)
- US Short: `01/15/24` (MM/DD/YY)
- EU: `15/01/2024` (DD/MM/YYYY)
- Text: `Jan 15, 2024`, `January 15, 2024`

### Import Process

#### Step 1: Validation
- Verifies account exists in database
- Computes file hash to detect duplicates
- Warns if file was previously imported
- Detects CSV format and column mappings

#### Step 2: Parsing
- Reads all rows from CSV
- Parses dates in multiple formats
- Handles currency symbols and formatting
- Processes debit/credit or single amount
- Smart check number detection

#### Step 3: Duplicate Detection
- Checks existing `bank_staging` records
- Matches on: account + date + amount + description
- Marks duplicates in preview

#### Step 4: Preview (if --dry-run)
- Shows first 10 transactions
- Displays detailed statistics:
  - Date range and span
  - Transaction counts
  - Debit/credit totals and averages
  - Net cash flow
- No database changes

#### Step 5: Import (if confirmed)
- Inserts new transactions into `acc.bank_staging`
- Sets `gl_account_code = 'TODO'`
- Logs import details in `acc.import_log`
- Tracks statistics for reporting

### Import Examples

#### Basic Import

```bash
# Import checking account statement
copilot import csv ~/Downloads/checking_jan.csv --account bgs:checking
```

#### Preview Before Import

```bash
# Dry run to review transactions
copilot import csv statement.csv --account bgs:checking --dry-run

# After reviewing, import without --dry-run
copilot import csv statement.csv --account bgs:checking
```

#### Filter by Period

```bash
# Import only Q4 2024 transactions
copilot import csv statement.csv --account bgs:checking --period 2024-Q4

# Import only December 2024
copilot import csv statement.csv --account bgs:checking --period 2024-12

# Import all of 2024
copilot import csv statement.csv --account bgs:checking --period 2024
```

### Import Output

**Successful Import:**
```
═══════════════════════════════════════
   Bank Transaction Import
═══════════════════════════════════════

Account: BGS Checking Account (bgs:checking)
File: statement_jan.csv

✓ CSV format detected
  Date column: Transaction Date
  Description column: Description
  Debit column: Debit Amount
  Credit column: Credit Amount

Found 156 transactions

Date         Description                Amount      Check #  Status
────────────────────────────────────────────────────────────────────
2024-01-31   AMAZON MARKETPLACE         -$45.67     -        New
2024-01-30   PAYCHECK DEPOSIT           $2,500.00   -        New
2024-01-29   UTILITIES PAYMENT          -$125.43    -        Duplicate
...

Summary:
  New transactions: 143
  Duplicates (skipped): 13

Import 143 transactions? [Y/n]: y

✓ Successfully imported 143 transactions!
```

**Dry Run Output:**
```
═══════════════════════════════════════
   Detailed Statistics
═══════════════════════════════════════

Date Range:
  From: 2024-01-01
  To:   2024-01-31
  Span: 30 days

Transaction Counts:
  Total:   143
  Debits:  98
  Credits: 45

Debits (Outflows):
  Total:    -$12,456.78
  Largest:  -$1,200.00
  Smallest: -$5.50
  Average:  -$127.11

Credits (Inflows):
  Total:    $15,000.00
  Largest:  $5,000.00
  Smallest: $10.00
  Average:  $333.33

Net Flow:
  +$2,543.22

Dry run - no changes made
```

### Additional Import Commands

#### List Import History

```bash
# Show all recent imports
copilot import list

# Show imports for specific account
copilot import list --account bgs:checking
```

**Output:**
```
ID   Account                Date                 File              Imported  Skipped  Date Range
─────────────────────────────────────────────────────────────────────────────────────────────────
15   bgs:checking          2024-02-01 14:30     jan_stmt.csv      143       13       2024-01-01 to 2024-01-31
14   mhb:checking          2024-01-28 10:15     dec_stmt.csv      89        5        2023-12-01 to 2023-12-31
```

#### Check Import Status

```bash
# Show staging status summary
copilot import status

# Show status for specific account
copilot import status --account bgs:checking
```

**Output:**
```
Status                   Count    Total Amount
─────────────────────────────────────────────
Unmatched (TODO)         245      $3,456.78
Pattern Matched          512      $45,678.90
Manually Assigned        89       $12,345.67
```

---

## Allocation Wizard

### Overview

The **Allocation Wizard** is a guided, step-by-step interface for categorizing imported transactions. It intelligently detects common transaction patterns and assists with GL code assignment.

### Command Syntax

```bash
copilot allocate wizard --period <period> [--entity <code>]
```

### Parameters

- **`--period <period>`** or **`-p <period>`** (Required)
  - Same format as import: `YYYY`, `YYYY-QN`, or `YYYY-MM`
  - Example: `2024`, `2024-Q4`, `2024-12`

- **`--entity <code>`** or **`-e <code>`** (Optional)
  - Filter to specific entity
  - Example: `bgs`, `mhb`
  - If omitted, wizard shows all entities

### Wizard Steps

The wizard guides you through **5 comprehensive steps**:

#### Step 1: Import Status

**Purpose**: Verify that bank statements have been imported for the period.

**Display**:
- Shows all accounts and their import status
- Displays record counts and date ranges
- Identifies complete, partial, or missing imports

**Status Indicators**:
- ✓ **Complete** - Data covers full period
- ⚠ **Partial** - Incomplete date range
- ✗ **Not imported** - No data
- ⊘ **Skipped** - Manually excluded

**Commands**:
- `c` - Continue with imported accounts
- `s #,#` - Skip account(s) (e.g., `s 3,4`)
- `u #` - Unskip account
- `q` - Quit wizard

**Example**:
```
STEP 1 of 5: Import Status
───────────────────────────────────────────────────────────────

#   Entity  Account         Records  Date Range               Status
────────────────────────────────────────────────────────────────────
1   bgs     bgs:checking    143      2024-01-01 → 2024-12-31  ✓ Complete
2   bgs     bgs:savings     45       2024-01-01 → 2024-12-31  ✓ Complete
3   mhb     mhb:checking    0                                 ✗ Not imported

Commands:
  [c] Continue with imported accounts
  [s #,#] Skip account(s) - e.g., 's 3'
  [u #] Unskip account - e.g., 'u 3'
  [q] Quit

Enter command [c]: c
```

#### Step 2: Intercompany Detection

**Purpose**: Automatically identify and categorize transfers between entities.

**Detection Logic**:
- Finds matching amounts on same date
- Opposite signs (debit from one, credit to other)
- Different entities
- Both transactions unallocated (gl_account_code = 'TODO')

**Assignment**:
- Creates intercompany GL code: `ic:entity1-entity2`
- Updates both transactions atomically
- Marks as `match_method = 'intercompany'`

**Actions**:
- `a` - Auto-assign all detected transfers
- `r` - Review one-by-one (manual mode)
- `s` - Skip intercompany detection

**Example**:
```
STEP 2 of 5: Intercompany Detection
───────────────────────────────────────────────────────────────

Found 8 potential intercompany transfers:

Date         From   To    Amount      Description
──────────────────────────────────────────────────────────
2024-01-15   bgs    mhb   $5,000.00   TRANSFER TO MHB
2024-02-20   mhb    bgs   $2,500.00   TRANSFER FROM BGS
...

[a] Auto-assign intercompany    [r] Review one-by-one    [s] Skip

Choice [a]: a

✓ Assigned 8 intercompany transfers (16 transactions)
```

#### Step 3: Loan/Mortgage Payments

**Purpose**: Identify and suggest GL codes for loan and mortgage payments.

**Detection Logic**:
- Description contains keywords: `MORTGAGE`, `LOAN`
- Matches vendor GL patterns with `loan:*` codes
- Unallocated transactions only

**Suggested Codes**:
- From `acc.vendor_gl_patterns` table
- Pattern-based matching on description

**Actions**:
- `a` - Auto-assign loans (requires verification)
- `r` - Review one-by-one
- `s` - Skip loan detection

**Note**: Auto-assign for loans typically requires manual verification. Use staging commands for detailed assignment.

**Example**:
```
STEP 3 of 5: Loan/Mortgage Payments
───────────────────────────────────────────────────────────────

Found 12 potential loan payments:

Date         Account         Payee                    Amount       Suggested
────────────────────────────────────────────────────────────────────────────
2024-01-01   bgs:checking    WELLS FARGO MORTGAGE    -$2,345.67   loan:711pine
2024-02-01   bgs:checking    WELLS FARGO MORTGAGE    -$2,345.67   loan:711pine
...

[a] Auto-assign loans    [r] Review one-by-one    [s] Skip

Choice [s]: s
```

#### Step 4: Recurring Transactions

**Purpose**: Identify high-frequency vendors and assign GL codes using patterns.

**Detection Logic**:
- Groups transactions by description
- Finds vendors with 5+ transactions in period
- Checks for existing patterns in `acc.vendor_gl_patterns`

**Auto-Assignment**:
- Only assigns if pattern exists with suggested code
- Updates all matching transactions
- Marks as `match_method = 'pattern'`

**Actions**:
- `a` - Auto-assign with existing patterns
- `r` - Review one-by-one
- `s` - Skip recurring detection

**Example**:
```
STEP 4 of 5: Recurring Transactions
───────────────────────────────────────────────────────────────

High-frequency vendors (5+ transactions):

#   Entity  Vendor                    Count  Total        Suggested
───────────────────────────────────────────────────────────────────
1   bgs     AMAZON MARKETPLACE        23     -$1,245.67   expense:supplies
2   bgs     PG&E UTILITIES           12     -$1,567.89   expense:utilities
3   mhb     AT&T PHONE SERVICE       12     -$840.00     expense:communications
...

[a] Auto-assign with patterns    [r] Review one-by-one    [s] Skip

Choice [a]: a

✓ Auto-assigned 47 recurring transactions
```

#### Step 5: Remaining Transactions

**Purpose**: Show allocation progress and guide to manual assignment tools.

**Display**:
- Progress bar showing % allocated
- Count of remaining TODO transactions
- Grouped by description (first 10 groups)
- Suggests next steps

**Next Steps**:
- Use `copilot staging assign-todo` for interactive assignment
- Use `copilot staging` commands for detailed management

**Example**:
```
STEP 5 of 5: Remaining Transactions
───────────────────────────────────────────────────────────────

Remaining TODO: 45 transactions in 12 groups

Progress: ████████████████░░░░ 80%

#   Description                             Count  Total
──────────────────────────────────────────────────────────
1   CHECK #1234                             8      -$2,345.67
2   ATM WITHDRAWAL                          12     -$600.00
3   WIRE TRANSFER                           5      -$15,000.00
...

Use 'copilot staging assign-todo --entity bgs' for interactive assignment

[Enter] to view summary    [q] Quit
```

### Wizard Summary

After completing all steps, the wizard displays a comprehensive summary:

```
═══════════════════════════════════════════════════════════════
   Allocation Complete!
═══════════════════════════════════════════════════════════════

Summary for BGS - 2024:

  Total transactions:      1,245
  Allocated:               1,200 (96%)
  Remaining:               45

  By category:
    Intercompany:           16
    Loan payments:          0
    Recurring:              47
    Manual:                 0

  Patterns created:         0

Use 'copilot report' to generate reports or 'copilot staging' for more details
```

---

## Complete Workflow Examples

### Example 1: Monthly Bank Reconciliation

**Scenario**: Import and allocate January 2024 transactions for BGS entity.

```bash
# Step 1: Preview the import
copilot import csv ~/Downloads/bgs_jan_2024.csv \
  --account bgs:checking \
  --period 2024-01 \
  --dry-run

# Step 2: Import the transactions
copilot import csv ~/Downloads/bgs_jan_2024.csv \
  --account bgs:checking \
  --period 2024-01

# Step 3: Run allocation wizard
copilot allocate wizard --entity bgs --period 2024-01

# Step 4: Assign remaining transactions manually
copilot staging assign-todo --entity bgs

# Step 5: Generate trial entries
copilot trial generate --entity bgs \
  --date-from 2024-01-01 \
  --date-to 2024-01-31

# Step 6: Validate and post
copilot trial validate
copilot journal post --entity bgs --posted-by admin
```

### Example 2: Quarterly Processing for Multiple Entities

**Scenario**: Process Q4 2024 for both BGS and MHB entities.

```bash
# Import BGS accounts
copilot import csv bgs_checking_q4.csv --account bgs:checking --period 2024-Q4
copilot import csv bgs_savings_q4.csv --account bgs:savings --period 2024-Q4

# Import MHB accounts
copilot import csv mhb_checking_q4.csv --account mhb:checking --period 2024-Q4

# Run wizard for all entities (detects intercompany automatically)
copilot allocate wizard --period 2024-Q4

# Note: Wizard will show all entities and detect cross-entity transfers

# Manual assignment for each entity
copilot staging assign-todo --entity bgs
copilot staging assign-todo --entity mhb

# Generate and post for each entity
copilot trial generate --entity bgs --date-from 2024-10-01 --date-to 2024-12-31
copilot trial generate --entity mhb --date-from 2024-10-01 --date-to 2024-12-31

copilot trial validate
copilot journal post --entity bgs --posted-by admin
copilot journal post --entity mhb --posted-by admin
```

### Example 3: Year-End Processing

**Scenario**: Complete year-end processing for 2024.

```bash
# Import all bank statements for the year
for month in {01..12}; do
  copilot import csv ~/statements/bgs_checking_2024_${month}.csv \
    --account bgs:checking --period 2024-${month}
done

# Run comprehensive wizard for full year
copilot allocate wizard --entity bgs --period 2024

# Review and assign remaining transactions
copilot staging assign-todo --entity bgs

# Check staging status
copilot import status --account bgs:checking

# Generate trial entries for full year
copilot trial generate --entity bgs \
  --date-from 2024-01-01 \
  --date-to 2024-12-31

# Match transfers and validate
copilot trial match-transfers --entity bgs
copilot trial validate

# Review ready entries
copilot trial ready --entity bgs

# Post to journal
copilot journal post --entity bgs --posted-by admin

# Generate year-end reports
copilot journal trial-balance --entity bgs
copilot report
```

---

## Best Practices

### Import Best Practices

1. **Always Preview First**
   - Use `--dry-run` to review before importing
   - Check for duplicate detection accuracy
   - Verify date range and transaction counts

2. **Use Period Filters**
   - Filter imports to specific periods
   - Prevents importing wrong date ranges
   - Easier to reconcile and track

3. **Regular Imports**
   - Import monthly rather than quarterly/annually
   - Easier to track and reconcile
   - Reduces memory and processing time

4. **Check Import History**
   - Run `copilot import list` regularly
   - Verify no gaps in date ranges
   - Ensure no duplicate imports

5. **File Organization**
   - Keep CSV files organized by month/year
   - Use consistent naming: `entity_account_period.csv`
   - Example: `bgs_checking_2024_01.csv`

### Allocation Best Practices

1. **Run Wizard Immediately After Import**
   - Leverages fresh context
   - Patterns are easier to recognize
   - Intercompany transfers are fresh in memory

2. **Review Auto-Assignments**
   - Wizard shows what it assigned
   - Spot-check for accuracy
   - Use staging commands to fix errors

3. **Build Pattern Library**
   - Create patterns for recurring vendors
   - Document notes in pattern descriptions
   - Share patterns across team members

4. **Handle Loans Carefully**
   - Loan payments require principal/interest split
   - Don't auto-assign without verification
   - Use staging commands for detailed review

5. **Skip Inactive Accounts**
   - Use Step 1 to skip accounts with no activity
   - Document skip reasons
   - Unskip if needed later in process

### Data Quality Best Practices

1. **Validate Bank Statements**
   - Verify CSV export from bank is complete
   - Check for corrupted or truncated files
   - Ensure consistent date formats

2. **Reconcile Imported Counts**
   - Compare imported count to bank statement
   - Investigate significant differences
   - Document any discrepancies

3. **Review Edge Cases**
   - Check transactions with unusual amounts
   - Verify check numbers are captured correctly
   - Review split transactions

4. **Backup Before Processing**
   - Database backups before large imports
   - Keep original CSV files
   - Document processing steps

---

## Troubleshooting

### Import Issues

#### Problem: "Account not found"

**Cause**: The specified account code doesn't exist in the database.

**Solution**:
```bash
# List available accounts
copilot import

# Verify account exists
psql -d copilot_db -c "SELECT code, name FROM acc.bank_account WHERE status = 'active';"
```

#### Problem: "Could not detect CSV format"

**Cause**: CSV headers don't match expected patterns.

**Solution**:
1. Open CSV file and check headers
2. Verify it has a date column
3. Verify it has amount or debit/credit columns
4. If needed, rename headers to match expected patterns
5. Common fixes:
   - Rename `Trans Date` to `Transaction Date`
   - Rename `Desc` to `Description`
   - Rename `Amt` to `Amount`

#### Problem: "File already imported"

**Cause**: File hash matches previous import.

**Solution**:
```bash
# Check import history
copilot import list --account <code>

# If truly a duplicate, skip or manually override
# If different data, verify file is correct version
```

#### Problem: "No valid transactions found"

**Cause**: 
- Date parsing failed
- All amounts are zero
- CSV format is incompatible

**Solution**:
1. Check date format in CSV
2. Verify amount columns have data
3. Try with `--dry-run` to see parsing details
4. Check for special characters in CSV

### Allocation Issues

#### Problem: "No transactions imported for this period"

**Cause**: Either no imports exist, or all accounts are skipped.

**Solution**:
```bash
# Check import status
copilot import status

# Verify imports for period
copilot import list

# Run import if missing
copilot import csv <file> --account <code> --period <period>
```

#### Problem: "Intercompany transfers not detected"

**Cause**: 
- Amounts don't match exactly
- Dates are more than 2 days apart
- Entities are the same
- Transactions already allocated

**Solution**:
1. Verify amounts are exactly opposite
2. Check transaction dates
3. Manually assign if needed:
```bash
copilot staging assign <from_id> ic:bgs-mhb
copilot staging assign <to_id> ic:bgs-mhb
```

#### Problem: "Recurring vendors not auto-assigned"

**Cause**: No patterns exist in `acc.vendor_gl_patterns`.

**Solution**:
```bash
# Create patterns during manual assignment
copilot staging assign-todo --entity <entity>

# Or insert patterns directly:
psql -d copilot_db -c "
  INSERT INTO acc.vendor_gl_patterns 
    (pattern, gl_account_code, entity, notes, active, priority)
  VALUES 
    ('AMAZON', 'expense:supplies', 'bgs', 'Amazon purchases', true, 50);
"
```

#### Problem: "Wizard shows wrong entity data"

**Cause**: Entity filter not applied correctly.

**Solution**:
- Specify entity explicitly: `--entity bgs`
- Verify entity codes in database
- Check that transactions have correct entity set

### Performance Issues

#### Problem: "Import taking too long"

**Cause**: Large CSV file with many transactions.

**Solution**:
1. Split large files by period
2. Use `--period` filter to reduce scope
3. Import during off-peak hours
4. Consider database indexing

#### Problem: "Wizard step 4 is slow"

**Cause**: Many unique vendors with pattern matching.

**Solution**:
1. Process smaller periods
2. Filter by entity
3. Skip recurring step if not needed
4. Optimize vendor_gl_patterns table

---

## Additional Commands

### Staging Commands

After allocation wizard, use these commands for detailed management:

```bash
# List all staging transactions
copilot staging list --entity bgs

# Show only unallocated (TODO) transactions
copilot staging todos --entity bgs

# Interactive assignment of TODO items
copilot staging assign-todo --entity bgs

# Assign specific transaction
copilot staging assign <id> <gl_code>

# View summary statistics
copilot staging summary --entity bgs

# Find unmatched transfers
copilot staging transfers --entity bgs
```

### Trial Commands

After allocation, generate accounting entries:

```bash
# Generate trial entries
copilot trial generate --entity bgs

# Validate entries
copilot trial validate

# Match transfer pairs
copilot trial match-transfers --entity bgs

# Show entries ready to post
copilot trial ready --entity bgs

# View trial balance
copilot journal trial-balance --entity bgs
```

### Report Commands

Generate reports from allocated data:

```bash
# Interactive reporting menu
copilot report

# Quick trial balance
copilot journal trial-balance --entity bgs

# View balances by account
copilot journal balances --entity bgs
```

---

## Related Documentation

- [CLI Command Reference](cli/README.md) - Complete command documentation
- [Staging to Journal Workflow](workflow/staging-to-journal.md) - Complete processing workflow
- [Trial Entry System](trial_entry_system.md) - Technical details on trial entries

---

## Quick Reference Card

### Import Workflow
```bash
copilot import                                    # Show help
copilot import csv <file> -a <account> --dry-run # Preview
copilot import csv <file> -a <account>           # Import
copilot import list                               # View history
copilot import status                             # Check staging
```

### Allocation Workflow
```bash
copilot allocate wizard -p <period>               # Run wizard
copilot staging assign-todo -e <entity>           # Manual assign
copilot staging summary -e <entity>               # Check progress
```

### Post-Allocation
```bash
copilot trial generate -e <entity>                # Create entries
copilot trial validate                            # Validate
copilot journal post -e <entity> --posted-by user # Post to GL
```
