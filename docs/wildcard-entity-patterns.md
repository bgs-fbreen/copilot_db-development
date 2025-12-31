# Wildcard Entity Patterns Feature

## Overview

As of migration 014, the `vendor_gl_patterns` table supports **wildcard patterns** that apply to all entities. This eliminates the need to create duplicate patterns for each entity when a pattern should apply universally.

## How It Works

### Pattern Matching Behavior

When `vendor_gl_patterns.entity IS NULL`, the pattern becomes a **wildcard** that matches transactions from **any entity**.

### Example

#### Pattern Table:
```
| pattern    | entity | gl_account_code |
|------------|--------|-----------------|
| POSHMARK   | NULL   | per:household   |  <- matches ALL entities
| CASEYS     | bgs    | bgs:proj_exp:gas|  <- matches only bgs
```

#### Transaction Matching:
```
| description | entity | Result |
|-------------|--------|--------|
| POSHMARK    | bgs    | ✅ Matches (NULL = wildcard) |
| POSHMARK    | csb    | ✅ Matches (NULL = wildcard) |
| POSHMARK    | mhb    | ✅ Matches (NULL = wildcard) |
| CASEYS #123 | bgs    | ✅ Matches (entity = bgs) |
| CASEYS #123 | csb    | ❌ No match (entity != bgs) |
```

## Usage

### Creating Wildcard Patterns

To create a pattern that applies to all entities, set `entity` to `NULL`:

```sql
-- Wildcard pattern (applies to all entities)
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity, priority)
VALUES ('POSHMARK', 'per:household', NULL, 100);

-- Entity-specific pattern (applies only to bgs)
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity, priority)
VALUES ('CASEYS', 'bgs:proj_exp:gas', 'bgs', 100);
```

### Updating Existing Patterns to Wildcards

To convert existing entity-specific patterns to wildcards:

```sql
-- Update specific patterns
UPDATE acc.vendor_gl_patterns 
SET entity = NULL 
WHERE pattern IN ('POSHMARK', 'DIXIE SALOON', 'JOSES MEXICAN');

-- Update all patterns for a specific GL account
UPDATE acc.vendor_gl_patterns 
SET entity = NULL 
WHERE gl_account_code = 'per:household';
```

### Using with apply-patterns Command

The `apply-patterns` command automatically supports wildcard patterns:

```bash
# Run dry-run to preview matches
copilot allocate apply-patterns --dry-run

# Apply patterns (including wildcards)
copilot allocate apply-patterns

# Filter by entity (still includes wildcard patterns)
copilot allocate apply-patterns --entity bgs
```

## Migration

### Applying the Migration

If you have an existing database, run the migration:

```bash
psql -d copilot_db -f sql/migrations/014_allow_wildcard_entity_patterns.sql
```

### What the Migration Does

1. Makes the `entity` column nullable in `vendor_gl_patterns` table
2. Updates the `fn_apply_fuzzy_matching()` trigger function to support wildcards
3. Updates documentation and comments

## Benefits

### Before Wildcard Support

If you wanted POSHMARK to map to `per:household` for all entities, you needed:

```sql
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity) VALUES 
  ('POSHMARK', 'per:household', 'bgs'),
  ('POSHMARK', 'per:household', 'mhb'),
  ('POSHMARK', 'per:household', 'csb'),
  ('POSHMARK', 'per:household', 'per');
```

### After Wildcard Support

Now you only need one pattern:

```sql
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity) VALUES 
  ('POSHMARK', 'per:household', NULL);
```

## Priority and Specificity

When both wildcard and entity-specific patterns match:
- **Entity-specific patterns take precedence** if they have the same priority
- Higher priority patterns always match first
- Pattern ordering: `priority DESC, id ASC`

### Example Priority Behavior

```sql
-- Two patterns for AMAZON
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity, priority) VALUES 
  ('AMAZON', 'per:household', NULL, 100),        -- Wildcard
  ('AMAZON', 'bgs:proj_exp:supplies', 'bgs', 100); -- Entity-specific

-- Results:
-- bgs transactions matching AMAZON → bgs:proj_exp:supplies (entity-specific wins)
-- csb transactions matching AMAZON → per:household (wildcard matches)
```

To ensure entity-specific patterns always win, give them higher priority:

```sql
-- Entity-specific pattern with higher priority
INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity, priority) VALUES 
  ('AMAZON', 'per:household', NULL, 100),         -- Wildcard (lower priority)
  ('AMAZON', 'bgs:proj_exp:supplies', 'bgs', 200); -- Entity-specific (higher priority)
```

## Technical Details

### Code Changes

The wildcard behavior is implemented in three places:

1. **Trigger Function** (`fn_apply_fuzzy_matching`):
   ```sql
   WHERE (vp.entity IS NULL OR vp.entity = NEW.entity)
   ```

2. **Python `apply_patterns()` function**:
   - Pattern query includes wildcard patterns
   - Transaction matching skips entity filter when pattern entity is NULL

3. **Helper Functions**:
   - `get_recurring_vendors()`
   - `detect_loan_payments()`

### Database Schema

```sql
CREATE TABLE acc.vendor_gl_patterns (
    id SERIAL PRIMARY KEY,
    pattern TEXT NOT NULL,
    pattern_type TEXT,
    gl_account_code VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 100,
    entity VARCHAR(50),  -- NULL = wildcard (applies to all entities)
    category_hint TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_matched_at TIMESTAMP,
    match_count INTEGER DEFAULT 0
);
```

## Troubleshooting

### Pattern Not Matching

If a wildcard pattern isn't matching:

1. Check that `entity` is actually `NULL` (not an empty string):
   ```sql
   SELECT pattern, entity, entity IS NULL as is_wildcard 
   FROM acc.vendor_gl_patterns 
   WHERE pattern = 'POSHMARK';
   ```

2. Verify pattern is active:
   ```sql
   SELECT pattern, is_active 
   FROM acc.vendor_gl_patterns 
   WHERE pattern = 'POSHMARK';
   ```

3. Check description matching:
   ```sql
   SELECT description 
   FROM acc.bank_staging 
   WHERE description ILIKE '%POSHMARK%' 
   AND gl_account_code = 'TODO';
   ```

### Entity-Specific Pattern Not Taking Precedence

Increase the priority of the entity-specific pattern:

```sql
UPDATE acc.vendor_gl_patterns 
SET priority = 200 
WHERE pattern = 'AMAZON' AND entity = 'bgs';
```

## Best Practices

1. **Use wildcards for truly universal patterns**:
   - Personal expenses (POSHMARK, restaurants, etc.)
   - Common utilities that don't vary by entity
   - Recurring payments from the same vendor

2. **Keep entity-specific patterns for business-specific transactions**:
   - Project expenses that vary by entity
   - Entity-specific vendors
   - Different accounting treatment by entity

3. **Use priority to control precedence**:
   - Lower priority (50-100) for wildcards
   - Higher priority (100-200) for entity-specific patterns
   - Very high priority (200+) for exact-match overrides

4. **Document your patterns**:
   ```sql
   INSERT INTO acc.vendor_gl_patterns 
     (pattern, gl_account_code, entity, notes, priority) 
   VALUES 
     ('POSHMARK', 'per:household', NULL, 
      'Universal pattern for Poshmark purchases - applies to all entities', 100);
   ```

## See Also

- [Import and Allocation Wizard Guide](import-and-wizard-guide.md)
- Database schema: `sql/schema/05_bank_staging.sql`
- Migration file: `sql/migrations/014_allow_wildcard_entity_patterns.sql`
