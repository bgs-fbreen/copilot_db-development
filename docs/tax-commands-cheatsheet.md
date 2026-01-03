# Tax Commands Cheatsheet

Quick reference for property tax tracking commands.

## Quick Reference Table

| Command | Purpose | Example |
|---------|---------|---------|
| `copilot tax owed` | View all outstanding taxes | `copilot tax owed` |
| `copilot tax foreclosure` | Show foreclosure risk bills (3+ years) | `copilot tax foreclosure -p 905brown` |
| `copilot tax priority` | Payment priority list | `copilot tax priority --limit 10` |
| `copilot tax trends <property>` | Assessment & tax trends with charts | `copilot tax trends 711pine` |
| `copilot tax show <property>` | Detailed property tax view | `copilot tax show 819helen` |
| `copilot tax list` | List all tax bills | `copilot tax list --year 2024` |
| `copilot tax pay` | Record a payment (interactive) | `copilot tax pay` |
| `copilot tax import` | Import tax data from CSV | `copilot tax import --file taxes.csv` |
| `copilot tax export` | Export to CSV/JSON | `copilot tax export -f csv -r owed` |
| `copilot tax report` | Generate annual report | `copilot tax report --year 2024` |

## Detailed Command Examples

### View Outstanding Taxes

**Command:**
```bash
copilot tax owed
```

**Description:**  
Shows all properties with unpaid tax balances.

**Sample Output:**
```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property  ┃ Total Due    ┃ Total Paid   ┃ Balance      ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 905brown  │  $12,500.00  │   $5,020.69  │   $7,479.31  │
│ 711pine   │  $16,200.00  │   $5,831.91  │  $10,368.09  │
│ 819helen  │  $14,000.00  │   $5,138.85  │   $8,861.15  │
│ parnell   │   $8,100.00  │   $7,399.04  │     $700.96  │
└───────────┴──────────────┴──────────────┴──────────────┘

TOTAL OUTSTANDING: $27,409.51
```

### Foreclosure Risk Report

**Command:**
```bash
# All properties
copilot tax foreclosure

# Specific property
copilot tax foreclosure --property 905brown
copilot tax foreclosure -p 711pine
```

**Description:**  
Shows bills that are 3+ years delinquent and at risk of foreclosure. These are YOUR HIGHEST PRIORITY to pay!

**Sample Output:**
```
╔═══════════════════════════════════════════════════════════╗
║        ⚠️  TAX FORECLOSURE RISK REPORT                    ║
╚═══════════════════════════════════════════════════════════╝

⚠️ Properties with taxes delinquent 3+ years are at risk of foreclosure!

┏━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Property  ┃ Year ┃ Season ┃ Balance    ┃ Years Overdue┃ Risk Level┃
┡━━━━━━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 905brown  │ 2022 │ Summer │  $  981.19 │   4 years   │ 🔴 CRITICAL│
│ 905brown  │ 2022 │ Winter │  $  981.18 │   4 years   │ 🔴 CRITICAL│
│ 711pine   │ 2022 │ Summer │ $1,356.40  │   4 years   │ 🔴 CRITICAL│
│ 711pine   │ 2022 │ Winter │ $1,356.40  │   4 years   │ 🔴 CRITICAL│
│ 819helen  │ 2022 │ Summer │  $  993.79 │   4 years   │ 🔴 CRITICAL│
│ 819helen  │ 2022 │ Winter │  $  993.79 │   4 years   │ 🔴 CRITICAL│
│ 905brown  │ 2023 │ Summer │ $1,258.48  │   3 years   │ 🔴 HIGH    │
│ 711pine   │ 2023 │ Summer │ $1,656.15  │   3 years   │ 🔴 HIGH    │
│ 819helen  │ 2023 │ Summer │ $1,443.50  │   3 years   │ 🔴 HIGH    │
└───────────┴──────┴────────┴────────────┴─────────────┴───────────┘

TOTAL AT RISK: $6,662.75

⚠️  ACTION REQUIRED: Pay these bills immediately to avoid property seizure!
```

### Payment Priority List

**Command:**
```bash
# Show top 20 priority items (default)
copilot tax priority

# Show top 10
copilot tax priority --limit 10
copilot tax priority -n 10

# Specific property
copilot tax priority --property 819helen
copilot tax priority -p parnell
```

**Description:**  
Intelligent payment priority list based on:
1. Years delinquent (oldest first)
2. Foreclosure risk (critical → high → medium → low)
3. Partial payments (finish what you started)

