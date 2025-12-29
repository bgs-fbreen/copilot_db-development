# CLI Command Reference

Command-line interface reference for the copilot accounting system.

## Command Structure

```
copilot <module> <action> [options]
```

## Modules

### Import Module

Import bank transaction data from CSV files.

```bash
copilot import csv <file> --account <code>    # Import CSV file
copilot import list                            # List recent imports
```

**Options:**
- `--account <code>` - Source bank account code (e.g., `bgs:checking`)

---

### Staging Module

Manage bank staging transactions and GL code assignment.

```bash
copilot staging list [--entity <code>]                    # List staged transactions
copilot staging todos [--entity <code>]                   # Show transactions needing GL assignment
copilot staging assign <id> <gl_code>                     # Assign GL code to transaction
copilot staging summary [--entity <code>]                 # Summary by entity and status
copilot staging transfers [--entity <code>]               # Show unmatched transfers
```

**Options:**
- `--entity <code>` - Filter by entity (e.g., `bgs`, `mhb`)

---

### Trial Module

Generate and manage trial entries for double-entry accounting.

```bash
copilot trial generate [options]                         # Generate trial entries from staging
copilot trial validate                                    # Validate pending entries
copilot trial list [--entity <code>]                     # List trial entries
copilot trial errors [--entity <code>]                   # Show entries with errors
copilot trial match-transfers [--entity <code>]          # Match internal transfer pairs
copilot trial summary [--entity <code>]                  # Summary by entity and status
copilot trial ready [--entity <code>]                    # Show entries ready to post
```

**Generate Options:**
- `--entity <code>` - Filter by entity
- `--date-from <date>` - Start date (YYYY-MM-DD)
- `--date-to <date>` - End date (YYYY-MM-DD)
- `--dry-run` - Preview without creating entries

---

### Journal Module

Post and manage final journal entries.

```bash
copilot journal post [options]                           # Post validated trial entries
copilot journal list [options]                           # List journal entries
copilot journal view <id>                                # View entry with lines
copilot journal reverse <id> --reason <text>             # Create reversal entry
copilot journal balances [--entity <code>]               # Show GL account balances
copilot journal trial-balance [--entity <code>]          # Show trial balance report
copilot journal summary [--entity <code>]                # Show journal statistics
```

**Post Options:**
- `--entity <code>` - Filter by entity
- `--posted-by <user>` - User posting the entries
- `--dry-run` - Preview without posting

**List Options:**
- `--entity <code>` - Filter by entity
- `--date-from <date>` - Start date
- `--date-to <date>` - End date

---

## Workflow Examples

### Complete Processing Workflow

```bash
# 1. Import bank data
copilot import csv ~/Downloads/bgs_checking.csv --account bgs:checking

# 2. Review and assign GL codes
copilot staging todos --entity bgs
copilot staging assign 101 expense:utilities
copilot staging assign 102 expense:supplies

# 3. Generate trial entries
copilot trial generate --entity bgs

# 4. Validate
copilot trial validate

# 5. Match transfers
copilot trial match-transfers --entity bgs

# 6. Review ready entries
copilot trial ready --entity bgs

# 7. Post to journal
copilot journal post --entity bgs --posted-by admin

# 8. Verify trial balance
copilot journal trial-balance --entity bgs
```

### Monthly Processing

```bash
# Generate entries for specific month
copilot trial generate --entity bgs       \
  --date-from 2024-01-01                  \
  --date-to 2024-01-31

# Validate and post
copilot trial validate
copilot journal post --entity bgs --posted-by admin
```

### Error Recovery

```bash
# Find and fix errors
copilot trial errors --entity bgs
copilot staging assign <id> <correct_gl_code>

# Re-validate
copilot trial validate

# Reverse incorrect journal entry
copilot journal reverse 123 --reason "Incorrect GL code"
```

---

## Common Options

Most commands support these common options:

- `--entity <code>` - Filter by entity code (e.g., `bgs`, `mhb`)
- `--help` - Show command help
- `--version` - Show version information

## Status Values

### Bank Staging
- `TODO` - No GL code assigned
- `<gl_code>` - GL code assigned

### Trial Entry
- `pending` - Newly created, not validated
- `balanced` - Validated and balanced
- `error` - Validation failed
- `posted` - Posted to journal

### Journal Entry
- `ACTIVE` - Normal posted entry
- `REVERSED` - Entry that was reversed
- `REVERSAL` - Reversal of another entry

---

## Related Documentation

- [Staging to Journal Workflow](../workflow/staging-to-journal.md) - Complete workflow guide
- [Trial Entry System](../trial_entry_system.md) - Technical details
