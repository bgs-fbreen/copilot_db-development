# Lease Tracking System Guide

## Overview

The Copilot Lease Tracking System provides comprehensive management for rental properties (905brown, 711pine, 819helen) including:

- Property and lease management
- Tenant and guarantor contact tracking
- Projected vs actual income/expense tracking
- Vacancy tracking and rent adjustments
- P&L comparison and variance analysis
- Academic and calendar year reporting

## Database Schema

### Core Tables

#### Properties (`acc.properties`)
Base property information including purchase details and mortgage information.

```sql
-- Example property codes: 905brown, 711pine, 819helen
property_code, address, city, state, zip_code
purchase_date, purchase_price
mortgage_amount, mortgage_rate, mortgage_start_date, mortgage_term_months
```

#### Leases (`acc.leases`)
Lease agreements with rental terms and deposit handling.

```sql
property_id, start_date, end_date, monthly_rent
deposit_amount, deposit_applies_to_last_month
lease_type (fixed, month-to-month, academic)
status (active, expired, terminated, pending)
```

#### Lease Tenants (`acc.lease_tenants`)
Tenant contact information including student details.

```sql
lease_id, tenant_name, email, phone
is_primary, is_student, school_name, graduation_date
emergency_contact_name, emergency_contact_phone
```

#### Lease Guarantors (`acc.lease_guarantors`)
Parent/guarantor contact information with full addresses.

```sql
lease_id, guarantor_name, relationship, email, phone
address_line1, city, state, zip_code
```

#### Property Expenses (`acc.property_expenses`)
Projected recurring expenses.

```sql
property_id, expense_type, expense_name, amount
frequency (monthly, quarterly, annual, one-time)
due_month
```

### Actual Tracking Tables

#### Rent Payments (`acc.rent_payments`)
Individual rent payments received with status tracking.

```sql
lease_id, property_id, payment_date, amount, for_month
payment_method, payment_status (received, bounced, partial, waived, pending)
check_number, bank_staging_id
```

#### Property Actual Expenses (`acc.property_actual_expenses`)
Actual expenses incurred.

```sql
property_id, expense_date, expense_type, description, amount
vendor, check_number, bank_staging_id
```

#### Property Vacancy (`acc.property_vacancy`)
Vacancy periods between leases with lost rent calculation.

```sql
property_id, start_date, end_date, expected_monthly_rent, reason
```

#### Rent Adjustments (`acc.rent_adjustments`)
Late fees, credits, concessions, and other rent adjustments.

```sql
lease_id, property_id, adjustment_date, adjustment_type, amount
description, for_month
```

### Views

- `acc.v_projected_rent_monthly` - Monthly projected rental income
- `acc.v_actual_rent_monthly` - Actual rent received by month
- `acc.v_vacancy_monthly` - Vacancy impact with lost rent
- `acc.v_adjustments_monthly` - Monthly adjustments by type
- `acc.v_property_monthly_comparison` - Monthly variance analysis
- `acc.v_property_pnl_comparison` - Annual P&L comparison
- `acc.v_lease_details` - Lease summary with tenant info
- `acc.v_lease_contact_directory` - All contacts for active leases

## Installation

1. Run the database migration:

```bash
psql -h <host> -U <user> -d copilot_db -f sql/migrations/015_create_leases_table.sql
```

2. Verify the lease command is available:

```bash
copilot lease --help
```

## Usage Examples

### 1. Property Management

#### List all properties
```bash
copilot lease property-list
```

#### Show property details
```bash
copilot lease property-show 711pine
```

#### Update property information
```bash
copilot lease property-update 711pine --mortgage-amount 150000 --mortgage-rate 6.5
```

### 2. Expense Management (Projected)

