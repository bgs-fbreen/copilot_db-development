# Schema Organization

## Overview

The Copilot Accounting System uses a multi-schema architecture to separate concerns between shared accounting infrastructure and entity-specific operations.

## Schema Structure

### ACC (Accounting) - Shared Infrastructure

The `acc` schema contains shared accounting infrastructure used across all entities:

**Bank & Transaction Management:**
- `bank_account` - Bank accounts for all entities
- `bank_staging` - Imported bank transactions awaiting categorization
- `vendor_gl_patterns` - Auto-categorization rules for transactions
- `pattern_suggestions` - Suggested patterns from manual corrections

**General Ledger:**
- `gl_accounts` - Chart of accounts for all entities
- `category` - Legacy hierarchical categories

**Journal System:**
- `trial_entry` / `trial_entry_line` - Pending journal entries
- `journal` / `journal_line` - Final, immutable journal entries

**Legacy Property Tables (Deprecated):**
- `properties` - **DEPRECATED**: Migrated to entity schemas
- `leases` - Lease tracking (consider migrating to MHB)
- `lease_tenants` - Tenant information
- `lease_guarantors` - Guarantor information
- `rent_payments` - Rent payment history
- `property_expenses` - Projected expenses
- `property_actual_expenses` - Actual expenses incurred
- `property_vacancy` - Vacancy tracking
- `rent_adjustments` - Late fees, credits, etc.

### MHB (MHB Properties LLC) - Rental Properties

The `mhb` schema contains all rental property operations:

**Core Property Management:**
- `property` - Rental property details (711pine, 819helen, 905brown)
- `tenant` - Tenant information
- `lease` - Lease agreements
- `rent_payment` - Rent payments received
- `property_expense` - Property operating expenses

**Mortgage Management:**
- `mortgage` - Mortgage loan details
- `mortgage_payment` - Payment history with P&I split
- `mortgage_projection` - Amortization schedules
- `mortgage_escrow` - Escrow disbursements

**Investment Analysis:**
- `property_valuation` - Property value over time
- `property_tax` - Property tax history
- `market_rent_comp` - Market rent comparables

### PER (Personal) - Personal Finances

The `per` schema contains personal financial operations:

**Residence:**
- `residence` - Personal residence details (1108 Parnell)

**Mortgage Management:**
- `mortgage` - Personal mortgage details
- `mortgage_payment` - Payment history with P&I split
- `mortgage_projection` - Amortization schedules
- `mortgage_escrow` - Escrow disbursements

### BGS (BGS Consulting) - Consulting Business

The `bgs` schema contains consulting business operations (structure defined in `sql/schema/02_bgs.sql`).

## Entity Codes

### Bank Account Codes
- `mhb:checking` - MHB Properties checking account
- `per:checking` - Personal checking account
- `bgs:checking` - BGS Consulting checking account

### GL Account Code Format

Format: `entity:type:detail`

**MHB Examples:**
- `mhb:mortgage:711pine` - 711 Pine Street mortgage liability
- `mhb:mortgage:interest:711pine` - Mortgage interest expense
- `mhb:rent:711pine` - Rental income
- `mhb:property:711pine` - Property asset

**Personal Examples:**
- `per:mortgage:parnell` - Parnell mortgage liability
- `per:mortgage:interest:parnell` - Mortgage interest expense
- `per:residence:parnell` - Residence asset

**BGS Examples:**
- `bgs:revenue:consulting` - Consulting revenue
- `bgs:expense:software` - Software expenses

## Inter-Entity Transactions

When one entity pays for another entity's expenses:

**Example: MHB pays personal mortgage**

MHB Books:
```sql
-- Debit: Receivable from Personal
-- Credit: MHB Bank Account
```

Personal Books:
```sql
-- Debit: Mortgage Principal & Interest
-- Credit: Payable to MHB
```

## Data Flow

1. **Import** → Transactions imported to `acc.bank_staging`
2. **Categorize** → GL codes assigned via patterns or manually
3. **Trial** → Converted to `acc.trial_entry` (double-entry format)
4. **Review** → Validate balances and correct errors
5. **Post** → Finalized to `acc.journal` (immutable)

## Migration History

- **Migration 015**: Created lease tracking system in `acc` schema
- **Migration 016**: Created `per` schema, enhanced `mhb` schema, added mortgage tracking

## Design Principles

1. **Separation of Concerns**: Each entity has its own schema for entity-specific data
2. **Shared Infrastructure**: Common accounting functions remain in `acc` schema
3. **Immutable Journal**: Final journal entries cannot be modified (reversals only)
4. **Entity Traceability**: All GL codes include entity prefix for clear attribution
5. **Deprecation over Deletion**: Legacy structures marked deprecated rather than dropped

## Future Enhancements

- Migrate lease tables from `acc` to `mhb` schema
- Add `bgs` schema enhancements for project-based accounting
- Create consolidated reporting views across entities
- Add inter-entity reconciliation tools
