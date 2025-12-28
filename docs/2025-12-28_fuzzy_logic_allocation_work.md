# Fuzzy Logic Allocation Work - 2025-12-28

## Overview
Session focused on categorizing bank transactions in `acc.bank_staging` using pattern matching against `acc.vendor_gl_patterns` table, with manual review and corrections.

## Starting Point
- **736 total transactions** in staging table
- Multiple transactions with `gl_account_code = 'TODO'` requiring categorization
- Existing vendor patterns in `acc.vendor_gl_patterns` for automatic matching

## Process

### 1. Pattern Matching Approach
Transactions were matched against vendor patterns using description field:
- Patterns stored in `acc.vendor_gl_patterns` with columns: `pattern`, `gl_account_code`, `entity`, `priority`
- Higher priority patterns take precedence when multiple patterns match
- Matching uses `ILIKE` for case-insensitive partial matching

### 2. Batch Updates by Category
Applied GL codes based on description patterns:

| Pattern | GL Account Code | Category |
|---------|-----------------|----------|
| USAA FUNDS TRANSFER | per:insurance:auto | Auto Insurance |
| NORTHWESTERN MUTUAL | per:insurance:life:fb | Life Insurance |
| BLUE CROSS | per:insurance:health | Health Insurance |
| AT&T PAYMENT | per:telecom:cell | Cell Phone |
| SPECTRUM | per:telecom:cable | Cable/Internet |
| GM FINANCIAL | per:auto:payment | Auto Payment |
| SHELL, MARATHON, KRIST OIL, BP, CIRCLE K, CASEYS | per:auto:gas / bgs:proj_exp:gas | Gasoline |
| HUNTINGTON SVC CHG | per:bank:fee | Bank Fees |
| STATE OF MICHIGAN | bgs:license:state | State Licensing |
| GEODE ENVIRON | bgs:sub:geode | Subcontractor |
| CNH IND AMERICA (credits) | bgs:ar:cnh | Client A/R |

### 3. Data Corrections

#### Entity Prefix Corrections
- **Issue:** Many transactions incorrectly coded as `bgm:` instead of `bgs:`
- **Cause:** Transactions from `bgs:account` were assigned BGM entity codes
- **Fix:**
```sql
UPDATE acc.bank_staging
SET gl_account_code = REPLACE(gl_account_code, 'bgm:', 'bgs:')
WHERE source_account_code = 'bgs:account'
  AND gl_account_code LIKE 'bgm:%';
```
- **Affected codes:**
  - bgm:draw:fbreen → bgs:draw:fbreen (27 transactions)
  - bgm:proj exp:dining → bgs:proj_exp:dining (18 transactions)
  - bgm:proj exp:gas → bgs:proj_exp:gas (14 transactions)
  - bgm:sub:geode → bgs:sub:geode (5 transactions)
  - And others...

#### Spacing Corrections
- **Issue:** Inconsistent spacing in GL codes (e.g., `proj exp:` vs `proj_exp:`)
- **Fix:** Standardized to underscore format `proj_exp:`
```sql
UPDATE acc.bank_staging
SET gl_account_code = REPLACE(gl_account_code, 'proj exp:', 'proj_exp:')
WHERE gl_account_code LIKE '%proj exp:%';
```

#### Typo Corrections
- **Issue:** `bmg:proj_exp:lodging` instead of `bgs:proj_exp:lodging`
- **Fix:** Manual correction (4 transactions)

### 4. CNH Transactions - Manual Review Required
CNH IND AMERICA credit transactions identified as **client invoice payments**, not equipment purchases:
- IDs: 610, 641, 661, 687
- Total: $31,920.00
- These are A/R collections, not vendor payments
- Flagged for manual review and invoice matching

## Final Results

| Category | Transactions | Amount |
|----------|--------------|--------|
| Personal | 284 | -$54,723.87 |
| Cash/Transfer | 233 | $34,266.40 |
| BGS (Business) | 200 | $35,913.91 |
| Other (USAA/MHB/CSB) | 19 | -$7,968.44 |
| **Total** | **736** | **$7,488.00** |

### Other Category Breakdown
Legitimate separate entities not requiring correction:
- `usaamc:credit` - 9 transactions (-$5,978.11)
- `mhb:maintenance` - 7 transactions (-$629.21)
- `mhb:maintenance:711pine` - 2 transactions (-$131.12)
- `csb:account` - 1 transaction (-$1,230.00)

## Verification Queries

### Check for remaining TODOs
```sql
SELECT COUNT(*) FROM acc.bank_staging WHERE gl_account_code = 'TODO';
```

### Check for entity prefix issues
```sql
SELECT gl_account_code, COUNT(*) 
FROM acc.bank_staging
WHERE source_account_code = 'bgs:account'
  AND gl_account_code LIKE 'bgm:%'
GROUP BY gl_account_code;
```

### Summary by category
```sql
SELECT 
    CASE 
        WHEN gl_account_code LIKE 'bgs:%' THEN 'BGS (Business)'
        WHEN gl_account_code LIKE 'bgm:%' THEN 'BGM (Business)'
        WHEN gl_account_code LIKE 'per:%' THEN 'Personal'
        WHEN gl_account_code LIKE 'cash:%' THEN 'Cash/Transfer'
        ELSE 'Other'
    END as category,
    COUNT(*) as transactions,
    SUM(amount) as total_amount
FROM acc.bank_staging
GROUP BY 1
ORDER BY 2 DESC;
```

## Next Steps
1. Manual review of CNH invoice payments for project code assignment
2. Move categorized transactions from staging to final GL tables
3. Generate P&L and expense reports
4. Review pattern performance for future imports

## Tables Referenced
- `acc.bank_staging` - Transaction staging table
- `acc.vendor_gl_patterns` - Pattern matching rules
- `acc.gl_accounts` - Chart of accounts