#### Add projected expenses
```bash
# Summer property tax
copilot lease expense-add 711pine --type summer_tax \
  --name "Summer Property Tax" --amount 1200 \
  --frequency annual --due-month 7

# Winter property tax
copilot lease expense-add 711pine --type winter_tax \
  --name "Winter Property Tax" --amount 1800 \
  --frequency annual --due-month 12

# Insurance
copilot lease expense-add 711pine --type insurance \
  --name "Homeowners Insurance" --amount 1200 \
  --frequency annual
```

#### List projected expenses
```bash
copilot lease expense-list 711pine
```

### 3. Lease Management

#### Add a new lease
```bash
copilot lease add --property 711pine \
  --start 2024-06-01 --end 2025-05-31 \
  --rent 850 --deposit 850 \
  --deposit-last-month --lease-type academic
```

#### List leases
```bash
# All leases
copilot lease list

# Filter by property
copilot lease list --property 711pine

# Filter by status
copilot lease list --status active
```

#### Show lease details
```bash
copilot lease show 1
```

#### Update lease
```bash
copilot lease update 1 --status terminated
```

### 4. Tenant Management

#### Add tenants to a lease
```bash
# Primary tenant
copilot lease tenant-add 1 \
  --name "John Smith" \
  --email "john@university.edu" \
  --phone "555-1234" \
  --primary --student \
  --school "CMU" \
  --graduation 2025-05-15

# Additional tenant
copilot lease tenant-add 1 \
  --name "Jane Doe" \
  --email "jane@university.edu" \
  --phone "555-5678" \
  --student --school "CMU"
```

#### List tenants
```bash
copilot lease tenant-list 1
```

### 5. Guarantor Management

#### Add guarantor
```bash
copilot lease guarantor-add 1 \
  --name "Jane Smith" \
  --relationship parent \
  --phone "555-5678" \
  --email "jane@email.com" \
  --address "123 Main St" \
  --city "Pittsburgh" \
  --state "PA" \
  --zip "15213"
```

#### List guarantors
```bash
copilot lease guarantor-list 1
```

### 6. Payment Tracking

#### Record rent payments
```bash
# Single payment
copilot lease payment-add --property 711pine \
  --amount 850 --date 2024-06-05 \
  --for-month 2024-06-01 --method check \
  --check-number 1001

# Payment with auto-detected lease
copilot lease payment-add --property 711pine \
  --amount 850 --date 2024-07-01 \
  --for-month 2024-07-01 --method check
```

#### List payments
```bash
# All payments
copilot lease payment-list

# Filter by property
copilot lease payment-list --property 711pine

# Filter by year and month
copilot lease payment-list --year 2024 --month 6
```

### 7. Actual Expense Tracking

#### Record actual expenses
```bash
copilot lease actual-expense-add 711pine \
  --date 2024-07-15 --type summer_tax \
  --description "Summer 2024 Property Tax" \
  --amount 1200 --check-number 2001

copilot lease actual-expense-add 711pine \
  --date 2024-08-20 --type repair \
  --description "Plumbing repair" \
  --amount 350 --vendor "Joe's Plumbing"
```

### 8. Vacancy Tracking

#### Record vacancy periods
```bash
copilot lease vacancy-add 711pine \
  --start 2024-05-15 --end 2024-05-31 \
  --rent 850 --reason between_leases
```

#### List vacancies
```bash
# All vacancies
copilot lease vacancy-list

# Filter by property
copilot lease vacancy-list --property 711pine
```

### 9. Adjustments

#### Record adjustments
```bash
# Late fee
copilot lease adjustment-add 1 \
  --date 2024-07-15 --type late_fee \
  --amount 50 --description "Late payment fee" \
  --for-month 2024-07-01

# Credit
copilot lease adjustment-add 1 \
  --date 2024-08-01 --type credit \
  --amount -100 --description "Maintenance discount" \
  --for-month 2024-08-01
```

### 10. Reports and Analysis

#### Contact directory
```bash
copilot lease contacts
```

#### Current lease status
```bash
copilot lease status
```

#### Income report (calendar or academic year)
```bash
# Calendar year report
copilot lease report --year 2024 --type calendar

# Academic year report (June-May)
copilot lease report --year 2024 --type academic
```