**Sample Output:**
```
╔═══════════════════════════════════════════════════════════╗
║              PAYMENT PRIORITY LIST                        ║
╚═══════════════════════════════════════════════════════════╝

┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Priority ┃ Property  ┃ Year ┃ Season ┃ Balance    ┃ Risk     ┃ Reason                 ┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 🔴 1     │ 905brown  │ 2022 │ Summer │  $  981.19 │ CRITICAL │ Foreclosure imminent   │
│ 🔴 2     │ 905brown  │ 2022 │ Winter │  $  981.18 │ CRITICAL │ Foreclosure imminent   │
│ 🔴 3     │ 711pine   │ 2022 │ Summer │ $1,356.40  │ CRITICAL │ Foreclosure imminent   │
│ 🔴 4     │ 711pine   │ 2022 │ Winter │ $1,356.40  │ CRITICAL │ Foreclosure imminent   │
│ 🔴 5     │ 819helen  │ 2022 │ Summer │  $  993.79 │ CRITICAL │ Foreclosure imminent   │
│ 🔴 6     │ 819helen  │ 2022 │ Winter │  $  993.79 │ CRITICAL │ Foreclosure imminent   │
│ 🔴 7     │ 905brown  │ 2023 │ Summer │ $1,258.48  │ HIGH     │ Foreclosure risk       │
│ 🔴 8     │ 711pine   │ 2023 │ Summer │ $1,656.15  │ HIGH     │ Foreclosure risk       │
│ 🔴 9     │ 819helen  │ 2023 │ Summer │ $1,443.50  │ HIGH     │ Foreclosure risk       │
│ 🟡 10    │ 905brown  │ 2024 │ Summer │ $1,629.24  │ MEDIUM   │ 2 years delinquent     │
└──────────┴───────────┴──────┴────────┴────────────┴──────────┴────────────────────────┘

MINIMUM TO AVOID FORECLOSURE: $6,662.75 (items 1-6)
TOTAL OUTSTANDING:            $27,409.51
```

### Assessment & Tax Trends

**Command:**
```bash
# Show last 10 years (default)
copilot tax trends 711pine

# Show last 5 years
copilot tax trends 905brown --years 5
copilot tax trends 819helen -y 5
```

**Description:**  
Visualize assessment and tax trends over time with ASCII charts. Shows year-over-year changes and highlights when PRE exemption was lost.

**Sample Output:**
```
╔═══════════════════════════════════════════════════════════╗
║         TAX TRENDS: 711pine (2018-2025)                  ║
╚═══════════════════════════════════════════════════════════╝

ASSESSED VALUE TREND:
$ 52,000 |    ████       ████       ████  
$ 48,000 |    ████       ████       ████  
$ 44,000 |    ████       ████       ████  
$ 40,000 | ████████    ████████    ████████
$ 36,000 | ████████    ████████    ████████
$ 32,000 | ████████ ████████████ ████████████
$ 28,000 | ████████████████████████████████
$ 24,000 | ████████████████████████████████
          └──────────────────────────────────
           2018 2019 2020 2021 2022 2023 2024 2025

ANNUAL TAX TREND:
$  3,822 |                         ████  
$  3,500 |                         ████████
$  3,200 |                      ████████████
$  2,900 |                   ████████████████
$  2,600 |                ████████████████████
$  2,300 |             ████████████████████████
$  2,000 | ████    ████████████████████████████
$  1,700 | ████████████████████████████████████
          └──────────────────────────────────────
           2018 2019 2020 2021 2022 2023 2024 2025
                             ↑
                       PRE Exemption Lost

Year-over-Year Changes:
┏━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┓
┃ Year   ┃ Assessed   ┃ Change ┃ Annual Tax ┃ Change ┃ PRE% ┃
┡━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━┩
│ 2018   │ $ 35,000   │    -   │ $ 1,295.00 │    -   │ 100% │
│ 2019   │ $ 36,000   │ + 2.9% │ $ 1,332.00 │ + 2.9% │ 100% │
│ 2020   │ $ 37,000   │ + 2.8% │ $ 1,369.00 │ + 2.8% │ 100% │
│ 2021   │ $ 38,000   │ + 2.7% │ $ 1,406.00 │ + 2.7% │ 100% │
│ 2022   │ $ 42,000   │ +10.5% │ $ 2,712.80 │ +92.9% │   0% ⚠️ │
│ 2023   │ $ 44,000   │ + 4.8% │ $ 3,312.30 │ +22.1% │   0% │
│ 2024   │ $ 48,000   │ + 9.1% │ $ 3,822.00 │ +15.4% │   0% │
│ 2025   │ $ 52,000   │ + 8.3% │ $ 4,126.00 │ + 8.0% │   0% │
└────────┴────────────┴────────┴────────────┴────────┴──────┘

⚠️ Note: PRE exemption lost in 2022 caused significant tax increase
```

