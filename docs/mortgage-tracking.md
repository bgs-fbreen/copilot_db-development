# Mortgage Tracking Guide

## Overview

The mortgage tracking system provides comprehensive management of mortgage loans with payment tracking, amortization projections, and investment analysis tools.

## Architecture

### Data Model

**Mortgage Tables:**
- `mhb.mortgage` - MHB rental property mortgages
- `per.mortgage` - Personal residence mortgages

**Payment Tracking:**
- `{entity}.mortgage_payment` - Payment history with P&I split
- `{entity}.mortgage_escrow` - Escrow disbursements
- `{entity}.mortgage_projection` - Amortization schedules

### Key Features

1. **Principal/Interest Split**: Each payment automatically calculated based on current balance and rate
2. **Escrow Tracking**: Separate tracking of escrow disbursements for taxes and insurance
3. **Amortization Projection**: Full loan amortization schedule generation
4. **Scenario Analysis**: What-if calculations for extra payments, rate changes, etc.

## CLI Commands

### List Mortgages

```bash
# List all mortgages
copilot mortgage list

# List MHB mortgages only
copilot mortgage list --entity mhb

# List personal mortgages only
copilot mortgage list --entity per
```

**Output:**
- Property code and address
- Lender
- Interest rate
- Current balance
- Maturity date
- Portfolio summary statistics

### Show Mortgage Details

```bash
copilot mortgage show 711pine
copilot mortgage show parnell
```

**Output:**
- Complete loan details
- Payment history (last 12 months)
- Principal/interest breakdown
- Progress toward payoff
- Escrow information

### Import Payments

```bash
copilot mortgage import --file 819helen.csv --property 819helen
```

**Process:**
1. Parse CSV transactions
2. Handle reversals and rate change entries
3. Calculate interest = balance × (rate / 12)
4. Calculate principal = payment - interest
5. Update current balance
6. Create payment record in `mortgage_payment` table
7. Handle escrow disbursements separately

**CSV Format:**
```csv
Date,Description,Amount
2024-01-15,Mortgage Payment,-1234.56
2024-01-20,Reversal,1234.56
2024-01-22,Mortgage Payment,-1234.56
2024-02-15,Escrow Disbursement - Property Tax,-2500.00
```

### Generate Projection

```bash
copilot mortgage project 711pine
```

**Output:**
- Complete amortization schedule
- Payment number, date, amount
- Principal and interest per payment
- Balance after each payment
- Cumulative interest paid
- Payoff date

**Storage:**
- Saved to `{entity}.mortgage_projection` table
- Tagged with projection_date for versioning

### Compare Projected vs Actual

```bash
copilot mortgage compare 819helen
```

**Analysis:**
- Side-by-side comparison of projection vs actual payments
- Extra principal payments identified
- Interest savings from early payments
- Ahead/behind schedule calculation
- Updated payoff date estimate

### Scenario Analysis

```bash
# Extra monthly payment
copilot mortgage whatif 711pine --extra-monthly 100

# Annual lump sum
copilot mortgage whatif 905brown --extra-annual 5000

# Rate change analysis
copilot mortgage whatif parnell --rate-change 5.5

# Cash-out refinance
copilot mortgage whatif 819helen --cashout 15000
```

**Calculations:**
- Payoff date with extra payments
- Total interest savings
- Monthly payment changes
- Break-even analysis for refinance
- Cash flow impact

### Tax Reporting

```bash
copilot mortgage tax-report --year 2024
```

**Output:**
- Total interest paid by property
- Monthly breakdown
- Schedule E format
- Year-over-year comparison

## Payment Calculation

### Interest Calculation

```
Monthly Interest = Current Balance × (Annual Rate / 12 / 100)
```

### Principal Calculation

```
Principal = Payment Amount - Interest - Escrow
```

### Balance Update

```
New Balance = Current Balance - Principal
```

### Example

Property: 711 Pine Street
- Current Balance: $66,621.85
- Annual Rate: 8.500%
- Monthly Payment: $547.89

```
Interest = $66,621.85 × (8.500 / 12 / 100) = $471.07
Principal = $547.89 - $471.07 = $76.82
New Balance = $66,621.85 - $76.82 = $66,545.03
```

## Escrow Handling

### Escrow Types

- `property_tax` - Real estate taxes
- `homeowners_insurance` - Property insurance
- `flood_insurance` - Flood insurance
- `pmi` - Private mortgage insurance

### Escrow Flow

1. Monthly payment includes escrow portion
2. Escrow held in separate account
3. Disbursements recorded in `mortgage_escrow` table
4. Annual escrow analysis reconciles payments vs disbursements

### Example Entry