#### Projected vs Actual Comparison
```bash
# Compare all properties
copilot lease compare --year 2024

# Compare specific property
copilot lease compare --year 2024 --property 711pine
```

## Security Deposit Handling

The system properly handles security deposits that apply to last month's rent (common for student rentals):

- Set `deposit_applies_to_last_month` flag when creating lease
- The `v_projected_rent_monthly` view automatically adjusts the last month's rent
- Cash flow vs income recognition is properly tracked

Example:
```bash
copilot lease add --property 711pine \
  --start 2024-06-01 --end 2025-05-31 \
  --rent 850 --deposit 850 \
  --deposit-last-month  # This flag indicates deposit covers May 2025
```

## Variance Analysis

The comparison report (`copilot lease compare`) provides comprehensive variance analysis:

### Income Variances
- **Projected Rent**: Expected rental income based on lease terms
- **Actual Rent Received**: Money actually collected
- **Adjustments**: Late fees, credits, concessions
- **Vacancy Loss**: Lost income during vacancy periods
- **Bounced Checks**: Failed payments
- **Waived Rent**: Rent forgiven

### Expense Variances
- **Projected Expenses**: Budgeted recurring expenses
- **Actual Expenses**: Real costs incurred
- **Variance**: Difference between projected and actual

### Net Income Variance
- Shows overall financial performance vs projection
- Highlights areas needing attention

## Academic Year Reporting

Student rental properties often operate on academic years (June-May). Use the academic year report type:

```bash
copilot lease report --year 2024 --type academic
```

This reports from June 2024 through May 2025, aligning with typical student lease periods.

## Best Practices

### 1. Property Setup
1. Add property with purchase details
2. Set up projected expenses (taxes, insurance, maintenance)
3. Keep mortgage information current

### 2. Lease Management
1. Create lease with accurate dates and rent
2. Add all tenants (mark primary contact)
3. Add guarantors with complete contact info
4. Set `deposit-last-month` flag if applicable

### 3. Monthly Tracking
1. Record rent payments as received
2. Record actual expenses when paid
3. Track any adjustments (late fees, credits)
4. Update vacancy periods when they occur

### 4. Regular Reviews
1. Run monthly comparison reports
2. Review payment status and follow up on late payments
3. Compare actual vs projected expenses
4. Adjust projections as needed

### 5. Year-End Process
1. Run annual comparison report
2. Review variances and document reasons
3. Update projected expenses for next year
4. Archive closed leases

## Database Maintenance

### Updating Lease Status
Leases should be updated from 'active' to 'expired' or 'terminated':

```bash
copilot lease update 1 --status expired
```

### Archiving Old Data
Completed leases remain in the database for historical reporting. Use the status field to filter:

```bash
# Show only active leases
copilot lease list --status active
```

### Data Integrity
The system enforces:
- Date constraints (end_date > start_date)
- Positive rent amounts
- Valid status values
- Referential integrity (cascading deletes for tenants/guarantors)

## Troubleshooting

### Common Issues

**Issue**: "Property not found"
```bash
# Solution: Check property code
copilot lease property-list
```

**Issue**: "No active lease found"
```bash
# Solution: Verify lease dates cover payment month or specify lease ID
copilot lease list --property 711pine
copilot lease payment-add --property 711pine --lease 1 ...
```

**Issue**: Vacancy loss calculation seems wrong
```bash
# Solution: Check vacancy dates don't overlap with active lease
copilot lease list --property 711pine
copilot lease vacancy-list --property 711pine
```

## Support

For issues or questions:
1. Check this guide
2. Use `--help` on any command
3. Review database schema comments
4. Consult with system administrator

## Future Enhancements

Potential future features:
- Import payments from `bank_staging` automatically
- Email/SMS rent reminders to tenants
- Automated late fee calculation
- Lease renewal workflow
- Maintenance request tracking
- Document storage (lease PDFs, invoices)
