# Property Data Population Guide

This guide provides detailed instructions for populating all property-related tables to enable accurate investment analysis through the `copilot property` and `copilot mortgage` commands.

---

## Overview

### Entity Structure
- **MHB Properties LLC** (`mhb` schema) - Rental properties: 711pine, 819helen, 905brown
- **Personal** (`per` schema) - Personal residence: parnell

### Data Dependencies
```
mhb.property ─────────────────┬──► mhb.mortgage ──────► mhb.mortgage_payment
                              │                    └──► mhb.mortgage_escrow
                              │                    └──► mhb.mortgage_projection
                              ├──► mhb.property_tax
                              ├──► mhb.property_valuation
                              ├──► mhb.lease ──────────► mhb.tenant
                              └──► mhb.market_rent_comp

per.residence ────────────────┬──► per.mortgage ───────► per.mortgage_payment
                              │                     └──► per.mortgage_escrow
                              └──► per.mortgage_projection
```

---

## 1. mhb.mortgage - MHB Property Mortgages

### Purpose
Stores current mortgage information for MHB rental properties. This is the foundation for all mortgage-related analysis.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | FK to mhb.property (711pine, 819helen, 905brown) |
| `lender` | VARCHAR(200) | Yes | Lender name (e.g., "Central Savings Bank") |
| `loan_number` | VARCHAR(100) | No | Loan/account number |
| `original_balance` | NUMERIC(12,2) | Yes | Original loan amount at closing |
| `current_balance` | NUMERIC(12,2) | Yes | Current outstanding balance |
| `interest_rate` | NUMERIC(5,3) | Yes | Current annual interest rate (e.g., 8.250 for 8.25%) |
| `monthly_payment` | NUMERIC(10,2) | No | Monthly P&I payment amount |
| `issued_on` | DATE | Yes | Loan origination date |
| `matures_on` | DATE | Yes | Loan maturity date |
| `status` | VARCHAR(20) | No | 'active', 'paid_off', 'refinanced' (default: 'active') |
| `gl_account_code` | VARCHAR(100) | No | GL code (e.g., mhb:mortgage:711pine) |
| `notes` | TEXT | No | Additional notes |

### Data Sources
- **Current balance**: Latest mortgage statement or online banking portal
- **Interest rate**: Mortgage statement (check for recent rate changes)
- **Monthly payment**: Mortgage statement or payment history
- **Original balance**: Closing documents or initial loan paperwork
- **Issue/maturity dates**: Loan documents or mortgage statement

### Instructions
1. Log into your bank's online portal or locate latest mortgage statements
2. For each property, record:
   - Current principal balance (not payoff amount)
   - Current interest rate
   - Monthly payment amount (P&I only, or P&I+escrow - note which)
3. Update the `current_balance` field - this should be updated monthly or after importing payments

### Validation
```sql
-- Verify mortgage data is complete
SELECT property_code, lender, original_balance, current_balance, interest_rate, 
       issued_on, matures_on, status
FROM mhb.mortgage
ORDER BY property_code;
```

---

## 2. per.mortgage - Personal Mortgage (Parnell)

### Purpose
Stores mortgage information for personal residence. Same structure as mhb.mortgage but in the `per` schema.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `residence_id` | INTEGER | No | FK to per.residence |
| `property_code` | VARCHAR(50) | Yes | Property identifier (parnell) |
| `lender` | VARCHAR(200) | Yes | Lender name |
| `loan_number` | VARCHAR(100) | No | Loan/account number |
| `original_balance` | NUMERIC(12,2) | Yes | Original loan amount |
| `current_balance` | NUMERIC(12,2) | Yes | Current outstanding balance |
| `interest_rate` | NUMERIC(5,3) | Yes | Current annual interest rate |
| `monthly_payment` | NUMERIC(10,2) | No | Monthly payment amount |
| `issued_on` | DATE | Yes | Loan origination date |
| `maturity_date` | DATE | Yes | Loan maturity date |
| `status` | VARCHAR(20) | No | 'active', 'paid_off', 'refinanced' |
| `gl_account_code` | VARCHAR(100) | No | GL code (per:mortgage:parnell) |
| `notes` | TEXT | No | Additional notes |

### Data Sources
Same as mhb.mortgage - use mortgage statements or online banking.

