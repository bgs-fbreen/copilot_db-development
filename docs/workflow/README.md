# Workflow Documentation

This directory contains workflow documentation for the copilot accounting system.

## Available Workflows

### [Staging to Journal Workflow](staging-to-journal.md)
Complete guide for processing bank transactions from import through final journal posting.

**Covers:**
- Part 01: Bank Staging - Import and GL assignment
- Part 02: Trial Entry - Double-entry generation and validation
- Part 03: Journal - Final immutable accounting records

**Topics:**
- Import process
- GL code assignment
- Trial entry generation and validation
- Transfer matching
- Journal posting and reversals
- Complete workflow examples
- Troubleshooting guide

## Quick Start

For a quick overview of the staging-to-journal workflow:

```bash
# 1. Import bank transactions
copilot import csv ~/Downloads/bank_statement.csv --account bgs:checking

# 2. Assign GL codes
copilot staging todos --entity bgs
copilot staging assign <id> <gl_code>

# 3. Generate and validate trial entries
copilot trial generate --entity bgs
copilot trial validate

# 4. Match transfers
copilot trial match-transfers --entity bgs

# 5. Post to journal
copilot journal post --entity bgs --posted-by admin

# 6. Verify
copilot journal trial-balance --entity bgs
```

## Related Documentation

- [Trial Entry System](../trial_entry_system.md) - Technical details of Part 02
- [CLI Command Reference](../cli/README.md) - Complete CLI documentation

## Architecture Overview

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