### Show Property Details

**Command:**
```bash
copilot tax show 905brown
copilot tax show parnell
```

**Description:**  
Detailed view of all tax bills and payments for a single property.

**Sample Output:**
```
╔═══════════════════════════════════════════════════════════╗
║         PROPERTY TAX DETAILS: 905brown                    ║
╚═══════════════════════════════════════════════════════════╝

Property Information:
- Address: 905 Brown Street, Sault Ste Marie, MI
- Type: Rental Property
- PRE Status: 0% (No exemption)

Tax Bills:
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Year   ┃ Season ┃ Total Due   ┃ Paid       ┃ Balance    ┃ Status      ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 2025   │ Winter │ $ 1,785.50  │ $     0.00 │ $ 1,785.50 │ Unpaid      │
│ 2025   │ Summer │ $ 1,785.50  │ $     0.00 │ $ 1,785.50 │ Unpaid      │
│ 2024   │ Winter │ $ 1,629.24  │ $     0.00 │ $ 1,629.24 │ Delinquent  │
│ 2024   │ Summer │ $ 1,629.24  │ $     0.00 │ $ 1,629.24 │ Delinquent  │
│ 2023   │ Winter │ $ 1,258.48  │ $     0.00 │ $ 1,258.48 │ Delinquent  │
│ 2023   │ Summer │ $ 1,258.48  │ $     0.00 │ $ 1,258.48 │ Delinquent  │
│ 2022   │ Winter │ $   981.18  │ $     0.00 │ $   981.18 │ 🔴 AT RISK  │
│ 2022   │ Summer │ $   981.19  │ $     0.00 │ $   981.19 │ 🔴 AT RISK  │
└────────┴────────┴─────────────┴────────────┴────────────┴─────────────┘

Summary:
- Total Due:       $12,500.00
- Total Paid:      $ 5,020.69
- Balance:         $ 7,479.31
- At Risk:         $ 1,962.37 (2 bills)
- Years Delinquent: 4 years (oldest)
```

### List All Tax Bills

**Command:**
```bash
# List all bills
copilot tax list

# Filter by year
copilot tax list --year 2024
copilot tax list -y 2025

# Filter by property
copilot tax list --property 711pine
copilot tax list -p 819helen

# Filter by status
copilot tax list --status unpaid
copilot tax list --status delinquent
```

**Description:**  
List all tax bills with optional filters.

### Record a Payment

**Command:**
```bash
copilot tax pay
```

**Description:**  
Interactive wizard to record a tax payment. Will prompt for:
- Property code
- Tax year
- Tax season (Summer/Winter)
- Payment amount
- Payment date
- Payment method (optional)
- Check/confirmation number (optional)

**Example Session:**
```
Enter property code (905brown, 711pine, 819helen, parnell): 905brown
Enter tax year: 2022
Enter season (Summer/Winter): Summer
Enter payment amount: 981.19
Enter payment date (YYYY-MM-DD) [2026-01-15]: 2026-01-15
Enter payment method [check/online/wire/cash]: check
Enter check number (optional): 1234
Enter notes (optional): Paid in full - highest priority

✓ Payment recorded successfully!

Updated bill:
- Total due: $981.19
- Total paid: $981.19
- Balance: $0.00
- Status: PAID
```

### Import Tax Data

**Command:**
```bash
# Import from CSV file
copilot tax import --file tax_bills_2025.csv

# Import with year filter
copilot tax import --file all_taxes.csv --year 2025

# Import and skip duplicates
copilot tax import --file taxes.csv --skip-duplicates
```

**Description:**  
Import tax bills from a CSV file. See main guide for CSV format requirements.

**CSV Format:**
```csv
property_code,tax_year,tax_season,assessed_value,taxable_value,pre_pct,millage_rate,total_due,due_date,notes
905brown,2025,Summer,45000,38500,0,46.5,1785.50,2025-09-14,
711pine,2025,Summer,52000,45000,0,46.5,2092.50,2025-09-14,
```

### Export Tax Data