### Instructions
1. Locate your Parnell mortgage statement
2. Record current balance, rate, and payment
3. Note: Parnell mortgage is paid from MHB account - this creates inter-entity transactions

### Validation
```sql
SELECT property_code, lender, original_balance, current_balance, interest_rate,
       issued_on, maturity_date, status
FROM per.mortgage;
```

---

## 3. mhb.property - Property Details

### Purpose
Core property information including purchase history and current valuation. Required for ROI and equity calculations.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `code` | VARCHAR(50) | Yes | Unique identifier (711pine, 819helen, 905brown) |
| `address` | VARCHAR(255) | Yes | Street address |
| `city` | VARCHAR(100) | Yes | City |
| `state` | VARCHAR(2) | Yes | State abbreviation |
| `zip` | VARCHAR(10) | Yes | ZIP code |
| `property_type` | VARCHAR(50) | No | 'single_family', 'duplex', 'multi_family' |
| `bedrooms` | INTEGER | No | Number of bedrooms |
| `bathrooms` | NUMERIC(3,1) | No | Number of bathrooms |
| `square_feet` | INTEGER | No | Living area square footage |
| `lot_size` | NUMERIC(10,2) | No | Lot size in acres or sq ft |
| `year_built` | INTEGER | No | Year constructed |
| `purchase_date` | DATE | Yes | Date of purchase |
| `purchase_price` | NUMERIC(12,2) | Yes | Original purchase price |
| `current_value` | NUMERIC(12,2) | Yes | Current estimated market value |
| `status` | VARCHAR(20) | No | 'active', 'sold', 'pending_sale' |

### Data Sources
- **Purchase date/price**: Closing documents, HUD-1 settlement statement, or deed
- **Current value**: Zillow Zestimate, Redfin estimate, recent appraisal, or comparable sales
- **Property details**: County assessor records, listing history, or personal records

### Instructions
1. Gather closing documents for each property
2. For current value estimates:
   - Check Zillow.com and search for your address
   - Check Redfin.com for comparison
   - Consider ordering an appraisal for accuracy (especially for refinancing)
   - Use conservative estimate (lower of multiple sources)
3. Property type classification:
   - 711pine: duplex (if 2 units) or single_family
   - 819helen: single_family (4 bedroom)
   - 905brown: single_family (3 bedroom)

### Validation
```sql
SELECT code, address, purchase_date, purchase_price, current_value,
       (current_value - purchase_price) as appreciation
FROM mhb.property
ORDER BY code;
```

---

## 4. per.residence - Personal Residence Details

### Purpose
Personal residence information for Parnell property. Similar to mhb.property but simpler (no rental fields).

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | Unique identifier (parnell) |
| `address` | VARCHAR(255) | Yes | Street address |
| `city` | VARCHAR(100) | Yes | City |
| `state` | VARCHAR(2) | Yes | State abbreviation |
| `zip` | VARCHAR(10) | Yes | ZIP code |
| `purchase_date` | DATE | Yes | Date of purchase |
| `purchase_price` | NUMERIC(12,2) | Yes | Original purchase price |
| `current_value` | NUMERIC(12,2) | Yes | Current estimated market value |
| `notes` | TEXT | No | Additional notes |

### Data Sources
Same as mhb.property - closing documents and online valuation tools.

### Instructions
1. Locate closing documents from 2015 purchase
2. Get current value estimate from Zillow/Redfin
3. Update current_value periodically (annually recommended)

### Validation
```sql
SELECT property_code, address, purchase_date, purchase_price, current_value
FROM per.residence;
```

---

## 5. mhb.property_tax - Property Tax History

### Purpose
Tracks property tax assessments and payments. Essential for expense tracking and tax reporting.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | FK to mhb.property |
| `tax_year` | INTEGER | Yes | Tax year |
| `assessed_value` | NUMERIC(12,2) | No | SEV (State Equalized Value) or assessed value |
| `taxable_value` | NUMERIC(12,2) | No | Taxable value (may differ from assessed) |
| `millage_rate` | NUMERIC(8,4) | No | Mill rate used for calculation |
| `annual_tax` | NUMERIC(10,2) | Yes | Total annual property tax |
| `summer_tax` | NUMERIC(10,2) | No | Summer tax bill amount |
| `winter_tax` | NUMERIC(10,2) | No | Winter tax bill amount |
| `paid_date` | DATE | No | Date tax was paid |
| `paid_amount` | NUMERIC(10,2) | No | Amount paid |
| `paid_from` | VARCHAR(100) | No | 'escrow', 'direct', account code |

