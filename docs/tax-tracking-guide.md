# Property Tax Tracking Guide

## Overview

The Copilot Property Tax Tracking System provides comprehensive management of property tax bills, payments, and foreclosure risk analysis for rental properties (905brown, 711pine, 819helen) and personal residence (parnell).

## Michigan Property Tax Basics

### Tax Seasons and Due Dates

Michigan property taxes are billed twice per year:

| Season | Bill Period | Due Date | Covers |
|--------|-------------|----------|--------|
| **Summer** | July | September 14 | July 1 - December 31 |
| **Winter** | December | February 14 | January 1 - June 30 |

### Payment Schedule

- **Summer taxes**: Due September 14
  - Without penalty through September 14
  - 1% penalty after September 14
  - 3% additional penalty after March 1 following year
  
- **Winter taxes**: Due February 14
  - Without penalty through February 14
  - 1% penalty after February 14
  - 3% additional penalty after September 1 following year

## Key Tax Terms

### Assessment Values

| Term | Definition | Example |
|------|------------|---------|
| **SEV (State Equalized Value)** | Approximately 50% of market value | Market value $100,000 → SEV $50,000 |
| **Assessed Value** | Equal to SEV for most properties | $50,000 |
| **Taxable Value** | Capped value used for tax calculation | May be less than assessed if capped |

### Taxable Value Cap

Under Proposal A, taxable value increases are limited to the lesser of:
- Inflation rate (CPI)
- 5% per year

When a property is sold or transferred, taxable value becomes uncapped and resets to SEV.

### Principal Residence Exemption (PRE)

The PRE reduces the millage rate applied to your **primary residence**:

| Property Type | PRE Status | Effective Rate |
|--------------|------------|----------------|
| **Personal Residence** | 100% PRE | Lower rate (no school operating millage) |
| **Rental Property** | 0% PRE | Higher rate (includes school operating millage) |

**PRE Impact Example:**
- With PRE: ~18-24 mills (personal residence)
- Without PRE: ~42-48 mills (rental property)
- This represents approximately **2x higher** taxes for rentals!

### Millage Rate

The millage rate is expressed in "mills" where:
- **1 mill** = $1 per $1,000 of taxable value
- **Total tax** = (Taxable Value ÷ 1,000) × Total Mills

**Example Calculation:**
```
Taxable Value: $35,000
Millage Rate: 45.5 mills (rental property, no PRE)
Tax = ($35,000 ÷ 1,000) × 45.5 = $1,592.50
```

## Michigan Foreclosure Timeline

Unpaid property taxes in Michigan follow a strict foreclosure timeline:

| Years Delinquent | Status | Risk Level | Action Required |
|-----------------|--------|------------|----------------|
| **1 year** | Delinquent | 🟢 LOW | Pay to avoid penalties |
| **2 years** | Delinquent | 🟡 MEDIUM | Pay soon to avoid foreclosure risk |
| **3 years** | Foreclosure eligible | 🔴 HIGH | **PAY IMMEDIATELY** |
| **4+ years** | Foreclosure certain | 🔴 CRITICAL | **URGENT - Property seizure imminent** |

### Foreclosure Process

1. **Year 1**: Property becomes delinquent March 1 following tax year
2. **Year 2**: Continued delinquency, penalties accumulate
3. **Year 3**: Property becomes eligible for foreclosure
4. **Year 4**: County Treasurer petitions court for foreclosure judgment
5. **Foreclosure**: Property seized and sold at auction, often for pennies on the dollar

⚠️ **CRITICAL**: Once a property reaches 3+ years delinquent, the county can begin foreclosure proceedings. You could lose the property entirely!

## Database Schema

### Core Tables

#### `acc.property_tax_bill`
Tax bills with assessment values and payment tracking.