**Command:**
```bash
# Export to CSV (default)
copilot tax export

# Export specific format
copilot tax export --format csv
copilot tax export --format json
copilot tax export -f csv

# Export specific report type
copilot tax export --report owed          # Only unpaid bills
copilot tax export --report history       # All bills with payments
copilot tax export --report detail        # Detailed with payment info
copilot tax export --report summary       # Summary view (default)

# Filter by property
copilot tax export --property 711pine -f csv

# Filter by year
copilot tax export --year 2024 -f json

# Custom output file
copilot tax export -o my_taxes.csv
```

**Description:**  
Export tax data to CSV or JSON format for analysis in Excel, Google Sheets, or other tools.

**Sample Output:**
```
✓ Data exported to tax_export_owed_20260115_143022.csv
```

### Generate Annual Report

**Command:**
```bash
# Current year report
copilot tax report

# Specific year
copilot tax report --year 2024
copilot tax report -y 2023

# Specific property
copilot tax report --property 905brown

# Export to file
copilot tax report --year 2024 --output 2024_tax_report.txt
```

**Description:**  
Generate a comprehensive annual tax report showing:
- Total taxes assessed
- Total payments made
- Outstanding balance
- Year-over-year trends
- Property-by-property breakdown

## Common Workflows

### 1. Check What You Owe

**Quick Check:**
```bash
copilot tax owed
```

**Detailed with Priority:**
```bash
copilot tax foreclosure
copilot tax priority --limit 10
```

**Property-Specific:**
```bash
copilot tax show 905brown
```

### 2. After Making a Payment

**Record the payment:**
```bash
copilot tax pay
```

**Verify it was applied:**
```bash
copilot tax show 905brown
copilot tax owed
```

### 3. Monthly Review

**Check current status:**
```bash
# Overall outstanding balance
copilot tax owed

# Foreclosure risk check
copilot tax foreclosure

# Payment priority
copilot tax priority -n 5
```

### 4. Year-End Review

**Generate annual report:**
```bash
copilot tax report --year 2025

# Export for tax records
copilot tax export --year 2025 -f csv -r history -o 2025_taxes_history.csv
```

**Review trends:**
```bash
copilot tax trends 905brown
copilot tax trends 711pine
copilot tax trends 819helen
copilot tax trends parnell
```

## Database Queries (psql)

Connect to database:
```bash
psql -d copilot_db
```

### Quick Status Check

```sql
-- Outstanding by property
SELECT 
    property_code,
    SUM(balance_due) as outstanding
FROM acc.property_tax_bill
WHERE balance_due > 0
GROUP BY property_code
ORDER BY outstanding DESC;
```

### Foreclosure Risk

```sql
-- Bills at foreclosure risk
SELECT * FROM acc.v_property_tax_foreclosure_risk
ORDER BY years_delinquent DESC, property_code;
```

### Payment Priority

```sql
-- Top 10 priority bills
SELECT * FROM acc.v_property_tax_priority
ORDER BY priority_rank, tax_year
LIMIT 10;
```

### Recent Payments

```sql
-- Last 30 days of payments
SELECT 
    b.property_code,
    b.tax_year,
    b.tax_season,
    p.payment_date,
    p.amount,
    p.payment_method
FROM acc.property_tax_payment p
JOIN acc.property_tax_bill b ON b.id = p.tax_bill_id
WHERE p.payment_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY p.payment_date DESC;
```

### Assessment Trends

```sql
-- 5-year assessment trend for property
SELECT 
    tax_year,
    assessed_value,
    taxable_value,
    annual_tax,
    prev_tax,
    ROUND((annual_tax - prev_tax) / NULLIF(prev_tax, 0) * 100, 1) as pct_change
FROM acc.v_property_tax_trends
WHERE property_code = '711pine'
  AND tax_year >= EXTRACT(YEAR FROM CURRENT_DATE) - 5
ORDER BY tax_year;
```

## Current Status Summary

### All Properties Overview (as of 2026)

```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Property  ┃ Outstanding  ┃ At Risk       ┃ # Risk Bills  ┃ Status     ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 905brown  │  $ 7,479.31  │  $ 1,962.37   │       2       │ 🔴 URGENT  │
│ 711pine   │ $10,368.09   │  $ 2,712.80   │       2       │ 🔴 URGENT  │
│ 819helen  │  $ 8,861.15  │  $ 1,987.58   │       2       │ 🔴 URGENT  │
│ parnell   │  $   700.96  │  $    0.00    │       0       │ 🟢 OK      │
├───────────┼──────────────┼───────────────┼───────────────┼────────────┤
│ TOTAL     │ $27,409.51   │  $ 6,662.75   │       6       │ 🔴 ACTION  │
└───────────┴──────────────┴───────────────┴───────────────┴────────────┘
```