### Data Sources
- **Tax bills**: Summer tax bill (July) and Winter tax bill (December)
- **County assessor**: Online property records for assessed values
- **Escrow statements**: If taxes paid through escrow

### Instructions
1. Locate property tax bills for each property
   - Michigan has summer (July 1) and winter (December 1) taxes
2. Record both assessed value and taxable value from the bill
3. Note whether taxes are paid from escrow or directly
4. For historical data, check county treasurer's website for payment history

### Michigan-Specific Notes
- SEV (State Equalized Value) = approximately 50% of market value
- Taxable Value is capped by Proposal A (limited annual increases)
- Summer taxes typically go to schools, winter to county/township

### Validation
```sql
SELECT property_code, tax_year, assessed_value, annual_tax,
       summer_tax, winter_tax, paid_date
FROM mhb.property_tax
WHERE tax_year >= 2023
ORDER BY property_code, tax_year;
```

---

## 6. mhb.mortgage_escrow - Escrow Disbursements

### Purpose
Tracks insurance and tax payments made from mortgage escrow accounts. Important for understanding true housing costs.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `mortgage_id` | INTEGER | Yes | FK to mhb.mortgage |
| `trans_date` | DATE | Yes | Transaction/disbursement date |
| `amount` | NUMERIC(10,2) | Yes | Amount (negative for disbursements) |
| `escrow_type` | VARCHAR(50) | Yes | 'insurance', 'property_tax', 'pmi', 'other' |
| `description` | TEXT | No | Description of disbursement |
| `reference` | VARCHAR(100) | No | Check number or reference |

### Data Sources
- **Mortgage statements**: Monthly statements show escrow activity
- **Annual escrow analysis**: Yearly statement from lender
- **Bank CSV files**: Can be imported via `copilot mortgage import`

### Instructions
1. Review mortgage statements for escrow disbursements
2. Common disbursements:
   - Annual homeowners insurance premium (typically March-April)
   - Summer property tax (July)
   - Winter property tax (December)
3. Record as negative amounts (money leaving escrow)
4. If importing from CSV, the `copilot mortgage import` command will detect these

### Sign Convention
- **Negative amounts**: Disbursements (insurance paid, taxes paid)
- **Positive amounts**: Escrow deposits (portion of monthly payment)

### Validation
```sql
SELECT m.property_code, e.trans_date, e.escrow_type, e.amount, e.description
FROM mhb.mortgage_escrow e
JOIN mhb.mortgage m ON m.id = e.mortgage_id
ORDER BY e.trans_date DESC;
```

---

## 7. mhb.property_valuation - Valuation History

### Purpose
Tracks property values over time from multiple sources. Enables appreciation analysis and supports refinancing decisions.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | FK to mhb.property |
| `valuation_date` | DATE | Yes | Date of valuation |
| `valuation_type` | VARCHAR(50) | Yes | Type of valuation |
| `value` | NUMERIC(12,2) | Yes | Valuation amount |
| `source` | VARCHAR(200) | No | Source of valuation |
| `notes` | TEXT | No | Additional notes |

### Valuation Types
| Type | Description | When to Use |
|------|-------------|-------------|
| `purchase` | Original purchase price | One-time at acquisition |
| `appraisal` | Professional appraisal | Refinancing, HELOC, sale |
| `assessed` | Tax assessor value | Annually from tax records |
| `market_estimate` | Online estimate | Periodic tracking (Zillow, Redfin) |
| `comp_analysis` | Comparable sales analysis | When evaluating sale/purchase |
| `insurance` | Insurance replacement value | From insurance policy |

### Data Sources
- **Purchase**: Closing documents
- **Appraisal**: Appraisal report (if refinanced or obtained HELOC)
- **Assessed**: Property tax bill or county assessor website
- **Market estimate**: Zillow.com, Redfin.com, Realtor.com

### Instructions
1. Start with purchase price as first valuation entry
2. Add current market estimate from Zillow/Redfin
3. Add assessed value from tax records
4. Update market estimates quarterly or semi-annually
5. Add appraisals when obtained

### Validation
```sql
SELECT property_code, valuation_date, valuation_type, value, source
FROM mhb.property_valuation
ORDER BY property_code, valuation_date DESC;
```