```sql
CREATE TABLE acc.property_tax_bill (
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) NOT NULL,        -- 905brown, 711pine, 819helen, parnell
    tax_year INTEGER NOT NULL,                  -- Tax year (e.g., 2024)
    tax_season VARCHAR(20) NOT NULL,            -- 'Summer' or 'Winter'
    assessed_value NUMERIC(12,2),               -- SEV/Assessed value
    taxable_value NUMERIC(12,2),                -- Taxable value (may be capped)
    pre_pct NUMERIC(5,2) DEFAULT 0,            -- PRE percentage (0 or 100)
    millage_rate NUMERIC(8,4),                  -- Mill rate
    total_due NUMERIC(12,2) NOT NULL,           -- Total amount due
    total_paid NUMERIC(12,2) DEFAULT 0,         -- Total paid so far
    balance_due NUMERIC(12,2) NOT NULL,         -- Remaining balance
    due_date DATE,                              -- Original due date
    paid_date DATE,                             -- Date fully paid
    payment_status VARCHAR(20),                 -- unpaid, partial, paid, delinquent
    late_fees NUMERIC(10,2) DEFAULT 0,
    interest_charges NUMERIC(10,2) DEFAULT 0,
    notes TEXT,
    CONSTRAINT uk_tax_bill UNIQUE (property_code, tax_year, tax_season)
);
```

#### `acc.property_tax_payment`
Individual payments applied to tax bills (supports partial payments).

```sql
CREATE TABLE acc.property_tax_payment (
    id SERIAL PRIMARY KEY,
    tax_bill_id INTEGER REFERENCES acc.property_tax_bill(id),
    payment_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(50),                 -- check, online, wire, etc.
    check_number VARCHAR(50),
    confirmation_number VARCHAR(100),
    bank_staging_id INTEGER,                    -- Link to bank import
    notes TEXT
);
```

### Views

#### `acc.v_property_tax_foreclosure_risk`
Properties at risk of tax foreclosure (3+ years delinquent).

```sql
CREATE VIEW acc.v_property_tax_foreclosure_risk AS
SELECT 
    property_code,
    tax_year,
    tax_season,
    total_due,
    balance_due,
    EXTRACT(YEAR FROM CURRENT_DATE) - tax_year as years_delinquent,
    CASE 
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 5 THEN 'CRITICAL'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 3 THEN 'HIGH'
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 2 THEN 'MEDIUM'
        ELSE 'LOW'
    END as risk_level
FROM acc.property_tax_bill
WHERE balance_due > 0
  AND EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 3;
```

#### `acc.v_property_tax_priority`
Payment priority recommendations based on foreclosure risk.

```sql
CREATE VIEW acc.v_property_tax_priority AS
SELECT 
    property_code,
    tax_year,
    tax_season,
    balance_due,
    EXTRACT(YEAR FROM CURRENT_DATE) - tax_year as years_delinquent,
    CASE 
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 5 THEN 1  -- CRITICAL
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 3 THEN 2  -- HIGH
        WHEN total_paid > 0 AND balance_due > 0 THEN 3               -- Partial payment
        WHEN EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 2 THEN 4  -- MEDIUM
        ELSE 5                                                        -- LOW
    END as priority_rank
FROM acc.property_tax_bill
WHERE balance_due > 0;
```

#### `acc.v_property_tax_trends`
Historical assessment and tax trends with year-over-year comparisons.

```sql
CREATE VIEW acc.v_property_tax_trends AS
SELECT 
    property_code,
    tax_year,
    MAX(assessed_value) as assessed_value,
    MAX(taxable_value) as taxable_value,
    MAX(pre_pct) as pre_pct,
    SUM(total_due) as annual_tax,
    SUM(total_paid) as annual_paid,
    SUM(balance_due) as annual_balance,
    LAG(MAX(assessed_value)) OVER (PARTITION BY property_code ORDER BY tax_year) as prev_assessed,
    LAG(SUM(total_due)) OVER (PARTITION BY property_code ORDER BY tax_year) as prev_tax
FROM acc.property_tax_bill
GROUP BY property_code, tax_year;
```

## Importing Tax Data

### CSV File Format

Create a CSV file with tax bill data:

```csv
property_code,tax_year,tax_season,assessed_value,taxable_value,pre_pct,millage_rate,total_due,due_date,notes
905brown,2024,Summer,45000,38500,0,45.5,1751.75,2024-09-14,
905brown,2024,Winter,45000,38500,0,45.5,1751.75,2025-02-14,
711pine,2024,Summer,52000,42000,0,45.5,1911.00,2024-09-14,
711pine,2024,Winter,52000,42000,0,45.5,1911.00,2025-02-14,
819helen,2024,Summer,48000,40000,0,45.5,1820.00,2024-09-14,
819helen,2024,Winter,48000,40000,0,45.5,1820.00,2025-02-14,
parnell,2024,Summer,95000,75000,100,18.5,1387.50,2024-09-14,Personal residence
parnell,2024,Winter,95000,75000,100,18.5,1387.50,2025-02-14,Personal residence
```

### Import Command

```bash
# Import tax data from CSV
copilot tax import --file tax_bills_2024.csv

# Import with specific year filter
copilot tax import --file tax_bills_2024.csv --year 2024
```

### Direct SQL Import

You can also import directly via SQL:

```sql
-- Import tax bill
INSERT INTO acc.property_tax_bill (
    property_code, tax_year, tax_season,
    assessed_value, taxable_value, pre_pct, millage_rate,
    total_due, balance_due, due_date, payment_status
) VALUES (
    '905brown', 2024, 'Summer',
    45000, 38500, 0, 45.5,
    1751.75, 1751.75, '2024-09-14', 'unpaid'
);
```

## Recording Payments

### Using CLI

```bash
# Record a payment interactively
copilot tax pay

# The wizard will prompt for:
# - Property code (905brown, 711pine, 819helen, parnell)
# - Tax year (e.g., 2024)
# - Tax season (Summer or Winter)
# - Payment amount
# - Payment date
# - Payment method (optional)
# - Check/confirmation number (optional)
```

### Using SQL

```sql
-- Record a payment
INSERT INTO acc.property_tax_payment (
    tax_bill_id,
    payment_date,
    amount,
    payment_method,
    check_number,
    notes
) VALUES (
    (SELECT id FROM acc.property_tax_bill 
     WHERE property_code = '905brown' 
       AND tax_year = 2024 
       AND tax_season = 'Summer'),
    '2024-09-10',
    1751.75,
    'check',
    '1234',
    'Paid in full'
);

-- Update bill totals (automatically via trigger or manually)
UPDATE acc.property_tax_bill
SET total_paid = (SELECT COALESCE(SUM(amount), 0) 
                  FROM acc.property_tax_payment 
                  WHERE tax_bill_id = acc.property_tax_bill.id),
    balance_due = total_due - total_paid,
    payment_status = CASE 
        WHEN balance_due = 0 THEN 'paid'
        WHEN total_paid > 0 THEN 'partial'
        ELSE 'unpaid'
    END
WHERE id = 123; -- Replace with actual bill ID
```

## Current Tax Situation

### Summary by Property

| Property | Outstanding | Foreclosure Risk | Status |
|----------|------------|------------------|--------|
| **905brown** | $7,479.31 | $1,962.37 | 🔴 3 bills at risk |
| **711pine** | $10,368.09 | $2,712.80 | 🔴 3 bills at risk |
| **819helen** | $8,861.15 | $1,987.58 | 🔴 3 bills at risk |
| **parnell** | $700.96 | $0.00 | 🟢 Personal residence |
| **TOTAL** | **$27,409.51** | **$6,662.75** | **9 bills at foreclosure risk** |

### Foreclosure Risk Bills Detail

⚠️ **All bills from 2022 and earlier are unpaid and at HIGH/CRITICAL risk!**

#### 905brown - Foreclosure Risk: $1,962.37
- 2022 Summer: $981.19 (4 years delinquent) 🔴 CRITICAL
- 2022 Winter: $981.18 (4 years delinquent) 🔴 CRITICAL

#### 711pine - Foreclosure Risk: $2,712.80
- 2022 Summer: $1,356.40 (4 years delinquent) 🔴 CRITICAL
- 2022 Winter: $1,356.40 (4 years delinquent) 🔴 CRITICAL

#### 819helen - Foreclosure Risk: $1,987.58
- 2022 Summer: $993.79 (4 years delinquent) 🔴 CRITICAL
- 2022 Winter: $993.79 (4 years delinquent) 🔴 CRITICAL

### Additional Outstanding Bills