**Critical Actions Needed:**
1. **Pay $6,662.75 immediately** - All 2022 bills (4 years delinquent)
2. Monitor 2023 bills - Approaching foreclosure threshold
3. Create payment plan for 2024-2025 bills

## Option Flags Reference

### Common Options

| Flag | Long Form | Description | Example |
|------|-----------|-------------|---------|
| `-p` | `--property` | Filter by property code | `-p 905brown` |
| `-y` | `--year` | Filter by tax year | `-y 2024` |
| `-n` | `--limit` | Limit number of results | `-n 10` |
| `-f` | `--format` | Output format (csv/json/pdf) | `-f csv` |
| `-o` | `--output` | Output file path | `-o taxes.csv` |
| `-r` | `--report` | Report type | `-r owed` |

### Property Codes

- `905brown` - 905 Brown Street (rental)
- `711pine` - 711 Pine Street (rental)
- `819helen` - 819 Helen Street (rental)
- `parnell` - Parnell residence (personal)

### Tax Seasons

- `Summer` - July bill, due September 14
- `Winter` - December bill, due February 14

### Payment Status

- `unpaid` - No payments made
- `partial` - Partially paid
- `paid` - Fully paid
- `delinquent` - Past due with penalties

### Report Types

- `summary` - Basic summary info (default)
- `detail` - Detailed with payment history
- `owed` - Only unpaid bills
- `history` - Complete history including paid bills

### Risk Levels

- 🔴 `CRITICAL` - 5+ years delinquent
- 🔴 `HIGH` - 3-4 years delinquent (foreclosure eligible)
- 🟡 `MEDIUM` - 2 years delinquent
- 🟢 `LOW` - 1 year or less delinquent

## Tips and Tricks

### Quick Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Tax shortcuts
alias tax-owed='copilot tax owed'
alias tax-risk='copilot tax foreclosure'
alias tax-priority='copilot tax priority -n 10'
alias tax-pay='copilot tax pay'

# Property-specific
alias tax-905='copilot tax show 905brown'
alias tax-711='copilot tax show 711pine'
alias tax-819='copilot tax show 819helen'
alias tax-home='copilot tax show parnell'
```

### Batch Export All Properties

```bash
# Export each property to separate CSV
for prop in 905brown 711pine 819helen parnell; do
  copilot tax export -p $prop -f csv -o "taxes_${prop}_2025.csv"
done
```

### Monthly Reminder Script

```bash
#!/bin/bash
# monthly_tax_check.sh

echo "=== Monthly Tax Status Check ==="
echo ""
echo "Outstanding Balances:"
copilot tax owed
echo ""
echo "Foreclosure Risk:"
copilot tax foreclosure
echo ""
echo "Next 5 Priority Payments:"
copilot tax priority -n 5
```

### Excel Analysis

After exporting to CSV:
```bash
copilot tax export -f csv -r history -o tax_history.csv
```

Open in Excel/Google Sheets and create pivot tables to analyze:
- Total taxes by year
- Payment patterns by property
- Assessment growth trends
- Tax burden comparison

## Troubleshooting

### Command not found

**Error:** `bash: copilot: command not found`

**Solution:**
```bash
# Ensure copilot is in your PATH
export PATH=$PATH:/path/to/copilot

# Or run with python
python -m copilot.cli tax owed
```

### Database connection error

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
1. Check PostgreSQL is running: `pg_isready`
2. Verify connection settings in `.env` file
3. Test connection: `psql -d copilot_db`

### No data returned

**Issue:** Commands return "No data found"

**Solution:**
1. Check if bills imported: `psql -d copilot_db -c "SELECT COUNT(*) FROM acc.property_tax_bill;"`
2. Import tax data if needed: `copilot tax import --file taxes.csv`
3. Verify property codes match exactly (case-sensitive)

## Additional Help

**View command help:**
```bash
copilot tax --help
copilot tax foreclosure --help
copilot tax priority --help
```

**See main documentation:**
- Full guide: `docs/tax-tracking-guide.md`
- Database schema: `sql/migrations/019_property_tax_tracking.sql`
- Command source: `copilot/commands/tax_cmd.py`

**Get support:**
- Check repository issues: https://github.com/bgs-fbreen/copilot_db-development/issues
- Review database logs: `tail -f /var/log/postgresql/postgresql-*.log`