---

## 8. mhb.lease - Lease Agreements

### Purpose
Tracks lease terms for rental properties. Required for rent income projections and tenant management.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | FK to mhb.property |
| `start_date` | DATE | Yes | Lease start date |
| `end_date` | DATE | Yes | Lease end date |
| `monthly_rent` | NUMERIC(10,2) | Yes | Monthly rent amount |
| `deposit_amount` | NUMERIC(10,2) | No | Security deposit held |
| `deposit_applies_to_last_month` | BOOLEAN | No | If deposit covers last month |
| `lease_type` | VARCHAR(20) | No | 'fixed', 'month_to_month' |
| `status` | VARCHAR(20) | No | 'active', 'expired', 'terminated', 'pending' |
| `notes` | TEXT | No | Special terms or notes |

### Data Sources
- **Lease agreements**: Signed lease documents
- **Rent records**: Bank deposits, payment tracking

### Instructions
1. Locate current lease agreement for each property
2. Record key terms:
   - Start and end dates
   - Monthly rent amount
   - Security deposit amount and terms
3. For student rentals (academic year):
   - Typical term: June 1 - May 31
   - Note if deposit applies to last month's rent
4. Update status when lease expires or is renewed

### Lease Status Values
| Status | Description |
|--------|-------------|
| `active` | Current, valid lease |
| `expired` | Past end date, may be month-to-month |
| `terminated` | Ended early |
| `pending` | Signed but not yet started |

### Validation
```sql
SELECT l.property_code, l.start_date, l.end_date, l.monthly_rent, 
       l.deposit_amount, l.status
FROM mhb.lease l
WHERE l.status = 'active'
ORDER BY l.property_code;
```

---

## 9. mhb.market_rent_comp - Market Rent Comparables

### Purpose
Stores comparable rental listings to analyze whether current rents are at market rate. Supports rent increase decisions.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `property_code` | VARCHAR(50) | Yes | Property being compared |
| `comp_date` | DATE | Yes | Date comparison was made |
| `comp_address` | VARCHAR(255) | Yes | Address of comparable property |
| `comp_city` | VARCHAR(100) | No | City (default: same as subject) |
| `bedrooms` | INTEGER | No | Number of bedrooms |
| `bathrooms` | NUMERIC(3,1) | No | Number of bathrooms |
| `square_feet` | INTEGER | No | Square footage if known |
| `rent_amount` | NUMERIC(10,2) | Yes | Listed or actual rent |
| `includes_utilities` | BOOLEAN | No | If rent includes utilities |
| `source` | VARCHAR(100) | No | Where listing was found |
| `listing_url` | TEXT | No | URL to listing |
| `notes` | TEXT | No | Property condition, amenities, etc. |

### Data Sources
- **Zillow Rentals**: zillow.com/homes/for_rent
- **Apartments.com**: apartments.com
- **Craigslist**: craigslist.org housing section
- **Facebook Marketplace**: Rental listings
- **Local property managers**: Ask about going rates

### Instructions
1. Search for rentals in Sault Ste. Marie area
2. Filter for similar properties:
   - Same number of bedrooms (±1)
   - Similar condition
   - Same general area
3. Record 3-5 comparables per property
4. Note differences (newer, includes utilities, better location, etc.)
5. Update comparables every 6-12 months or before lease renewal

### Comparison Tips
- Adjust for differences:
  - Utilities included: Add $100-200 to rent for comparison
  - Newer/renovated: May command 10-20% premium
  - Location: Downtown vs. residential
- Use median of comparables rather than average

### Validation
```sql
SELECT c.property_code, c.comp_date, c.comp_address, c.bedrooms, 
       c.rent_amount, c.source
FROM mhb.market_rent_comp c
ORDER BY c.property_code, c.comp_date DESC;

-- Compare to current rents
SELECT p.code, l.monthly_rent as current_rent,
       AVG(c.rent_amount) as avg_market_rent,
       AVG(c.rent_amount) - l.monthly_rent as rent_gap
FROM mhb.property p
LEFT JOIN mhb.lease l ON l.property_code = p.code AND l.status = 'active'
LEFT JOIN mhb.market_rent_comp c ON c.property_code = p.code 
    AND c.comp_date > CURRENT_DATE - INTERVAL '6 months'
GROUP BY p.code, l.monthly_rent;
```

---