In addition to foreclosure risk bills, each property has:
- 2023 Summer & Winter (3 years delinquent) - Next in line for foreclosure
- 2024 Summer & Winter (2 years delinquent) - Approaching foreclosure
- 2025 Summer & Winter (1 year delinquent) - Recent delinquency

## Annual Tax Calendar

### January
- Review year-end tax situation
- Plan for February winter tax payment
- Check for assessment notices

### February
- **Feb 14**: Winter taxes due
- Pay winter taxes to avoid 1% penalty
- Record payments in system

### March
- **Mar 1**: Summer taxes from previous year become delinquent
- Review any unpaid summer taxes
- Priority payment on oldest bills

### April
- Tax appeal deadline (usually mid-April)
- Review assessments for accuracy
- File appeals if needed

### May
- Prepare for summer tax bill
- Review projected increases
- Budget for July bill

### June
- Plan for summer tax payment
- Check property assessment changes

### July
- Receive summer tax bill
- Review assessment values
- Import new tax bills to system

### August
- Prepare summer tax payment
- Priority: pay oldest bills first

### September
- **Sep 14**: Summer taxes due
- Pay summer taxes to avoid 1% penalty
- Record payments in system
- **Sep 1**: Winter taxes from previous year accumulate additional 3% penalty

### October
- Review year-to-date tax payments
- Plan for upcoming winter bill

### November
- Review annual tax trends
- Prepare for December bill

### December
- Receive winter tax bill
- Review any assessment changes
- Import new tax bills to system
- Plan year-end tax payment strategy

## Payment Priority Strategy

### Immediate Priority (PAY FIRST)

**Minimum to avoid foreclosure: $6,662.75**

Pay ALL bills that are 3+ years delinquent (from 2022 and earlier):

1. **905brown**: 2022 Summer & Winter ($1,962.37)
2. **711pine**: 2022 Summer & Winter ($2,712.80)
3. **819helen**: 2022 Summer & Winter ($1,987.58)

### Secondary Priority (PAY NEXT)

Bills that are 2-3 years old (approaching foreclosure):

4. All 2023 Summer & Winter bills
5. All 2024 Summer & Winter bills

### Tertiary Priority (PAY LAST)

Recent bills (1 year old or less):

6. All 2025 Summer & Winter bills
7. Current year bills

### Strategy Notes

- **Always pay oldest bills first** to avoid foreclosure
- **Personal residence (parnell)** generally has lower effective tax rates due to PRE exemption, but foreclosure risk bills should still be prioritized
- **Partial payments** are acceptable - pay what you can toward oldest bills
- **Contact county treasurer** if unable to pay - payment plans may be available

## Useful SQL Queries

### Check Outstanding Balance by Property

```sql
SELECT 
    property_code,
    COUNT(*) as num_bills,
    SUM(total_due) as total_due,
    SUM(total_paid) as total_paid,
    SUM(balance_due) as balance_due
FROM acc.property_tax_bill
WHERE balance_due > 0
GROUP BY property_code
ORDER BY balance_due DESC;
```

### Find All Unpaid Bills

```sql
SELECT 
    property_code,
    tax_year,
    tax_season,
    total_due,
    total_paid,
    balance_due,
    due_date,
    payment_status
FROM acc.property_tax_bill
WHERE balance_due > 0
ORDER BY tax_year, property_code, tax_season;
```

### Calculate Foreclosure Risk

```sql
SELECT 
    property_code,
    COUNT(*) as at_risk_bills,
    SUM(balance_due) as total_at_risk
FROM acc.property_tax_bill
WHERE balance_due > 0
  AND EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 3
GROUP BY property_code
ORDER BY total_at_risk DESC;
```

### Payment History for Property

```sql
SELECT 
    b.tax_year,
    b.tax_season,
    b.total_due,
    p.payment_date,
    p.amount,
    p.payment_method,
    p.check_number
FROM acc.property_tax_bill b
LEFT JOIN acc.property_tax_payment p ON p.tax_bill_id = b.id
WHERE b.property_code = '905brown'
ORDER BY b.tax_year DESC, b.tax_season, p.payment_date;
```

### Assessment Trend Analysis