```sql
INSERT INTO mhb.mortgage_escrow (
    mortgage_id, 
    disbursement_date, 
    expense_type, 
    payee, 
    amount,
    description
) VALUES (
    1,  -- 711 Pine mortgage
    '2024-07-15',
    'property_tax',
    'Chippewa County Treasurer',
    1250.00,
    'Summer 2024 property taxes'
);
```

## Inter-Entity Transactions

### MHB Pays Personal Mortgage

When MHB account pays the Parnell (personal) mortgage:

**In MHB Books:**
```sql
-- Create trial entry
INSERT INTO acc.trial_entry (entry_date, description, entity)
VALUES ('2024-01-15', 'Parnell mortgage payment', 'mhb');

-- Debit receivable
INSERT INTO acc.trial_entry_line (entry_id, gl_account_code, debit)
VALUES (entry_id, 'mhb:receivable:per', 1234.56);

-- Credit bank account
INSERT INTO acc.trial_entry_line (entry_id, gl_account_code, credit)
VALUES (entry_id, 'mhb:checking', 1234.56);
```

**In Personal Books:**
```sql
-- Create trial entry
INSERT INTO acc.trial_entry (entry_date, description, entity)
VALUES ('2024-01-15', 'Parnell mortgage payment', 'per');

-- Debit mortgage principal
INSERT INTO acc.trial_entry_line (entry_id, gl_account_code, debit)
VALUES (entry_id, 'per:mortgage:parnell', 234.56);

-- Debit mortgage interest
INSERT INTO acc.trial_entry_line (entry_id, gl_account_code, debit)
VALUES (entry_id, 'per:mortgage:interest:parnell', 1000.00);

-- Credit payable to MHB
INSERT INTO acc.trial_entry_line (entry_id, gl_account_code, credit)
VALUES (entry_id, 'per:payable:mhb', 1234.56);
```

## Database Schema

### Mortgage Table

```sql
CREATE TABLE {entity}.mortgage (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50),
    gl_account_code VARCHAR(100) NOT NULL,
    lender VARCHAR(200) NOT NULL,
    loan_number VARCHAR(100),
    issued_on DATE NOT NULL,
    original_balance NUMERIC(12,2) NOT NULL,
    current_balance NUMERIC(12,2) NOT NULL,
    interest_rate NUMERIC(6,3) NOT NULL,
    monthly_payment NUMERIC(10,2),
    matures_on DATE NOT NULL,
    escrow_included BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active'
);
```

### Mortgage Payment Table

```sql
CREATE TABLE {entity}.mortgage_payment (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER REFERENCES {entity}.mortgage(id),
    payment_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    escrow NUMERIC(10,2) DEFAULT 0,
    balance_after NUMERIC(12,2) NOT NULL,
    bank_staging_id INTEGER REFERENCES acc.bank_staging(id)
);
```

### Mortgage Projection Table

```sql
CREATE TABLE {entity}.mortgage_projection (
    id SERIAL PRIMARY KEY,
    mortgage_id INTEGER REFERENCES {entity}.mortgage(id),
    projection_date TIMESTAMP NOT NULL,
    payment_number INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(10,2) NOT NULL,
    principal NUMERIC(10,2) NOT NULL,
    interest NUMERIC(10,2) NOT NULL,
    balance_after NUMERIC(12,2) NOT NULL,
    cumulative_interest NUMERIC(12,2) NOT NULL
);
```

## Current Portfolio

### MHB Properties

| Property | Address | Original | Balance | Rate | Maturity |
|----------|---------|----------|---------|------|----------|
| 711pine | 711 Pine Street | $66,621.85 | TBD | 8.500% | 2040-04-17 |
| 905brown | 905 Brown Street | $36,620.00 | TBD | 7.950% | 2039-08-16 |
| 819helen | 819 Helen Street | $67,014.00 | TBD | 8.250% | 2041-03-19 |

### Personal

| Property | Address | Original | Balance | Rate | Maturity |
|----------|---------|----------|---------|------|----------|
| parnell | 1108 Parnell Street | $180,000.00 | TBD | 3.750% | 2045-02-01 |

## Best Practices

1. **Import Regularly**: Import payments monthly to maintain accurate balances
2. **Verify Calculations**: Compare calculated P&I split with lender statements
3. **Track Escrow**: Record escrow disbursements when they occur
4. **Project Annually**: Regenerate amortization schedules annually or after rate changes
5. **Reconcile**: Compare projected vs actual quarterly to identify discrepancies
6. **Document Extra Payments**: Note reason for extra principal payments
7. **Review Escrow**: Annual escrow analysis to ensure proper funding

## Future Enhancements

- Automatic CSV import with parsing rules per lender
- Integration with bank import system
- Automated escrow analysis and projections
- Refinance analysis with closing costs
- Portfolio-level debt service coverage ratio
- Automated lender statement reconciliation