## 10. mhb.mortgage_payment - Payment History

### Purpose
Detailed payment history with principal/interest breakdown. Populated via `copilot mortgage import` from bank CSV files.

### Table Structure
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | Auto | Primary key |
| `mortgage_id` | INTEGER | Yes | FK to mhb.mortgage |
| `payment_date` | DATE | Yes | Date payment was applied |
| `total_amount` | NUMERIC(10,2) | Yes | Total payment amount |
| `principal` | NUMERIC(10,2) | Yes | Principal portion |
| `interest` | NUMERIC(10,2) | Yes | Interest portion |
| `escrow` | NUMERIC(10,2) | No | Escrow portion (if applicable) |
| `extra_principal` | NUMERIC(10,2) | No | Additional principal payment |
| `balance_after` | NUMERIC(12,2) | Yes | Remaining balance after payment |
| `source` | VARCHAR(50) | No | 'import', 'manual', 'calculated' |

### Data Sources
- **Bank CSV files**: Downloaded from mortgage lender's website
- **Monthly statements**: Manual entry if CSV not available
- **Annual mortgage statement**: Year-end summary with totals

### Instructions
This table is primarily populated via the `copilot mortgage import` command:

```bash
# Import mortgage payment history from CSV
copilot mortgage import --file 711pine.csv --property 711pine
copilot mortgage import --file 819helen.csv --property 819helen
copilot mortgage import --file 905brown.csv --property 905brown
copilot mortgage import --file parnell.csv --property parnell
```

**Note**: The import command handles:
- Parsing various CSV formats
- Calculating P&I split based on balance and rate
- Handling reversals and adjustments
- Detecting rate changes
- Identifying escrow disbursements

### Manual Entry
If CSV import is not available, you can enter payments manually, but you'll need to calculate the P&I split:

```
Interest = Previous Balance × (Annual Rate ÷ 12)
Principal = Total Payment - Interest - Escrow
New Balance = Previous Balance - Principal
```

### Validation
```sql
-- Payment history summary
SELECT m.property_code, 
       COUNT(*) as payment_count,
       SUM(p.principal) as total_principal_paid,
       SUM(p.interest) as total_interest_paid,
       MIN(p.balance_after) as current_balance
FROM mhb.mortgage_payment p
JOIN mhb.mortgage m ON m.id = p.mortgage_id
GROUP BY m.property_code;

-- Verify balance consistency
SELECT m.property_code, m.current_balance as mortgage_balance,
       (SELECT balance_after FROM mhb.mortgage_payment 
        WHERE mortgage_id = m.id ORDER BY payment_date DESC LIMIT 1) as last_payment_balance
FROM mhb.mortgage m;
```

---

## Data Entry Priority

### Minimum Required (for basic analysis)
1. ✅ `mhb.mortgage` - Current balances and rates
2. ✅ `per.mortgage` - Parnell current balance
3. ✅ `mhb.property` - Purchase prices and current values
4. ✅ `per.residence` - Parnell purchase price and value

### Recommended (for full analysis)
5. `mhb.property_tax` - Annual tax amounts
6. `mhb.mortgage_escrow` - Insurance payments
7. `mhb.lease` - Current rent amounts

### Optional (for advanced analysis)
8. `mhb.property_valuation` - Historical values
9. `mhb.market_rent_comp` - Rent comparisons
10. `mhb.mortgage_payment` - Full payment history

---

## Verification Commands

After populating data, verify with these commands:

```bash
# List all mortgages with current balances
copilot mortgage list

# Show detailed mortgage info
copilot mortgage show 711pine

# List all properties with values
copilot property list

# Show property details with equity calculation
copilot property show 711pine

# Full investment analysis (requires complete data)
copilot property analyze 711pine

# Portfolio dashboard
copilot property dashboard
```

---

## Maintenance Schedule

| Task | Frequency | Tables Updated |
|------|-----------|----------------|
| Update mortgage balances | Monthly | mhb.mortgage, per.mortgage |
| Import mortgage payments | Monthly | mhb.mortgage_payment |
| Update property values | Quarterly | mhb.property, mhb.property_valuation |
| Record tax payments | Semi-annually | mhb.property_tax |
| Record insurance payments | Annually | mhb.mortgage_escrow |
| Update lease info | At renewal | mhb.lease |
| Update market comps | Semi-annually | mhb.market_rent_comp |