```sql
SELECT 
    property_code,
    tax_year,
    assessed_value,
    taxable_value,
    pre_pct,
    annual_tax,
    (annual_tax - prev_tax) as yoy_change,
    ROUND((annual_tax - prev_tax) / NULLIF(prev_tax, 0) * 100, 1) as yoy_pct_change
FROM acc.v_property_tax_trends
WHERE property_code = '711pine'
ORDER BY tax_year DESC
LIMIT 5;
```

### Current Year Tax Summary

```sql
SELECT 
    property_code,
    SUM(CASE WHEN tax_season = 'Summer' THEN total_due ELSE 0 END) as summer_tax,
    SUM(CASE WHEN tax_season = 'Winter' THEN total_due ELSE 0 END) as winter_tax,
    SUM(total_due) as annual_tax,
    SUM(total_paid) as paid_ytd,
    SUM(balance_due) as balance_ytd
FROM acc.property_tax_bill
WHERE tax_year = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY property_code
ORDER BY property_code;
```

## Contact Information

### Chippewa County Treasurer
**Property Tax Information and Payments**

**Address:**
Chippewa County Treasurer
319 Court Street
Sault Ste. Marie, MI 49783

**Phone:** (906) 635-6300  
**Fax:** (906) 635-6877

**Website:** https://www.chippewacountymi.gov/treasurer

**Office Hours:**
- Monday - Friday: 8:00 AM - 4:30 PM
- Closed on county holidays

**Online Payment:**
- Available through county website
- Credit/debit cards accepted (convenience fee applies)
- E-check payments available (lower fee)

**In-Person Payment:**
- Cash, check, money order accepted
- No convenience fee for in-person payments

**Mail Payments To:**
```
Chippewa County Treasurer
PO Box 250
Sault Ste. Marie, MI 49783
```

**Tax Information:**
- Current year bills available online
- Prior year delinquent tax information
- Payment history lookup
- Assessment appeal information

## Additional Resources

- [Michigan Department of Treasury - Property Tax](https://www.michigan.gov/treasury/property)
- [Chippewa County Equalization Department](https://www.chippewacountymi.gov/equalization)
- [Michigan Tax Tribunal - Assessment Appeals](https://www.michigan.gov/taxtrib)
- [Proposal A - Taxable Value Cap Information](https://www.michigan.gov/treasury/property/overview/proposal-a)

## Troubleshooting

### Issue: Cannot find tax bill in system

**Solution:**
1. Check if bill was imported: `SELECT * FROM acc.property_tax_bill WHERE property_code = 'XXX' AND tax_year = YYYY`
2. Import missing bill via CSV or SQL INSERT
3. Verify property_code spelling matches exactly

### Issue: Payment not reflecting in balance

**Solution:**
1. Check if payment was recorded: `SELECT * FROM acc.property_tax_payment WHERE tax_bill_id = [id]`
2. Recalculate totals:
```sql
UPDATE acc.property_tax_bill
SET total_paid = (SELECT COALESCE(SUM(amount), 0) 
                  FROM acc.property_tax_payment 
                  WHERE tax_bill_id = acc.property_tax_bill.id),
    balance_due = total_due - (SELECT COALESCE(SUM(amount), 0) 
                               FROM acc.property_tax_payment 
                               WHERE tax_bill_id = acc.property_tax_bill.id)
WHERE id = [bill_id];
```

### Issue: Foreclosure risk calculation seems wrong

**Solution:**
1. Check current date calculation: `SELECT EXTRACT(YEAR FROM CURRENT_DATE)`
2. Verify tax_year in bill: `SELECT tax_year FROM acc.property_tax_bill WHERE id = [id]`
3. Foreclosure risk is years_delinquent >= 3: `EXTRACT(YEAR FROM CURRENT_DATE) - tax_year >= 3`

### Issue: PRE exemption not showing correctly

**Solution:**
1. Verify pre_pct in bill: `SELECT pre_pct FROM acc.property_tax_bill WHERE id = [id]`
2. PRE should be:
   - 100 for personal residence (parnell)
   - 0 for rental properties (905brown, 711pine, 819helen)
3. Update if incorrect: `UPDATE acc.property_tax_bill SET pre_pct = 100 WHERE property_code = 'parnell'`
