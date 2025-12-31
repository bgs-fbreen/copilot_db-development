"""
Transaction allocation command - Categorize transactions
"""
import click
import os
import re
import calendar
from datetime import date
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, get_connection, execute_command

console = Console()

# Business account entity codes for Step 2 (Business-to-Business Loans)
BUSINESS_ACCOUNTS = {'bgs', 'mhb'}
# Personal and support account entity codes for Steps 3 & 4 (Owner Draws and Contributions)
PERSONAL_ACCOUNTS = {'csb', 'tax', 'medical'}
# Display constants
MAX_DESCRIPTION_LENGTH = 40


def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def format_currency(amount):
    """Format currency amount for display"""
    if amount >= 0:
        return f"${amount:,.2f}"
    else:
        return f"-${abs(amount):,.2f}"


def build_like_condition(pattern_type, pattern):
    """
    Build ILIKE condition and parameter based on pattern type.
    
    Args:
        pattern_type: Type of pattern ('contains', 'startswith', 'exact', or None)
        pattern: Pattern string to match
        
    Returns:
        tuple: (like_condition, like_param) for use in SQL query
    """
    if pattern_type == 'contains' or pattern_type is None:
        return ("bs.description ILIKE %s", f"%{pattern}%")
    elif pattern_type == 'startswith':
        return ("bs.description ILIKE %s", f"{pattern}%")
    elif pattern_type == 'exact':
        return ("bs.description ILIKE %s", pattern)
    else:
        # Default to contains for unknown types
        return ("bs.description ILIKE %s", f"%{pattern}%")


def find_matching_payee_alias(payee):
    """Find matching payee alias based on pattern"""
    if not payee:
        return None
    
    result = execute_query("""
        SELECT 
            pa.id,
            pa.normalized_name,
            pa.default_category_id,
            pa.entity,
            pa.confidence,
            c.name as category_name,
            c.code as category_code
        FROM acc.payee_alias pa
        LEFT JOIN acc.category c ON c.id = pa.default_category_id
        WHERE LOWER(%s) LIKE LOWER(pa.payee_pattern)
        ORDER BY pa.confidence DESC, LENGTH(pa.payee_pattern) DESC
        LIMIT 1
    """, (payee,))
    
    return result[0] if result else None


def lookup_account_by_number(account_number):
    """
    Lookup bank account by account_number field.
    
    Args:
        account_number: Account number string to search for
        
    Returns:
        Dictionary with 'entity', 'code', and 'type' fields, or None if not found
    """
    result = execute_query("""
        SELECT 
            entity,
            code,
            account_type as type
        FROM acc.bank_account
        WHERE account_number = %s
        LIMIT 1
    """, (account_number,))
    
    return result[0] if result else None


def detect_transfer_gl_code(description, source_entity):
    """
    Parse account number from description, lookup target entity,
    and return appropriate GL code.
    
    Args:
        description: Transaction description string
        source_entity: Entity code where the transaction originated
        
    Returns:
        GL code string or None if transfer cannot be detected
    """
    # 1. Detect direction
    desc_upper = description.upper()
    if 'TRANSFER TO' in desc_upper or 'TRF TO' in desc_upper:
        direction = 'outgoing'
    elif 'TRANSFER FR' in desc_upper or 'TRF FR' in desc_upper:
        direction = 'incoming'
    else:
        return None
    
    # 2. Extract account number
    # Try mortgage pattern first
    mortgage_match = re.search(r'LOAN ACCT\s*0*(\d+)\s*NOTE NO\s*0*(\d+)', desc_upper)
    if mortgage_match:
        account_num = f"{mortgage_match.group(1)}-{mortgage_match.group(2)}"
    else:
        # Try checking account pattern
        checking_match = re.search(r'ACC\s*0*(\d+)', desc_upper)
        if checking_match:
            account_num = checking_match.group(1)
        else:
            return None
    
    # 3. Lookup account in database
    target_account = lookup_account_by_number(account_num)
    if not target_account:
        return None
    
    target_entity = target_account['entity']
    target_code = target_account['code']
    
    # 4. Determine GL code based on entities and direction
    if 'mortgage' in target_code.lower():
        # Extract property name from code (e.g., mhb:mortgage:711pine -> 711pine)
        property_name = target_code.split(':')[-1]
        return f"mortgage:{property_name}"
    
    if direction == 'outgoing':
        if source_entity in BUSINESS_ACCOUNTS and target_entity in BUSINESS_ACCOUNTS:
            return f"loan:{source_entity}-to-{target_entity}"
        elif source_entity in BUSINESS_ACCOUNTS and target_entity in PERSONAL_ACCOUNTS:
            return "draw:fbreen"
        elif source_entity in PERSONAL_ACCOUNTS and target_entity in BUSINESS_ACCOUNTS:
            return "contrib:fbreen"
    else:  # incoming
        if source_entity in BUSINESS_ACCOUNTS and target_entity in BUSINESS_ACCOUNTS:
            return f"loan:{target_entity}-to-{source_entity}"
        elif source_entity in PERSONAL_ACCOUNTS and target_entity in BUSINESS_ACCOUNTS:
            return "draw:fbreen"
        elif source_entity in BUSINESS_ACCOUNTS and target_entity in PERSONAL_ACCOUNTS:
            return "contrib:fbreen"
    
    return None


@click.group()
def allocate():
    """Allocate and categorize transactions"""
    pass


@allocate.command('interactive')
@click.option('--account', '-a', help='Filter by account code')
@click.option('--limit', '-l', default=20, help='Number of transactions to process')
def allocate_interactive(account, limit):
    """Interactively allocate transactions"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Interactive Transaction Allocation[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Get uncategorized transactions
    if account:
        query = """
            SELECT * FROM acc.vw_uncategorized
            WHERE account_code = %s
            ORDER BY trans_date DESC
            LIMIT %s
        """
        transactions = execute_query(query, (account, limit))
    else:
        query = """
            SELECT * FROM acc.vw_uncategorized
            ORDER BY trans_date DESC
            LIMIT %s
        """
        transactions = execute_query(query, (limit,))
    
    if not transactions:
        console.print("[green]All transactions are categorized![/green]\n")
        return
    
    console.print(f"[bold]Found {len(transactions)} uncategorized transactions[/bold]\n")
    
    # Get available categories
    categories = execute_query("""
        SELECT id, code, name, account_type, entity
        FROM acc.category
        WHERE status = 'active'
        ORDER BY code
    """)
    
    category_map = {cat['code']: cat for cat in categories}
    
    # Process each transaction
    for i, trans in enumerate(transactions, 1):
        clear_screen()
        console.print(f"\n[bold cyan]Transaction {i} of {len(transactions)}[/bold cyan]\n")
        
        # Display transaction details
        table = Table(show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("ID", str(trans['id']))
        table.add_row("Account", trans['account_code'])
        table.add_row("Date", trans['trans_date'].strftime('%Y-%m-%d'))
        table.add_row("Payee", trans['payee'] or '')
        table.add_row("Memo", trans['memo'] or '')
        
        amount_str = f"${trans['amount']:,.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):,.2f}"
        table.add_row("Amount", amount_str)
        
        console.print(table)
        console.print()
        
        # Check for payee alias match
        alias_match = find_matching_payee_alias(trans['payee'])
        if alias_match:
            console.print("[bold green]Suggested Categorization:[/bold green]")
            console.print(f"  Category: {alias_match['category_code']} - {alias_match['category_name']}")
            console.print(f"  Entity: {alias_match['entity'] or 'None'}")
            console.print(f"  Confidence: {alias_match['confidence']}%")
            console.print()
            
            if Confirm.ask("Use suggested categorization?", default=True):
                category_code = alias_match['category_code']
                entity = alias_match['entity']
            else:
                category_code = None
                entity = None
        else:
            console.print("[yellow]No matching payee alias found[/yellow]\n")
            category_code = None
            entity = None
        
        # Manual categorization
        if not category_code:
            console.print("[bold]Available Categories:[/bold]")
            console.print("[dim]Enter category code, or 's' to skip, 'q' to quit[/dim]\n")
            
            # Show common categories
            common_cats = [cat for cat in categories[:15]]
            cat_table = Table(show_header=True, header_style="bold magenta")
            cat_table.add_column("Code", style="cyan")
            cat_table.add_column("Name", style="white")
            cat_table.add_column("Type", style="yellow")
            
            for cat in common_cats:
                cat_table.add_row(cat['code'], cat['name'], cat['account_type'])
            
            console.print(cat_table)
            console.print()
            
            category_code = Prompt.ask("Category code", default="s")
            
            if category_code.lower() == 'q':
                console.print("\n[yellow]Allocation cancelled[/yellow]\n")
                return
            elif category_code.lower() == 's':
                console.print("[yellow]Skipped[/yellow]")
                continue
            
            if category_code not in category_map:
                console.print(f"[red]Invalid category code: {category_code}[/red]")
                if not Confirm.ask("Skip this transaction?", default=True):
                    continue
                continue
        
        # Get additional details
        console.print()
        entity = Prompt.ask("Entity (BGS/MHB or blank)", default=entity or "")
        project_code = Prompt.ask("Project code (optional)", default="")
        property_code = Prompt.ask("Property code (optional)", default="")
        notes = Prompt.ask("Notes (optional)", default="")
        
        # Confirm allocation
        console.print("\n[bold yellow]Confirm Allocation:[/bold yellow]")
        console.print(f"  Category: {category_code}")
        if entity:
            console.print(f"  Entity: {entity}")
        if project_code:
            console.print(f"  Project: {project_code}")
        if property_code:
            console.print(f"  Property: {property_code}")
        console.print()
        
        if not Confirm.ask("Save allocation?", default=True):
            console.print("[yellow]Skipped[/yellow]")
            continue
        
        # Update transaction
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE acc.transaction
                    SET 
                        category_id = (SELECT id FROM acc.category WHERE code = %s),
                        entity = NULLIF(%s, ''),
                        project_code = NULLIF(%s, ''),
                        property_code = NULLIF(%s, ''),
                        notes = CASE 
                            WHEN %s != '' THEN COALESCE(notes || E'\n', '') || %s
                            ELSE notes
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (category_code, entity, project_code, property_code, 
                      notes, notes, trans['id']))
                conn.commit()
                console.print("[bold green]✓ Transaction allocated![/bold green]")
        except Exception as e:
            conn.rollback()
            console.print(f"[red]Error allocating transaction: {e}[/red]")
        finally:
            conn.close()
        
        # Wait for user to continue
        if i < len(transactions):
            input("\nPress Enter to continue...")
    
    console.print("\n[bold green]✓ Allocation complete![/bold green]\n")


@allocate.command('auto')
@click.option('--account', '-a', help='Filter by account code')
@click.option('--min-confidence', default=80, help='Minimum confidence percentage (default: 80)')
@click.option('--dry-run', is_flag=True, help='Preview without saving')
def allocate_auto(account, min_confidence, dry_run):
    """Automatically allocate transactions using payee aliases"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Auto-Allocation using Payee Aliases[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"[bold]Minimum confidence:[/bold] {min_confidence}%\n")
    
    # Get uncategorized transactions
    if account:
        query = """
            SELECT * FROM acc.vw_uncategorized
            WHERE account_code = %s
            ORDER BY trans_date DESC
        """
        transactions = execute_query(query, (account,))
    else:
        query = """
            SELECT * FROM acc.vw_uncategorized
            ORDER BY trans_date DESC
        """
        transactions = execute_query(query)
    
    if not transactions:
        console.print("[green]All transactions are categorized![/green]\n")
        return
    
    console.print(f"[bold]Found {len(transactions)} uncategorized transactions[/bold]\n")
    
    # Try to match each transaction
    matched = []
    unmatched = []
    
    for trans in transactions:
        alias_match = find_matching_payee_alias(trans['payee'])
        
        if alias_match and alias_match['confidence'] >= min_confidence:
            matched.append({
                'trans': trans,
                'alias': alias_match
            })
        else:
            unmatched.append(trans)
    
    console.print(f"[bold]Matched:[/bold] [green]{len(matched)}[/green]")
    console.print(f"[bold]Unmatched:[/bold] [yellow]{len(unmatched)}[/yellow]\n")
    
    if not matched:
        console.print("[yellow]No transactions matched with sufficient confidence[/yellow]\n")
        return
    
    # Show preview of matches
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Payee", style="white")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Confidence", justify="right")
    
    for match in matched[:20]:  # Show first 20
        trans = match['trans']
        alias = match['alias']
        
        amount_str = f"${trans['amount']:,.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):,.2f}"
        table.add_row(
            trans['trans_date'].strftime('%Y-%m-%d'),
            (trans['payee'] or '')[:30],
            amount_str,
            f"{alias['category_code']}",
            f"{alias['confidence']}%"
        )
    
    if len(matched) > 20:
        table.add_row("[dim]...", "[dim]...", "[dim]...", "[dim]...", f"[dim]{len(matched) - 20} more...")
    
    console.print(table)
    console.print()
    
    if dry_run:
        console.print("[yellow]Dry run - no changes made[/yellow]\n")
        return
    
    # Confirm allocation
    if not Confirm.ask(f"Allocate {len(matched)} transactions?", default=True):
        console.print("[yellow]Auto-allocation cancelled[/yellow]\n")
        return
    
    # Allocate transactions
    conn = get_connection()
    allocated_count = 0
    
    try:
        with conn.cursor() as cur:
            for match in matched:
                trans = match['trans']
                alias = match['alias']
                
                cur.execute("""
                    UPDATE acc.transaction
                    SET 
                        category_id = %s,
                        entity = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (alias['default_category_id'], alias['entity'], trans['id']))
                
                allocated_count += 1
            
            conn.commit()
            console.print(f"\n[bold green]✓ Successfully allocated {allocated_count} transactions![/bold green]\n")
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error allocating transactions: {e}[/red]")
    finally:
        conn.close()


@allocate.command('list')
@click.option('--account', '-a', help='Filter by account code')
@click.option('--category', '-c', help='Filter by category code')
@click.option('--entity', '-e', help='Filter by entity')
@click.option('--month', '-m', help='Filter by month (YYYY-MM)')
def allocate_list(account, category, entity, month):
    """List allocated transactions with summary"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Allocation Summary[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Build WHERE clause
    where_clauses = ["t.category_id IS NOT NULL"]
    params = []
    
    if account:
        where_clauses.append("t.account_code = %s")
        params.append(account)
    
    if category:
        where_clauses.append("c.code = %s")
        params.append(category)
    
    if entity:
        where_clauses.append("t.entity = %s")
        params.append(entity)
    
    if month:
        # Validate month format
        import re
        if not re.match(r'^\d{4}-\d{2}$', month):
            console.print("[red]Invalid month format. Use YYYY-MM (e.g., 2024-01)[/red]\n")
            return
        where_clauses.append("DATE_TRUNC('month', t.trans_date) = %s::date")
        params.append(f"{month}-01")
    
    where_clause = "WHERE " + " AND ".join(where_clauses)
    
    # Get allocated transactions
    query = f"""
        SELECT 
            t.id,
            t.account_code,
            t.trans_date,
            t.payee,
            t.amount,
            t.entity,
            c.code as category_code,
            c.name as category_name
        FROM acc.transaction t
        LEFT JOIN acc.category c ON c.id = t.category_id
        {where_clause}
        ORDER BY t.trans_date DESC
        LIMIT 100
    """
    transactions = execute_query(query, tuple(params) if params else None)
    
    if not transactions:
        console.print("[yellow]No allocated transactions found[/yellow]\n")
        return
    
    # Show summary statistics
    total_count = len(transactions)
    total_amount = sum(float(t['amount']) for t in transactions)
    income = sum(float(t['amount']) for t in transactions if t['amount'] > 0)
    expenses = sum(abs(float(t['amount'])) for t in transactions if t['amount'] < 0)
    
    console.print(f"[bold]Total Transactions:[/bold] {total_count}")
    console.print(f"[bold]Total Income:[/bold] [green]${income:,.2f}[/green]")
    console.print(f"[bold]Total Expenses:[/bold] [red]${expenses:,.2f}[/red]")
    console.print(f"[bold]Net:[/bold] ${total_amount:,.2f}\n")
    
    # Group by category
    by_category = {}
    for trans in transactions:
        cat_code = trans['category_code']
        if cat_code not in by_category:
            by_category[cat_code] = {
                'name': trans['category_name'],
                'count': 0,
                'amount': 0
            }
        by_category[cat_code]['count'] += 1
        by_category[cat_code]['amount'] += float(trans['amount'])
    
    # Show category summary
    console.print("[bold]Summary by Category:[/bold]\n")
    
    cat_table = Table(show_header=True, header_style="bold magenta")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Name", style="white")
    cat_table.add_column("Count", justify="right")
    cat_table.add_column("Amount", justify="right", style="green")
    
    for cat_code, data in sorted(by_category.items(), key=lambda x: abs(x[1]['amount']), reverse=True):
        amount_str = f"${data['amount']:,.2f}" if data['amount'] >= 0 else f"-${abs(data['amount']):,.2f}"
        cat_table.add_row(
            cat_code,
            data['name'][:40],
            str(data['count']),
            amount_str
        )
    
    console.print(cat_table)
    console.print()
    
    # Show recent transactions
    console.print("[bold]Recent Transactions:[/bold]\n")
    
    trans_table = Table(show_header=True, header_style="bold magenta")
    trans_table.add_column("Date", style="cyan")
    trans_table.add_column("Payee", style="white")
    trans_table.add_column("Category", style="yellow")
    trans_table.add_column("Entity", style="white")
    trans_table.add_column("Amount", justify="right", style="green")
    
    for trans in transactions[:20]:  # Show first 20
        amount_str = f"${trans['amount']:,.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):,.2f}"
        trans_table.add_row(
            trans['trans_date'].strftime('%Y-%m-%d'),
            (trans['payee'] or '')[:30],
            trans['category_code'],
            trans['entity'] or '',
            amount_str
        )
    
    if len(transactions) > 20:
        console.print(trans_table)
        console.print(f"[dim]... and {len(transactions) - 20} more[/dim]\n")
    else:
        console.print(trans_table)
        console.print()


# ============================================================================
# Wizard Helper Functions
# ============================================================================

def parse_period(period):
    """
    Parse period string into date range.
    Formats: '2024', '2024-Q1', '2024-01'
    Returns: (start_date, end_date)
    """
    if len(period) == 4:  # Year: 2024
        year = int(period)
        return date(year, 1, 1), date(year, 12, 31)
    elif '-Q' in period:  # Quarter: 2024-Q1
        year = int(period[:4])
        quarter = int(period[-1])
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        return date(year, start_month, 1), date(year, end_month, calendar.monthrange(year, end_month)[1])
    elif len(period) == 7:  # Month: 2024-01
        year, month = int(period[:4]), int(period[5:7])
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    else:
        raise ValueError(f"Invalid period format: {period}. Use YYYY, YYYY-QN, or YYYY-MM")


def get_import_status(entity, start_date, end_date, period):
    """Get import status for accounts. If entity is None, return all entities."""
    
    base_query = """
        SELECT 
            ba.entity,
            ba.code as account,
            ba.name as account_name,
            COUNT(bs.id) as record_count,
            MIN(bs.normalized_date) as min_date,
            MAX(bs.normalized_date) as max_date,
            was.status as wizard_status,
            was.reason as skip_reason
        FROM acc.bank_account ba
        LEFT JOIN acc.bank_staging bs 
            ON bs.source_account_code = ba.code
            AND bs.normalized_date BETWEEN %s AND %s
        LEFT JOIN acc.wizard_account_status was
            ON was.account_code = ba.code
            AND was.period = %s
    """
    
    params = [start_date, end_date, period]
    
    if entity:
        base_query += " WHERE ba.entity = %s"
        params.append(entity)
    else:
        # Exclude accounts with NULL entity
        base_query += " WHERE ba.entity IS NOT NULL"
    
    base_query += """
        GROUP BY ba.entity, ba.code, ba.name, was.status, was.reason
        ORDER BY ba.entity, ba.code
    """
    
    return execute_query(base_query, tuple(params))


def skip_account(account_code, entity, period, reason=None):
    """Mark an account as skipped for a period"""
    query = """
        INSERT INTO acc.wizard_account_status (account_code, entity, period, status, reason)
        VALUES (%s, %s, %s, 'skipped', %s)
        ON CONFLICT (account_code, entity, period) 
        DO UPDATE SET status = 'skipped', reason = %s, updated_at = CURRENT_TIMESTAMP
    """
    execute_command(query, (account_code, entity, period, reason, reason))


def unskip_account(account_code, entity, period):
    """Remove skipped status for an account"""
    query = """
        DELETE FROM acc.wizard_account_status 
        WHERE account_code = %s AND entity = %s AND period = %s
    """
    execute_command(query, (account_code, entity, period))


def get_skipped_accounts(entity, period):
    """Get list of skipped accounts for entity/period"""
    query = """
        SELECT account_code, reason, created_at
        FROM acc.wizard_account_status
        WHERE entity = %s AND period = %s AND status = 'skipped'
    """
    return execute_query(query, (entity, period))


def get_entity_type_map():
    """Get entity type mapping from database.
    Returns dict mapping entity codes to entity types (business, personal, support).
    If acc.entity table doesn't exist (migration 012 not run), returns empty dict."""
    entity_type_map = {}
    try:
        entity_types = execute_query("""
            SELECT code, entity_type FROM acc.entity
        """)
        entity_type_map = {e['code']: e['entity_type'] for e in entity_types}
    except Exception:
        # Migration 012 not run yet - use default behavior
        pass
    return entity_type_map


def detect_intercompany_transfers(entity, start_date, end_date, active_accounts=None):
    """Find Business-to-Business transfers only - matching amounts on same date, opposite signs.
    This is used for Step 2 (Business-to-Business Loans).
    
    Only includes transfers where BOTH entities are in BUSINESS_ACCOUNTS (bgs, mhb).
    
    If entity is None, find transfers across ALL business entities.
    Returns: (transfers_list, entity_type_map)
    Note: entity_type_map is returned for use by downstream classify_transfer() function."""
    
    # Get entity types from database
    entity_type_map = get_entity_type_map()
    
    # Query for cross-entity transfers (different entities)
    cross_entity_query = """
        SELECT 
            a.id as from_id,
            a.normalized_date,
            a.entity as from_entity,
            a.source_account_code as from_account,
            a.description as from_desc,
            a.amount as from_amount,
            b.id as to_id,
            b.entity as to_entity,
            b.source_account_code as to_account,
            b.description as to_desc,
            b.amount as to_amount
        FROM acc.bank_staging a
        JOIN acc.bank_staging b 
            ON a.normalized_date = b.normalized_date
            AND a.amount = -b.amount
            AND a.entity != b.entity
            AND a.id < b.id
        WHERE a.amount < 0
          AND a.normalized_date BETWEEN %s AND %s
          AND a.gl_account_code = 'TODO'
          AND b.gl_account_code = 'TODO'
    """
    
    params = [start_date, end_date]
    
    # If specific entity, filter to transfers involving that entity
    entity_filter = ""
    entity_params = []
    if entity:
        entity_filter = " AND (a.entity = %s OR b.entity = %s)"
        entity_params = [entity, entity]
    
    # Filter by active accounts if provided
    # Note: active_accounts list comes from trusted database query results
    account_filter = ""
    account_params = []
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        account_filter = f" AND (a.source_account_code IN ({placeholders}) OR b.source_account_code IN ({placeholders}))"
        account_params = active_accounts + active_accounts
    
    # Execute query
    all_params = params + entity_params + account_params
    
    cross_entity_results = execute_query(
        cross_entity_query + entity_filter + account_filter + " ORDER BY a.normalized_date",
        tuple(all_params)
    )
    
    # Filter to only Business → Business transfers
    business_to_business = []
    for row in cross_entity_results or []:
        from_entity = row['from_entity']
        to_entity = row['to_entity']
        
        # Only include if BOTH entities are business accounts
        # Exclude mortgage destinations (those are handled in Step 5)
        to_account_lower = row['to_account'].lower()
        if from_entity in BUSINESS_ACCOUNTS and to_entity in BUSINESS_ACCOUNTS and 'mortgage:' not in to_account_lower:
            business_to_business.append(row)
    
    return business_to_business, entity_type_map


def detect_loan_payments(entity, start_date, end_date, active_accounts=None):
    """Find potential loan payments. If entity is None, search all entities."""
    
    base_query = """
        SELECT 
            bs.id,
            bs.entity,
            bs.normalized_date,
            bs.source_account_code,
            bs.description,
            bs.amount,
            vp.gl_account_code as suggested_code
        FROM acc.bank_staging bs
        LEFT JOIN acc.vendor_gl_patterns vp 
            ON bs.description ILIKE '%%' || vp.pattern || '%%'
            AND (vp.entity IS NULL OR vp.entity = bs.entity)
            AND vp.gl_account_code LIKE 'loan:%%'
        WHERE bs.normalized_date BETWEEN %s AND %s
          AND bs.gl_account_code = 'TODO'
          AND (
              bs.description ILIKE '%%MORTGAGE%%'
              OR bs.description ILIKE '%%LOAN%%'
              OR vp.gl_account_code IS NOT NULL
          )
    """
    
    params = [start_date, end_date]
    
    if entity:
        base_query += " AND bs.entity = %s"
        params.append(entity)
    
    # Filter by active accounts if provided
    # Note: active_accounts list comes from trusted database query results
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        base_query += f" AND bs.source_account_code IN ({placeholders})"
        params.extend(active_accounts)
    
    base_query += " ORDER BY bs.entity, bs.normalized_date"
    
    return execute_query(base_query, tuple(params))


def get_recurring_vendors(entity, start_date, end_date, min_count=5, active_accounts=None):
    """Find vendors with 5+ transactions. If entity is None, search all entities."""
    
    base_query = """
        SELECT 
            bs.entity,
            bs.description,
            COUNT(*) as cnt,
            SUM(bs.amount) as total,
            vp.gl_account_code as suggested_code
        FROM acc.bank_staging bs
        LEFT JOIN acc.vendor_gl_patterns vp 
            ON bs.description ILIKE '%%' || vp.pattern || '%%'
            AND (vp.entity IS NULL OR vp.entity = bs.entity)
        WHERE bs.normalized_date BETWEEN %s AND %s
          AND bs.gl_account_code = 'TODO'
    """
    
    params = [start_date, end_date]
    
    if entity:
        base_query += " AND bs.entity = %s"
        params.append(entity)
    
    # Filter by active accounts if provided
    # Note: active_accounts list comes from trusted database query results
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        base_query += f" AND bs.source_account_code IN ({placeholders})"
        params.extend(active_accounts)
    
    base_query += """
        GROUP BY bs.entity, bs.description, vp.gl_account_code
        HAVING COUNT(*) >= %s
        ORDER BY COUNT(*) DESC
    """
    params.append(min_count)
    
    return execute_query(base_query, tuple(params))


def get_allocation_progress(entity, start_date, end_date):
    """Get allocation progress. If entity is None, get progress for all entities."""
    
    base_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE gl_account_code != 'TODO') as allocated,
            COUNT(*) FILTER (WHERE gl_account_code = 'TODO') as remaining
        FROM acc.bank_staging
        WHERE normalized_date BETWEEN %s AND %s
    """
    
    params = [start_date, end_date]
    
    if entity:
        base_query += " AND entity = %s"
        params.append(entity)
    
    results = execute_query(base_query, tuple(params))
    return results[0] if results else {'total': 0, 'allocated': 0, 'remaining': 0}


def classify_transfer(from_entity, to_entity, from_account, to_account, entity_type_map):
    """
    Classify a transfer and return the appropriate GL code.
    
    Detection Priority:
    1. Mortgage account destination → mortgage:{property}
    2. Business → Business → loan:{from}-to-{to}
    3. Business → Personal/Support → draw:fbreen
    4. Personal/Support → Business → contrib:fbreen
    5. Same Entity (non-mortgage) → transfer:{entity}
    
    Args:
        from_entity: Source entity code
        to_entity: Destination entity code
        from_account: Source account code
        to_account: Destination account code
        entity_type_map: Dictionary mapping entity codes to entity types
    
    Returns:
        GL code string (e.g., 'mortgage:711pine', 'loan:bgs-to-mhb', 'draw:fbreen')
    """
    # Priority 1: Mortgage account destination
    # Check if destination account contains "mortgage:"
    # Expected format: entity:mortgage:property (e.g., mhb:mortgage:711pine)
    to_account_lower = to_account.lower()
    if 'mortgage:' in to_account_lower:
        # Extract property name from account code
        parts = to_account.split(':')
        # Ensure we have at least 3 parts: entity, mortgage, property
        # Use lowercased version for comparison to ensure case-insensitive matching
        if len(parts) >= 3 and parts[1].lower() == 'mortgage':
            # Take the third part as property name (ignoring any additional parts)
            property_name = parts[2]
            return f"mortgage:{property_name}"
    
    # Priority 5: Same entity transfer (non-mortgage)
    if from_entity == to_entity:
        return f"transfer:{from_entity}"
    
    # Get entity types (default to 'business' if not found for backward compatibility)
    from_type = entity_type_map.get(from_entity, 'business')
    to_type = entity_type_map.get(to_entity, 'business')
    
    # Priority 2: Business → Business (related party loan)
    if from_type == 'business' and to_type == 'business':
        return f"loan:{from_entity}-to-{to_entity}"
    
    # Priority 3: Business → Personal/Support (owner draw)
    if from_type == 'business' and to_type in ('personal', 'support'):
        return "draw:fbreen"
    
    # Priority 4: Personal/Support → Business (owner contribution)
    if from_type in ('personal', 'support') and to_type == 'business':
        return "contrib:fbreen"
    
    # Fallback: treat as loan (should not happen with proper entity types)
    return f"loan:{from_entity}-to-{to_entity}"


def assign_intercompany(from_id, to_id, from_entity, to_entity, from_account, to_account, entity_type_map):
    """Assign transfer GL codes to both sides of transfer based on classification"""
    # Classify the transfer to get the appropriate GL code
    gl_code = classify_transfer(from_entity, to_entity, from_account, to_account, entity_type_map)
    
    # Determine match_method based on GL code type
    if gl_code.startswith('mortgage:'):
        match_method = 'mortgage'
    elif gl_code.startswith('loan:'):
        match_method = 'loan'
    elif gl_code.startswith('draw:'):
        match_method = 'draw'
    elif gl_code.startswith('contrib:'):
        match_method = 'contribution'
    elif gl_code.startswith('transfer:'):
        match_method = 'transfer'
    else:
        match_method = 'transfer'
    
    # Update both transactions
    update_query = """
        UPDATE acc.bank_staging
        SET gl_account_code = %s,
            match_method = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN (%s, %s)
    """
    execute_command(update_query, (gl_code, match_method, from_id, to_id))


def detect_owner_draws(entity, start_date, end_date, active_accounts, entity_type_map):
    """Find owner draws: Business → Personal/Support transfers.
    If entity is None, find draws from all business entities.
    
    Args:
        entity: Entity code to filter by (or None for all)
        start_date: Start of date range
        end_date: End of date range
        active_accounts: List of active account codes
        entity_type_map: Dict mapping entity codes to entity types
        
    Returns: List of owner draw transactions"""
    
    # Query for Business → Personal/Support transfers
    query = """
        SELECT 
            a.id as from_id,
            a.normalized_date,
            a.entity as from_entity,
            a.source_account_code as from_account,
            a.description as from_desc,
            a.amount as from_amount,
            b.id as to_id,
            b.entity as to_entity,
            b.source_account_code as to_account,
            b.description as to_desc,
            b.amount as to_amount
        FROM acc.bank_staging a
        JOIN acc.bank_staging b 
            ON a.normalized_date = b.normalized_date
            AND a.amount = -b.amount
            AND a.entity != b.entity
            AND a.id < b.id
        WHERE a.amount < 0
          AND a.normalized_date BETWEEN %s AND %s
          AND a.gl_account_code = 'TODO'
          AND b.gl_account_code = 'TODO'
    """
    
    params = [start_date, end_date]
    
    # If specific entity, filter to transfers from that entity
    entity_filter = ""
    entity_params = []
    if entity:
        entity_filter = " AND a.entity = %s"
        entity_params = [entity]
    
    # Filter by active accounts if provided
    account_filter = ""
    account_params = []
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        account_filter = f" AND (a.source_account_code IN ({placeholders}) OR b.source_account_code IN ({placeholders}))"
        account_params = active_accounts + active_accounts
    
    all_params = params + entity_params + account_params
    
    results = execute_query(
        query + entity_filter + account_filter + " ORDER BY a.normalized_date",
        tuple(all_params)
    )
    
    # Filter to only Business → Personal/Support transfers
    owner_draws = []
    for row in results or []:
        from_entity = row['from_entity']
        to_entity = row['to_entity']
        
        # Check for Business → Personal/Support
        if from_entity in BUSINESS_ACCOUNTS and to_entity in PERSONAL_ACCOUNTS:
            owner_draws.append(row)
    
    return owner_draws


def detect_owner_contributions(entity, start_date, end_date, active_accounts, entity_type_map):
    """Find owner contributions: Personal/Support → Business transfers.
    If entity is None, find contributions to all business entities.
    
    Args:
        entity: Entity code to filter by (or None for all)
        start_date: Start of date range
        end_date: End of date range
        active_accounts: List of active account codes
        entity_type_map: Dict mapping entity codes to entity types
        
    Returns: List of owner contribution transactions"""
    
    # Query for Personal/Support → Business transfers
    query = """
        SELECT 
            a.id as from_id,
            a.normalized_date,
            a.entity as from_entity,
            a.source_account_code as from_account,
            a.description as from_desc,
            a.amount as from_amount,
            b.id as to_id,
            b.entity as to_entity,
            b.source_account_code as to_account,
            b.description as to_desc,
            b.amount as to_amount
        FROM acc.bank_staging a
        JOIN acc.bank_staging b 
            ON a.normalized_date = b.normalized_date
            AND a.amount = -b.amount
            AND a.entity != b.entity
            AND a.id < b.id
        WHERE a.amount < 0
          AND a.normalized_date BETWEEN %s AND %s
          AND a.gl_account_code = 'TODO'
          AND b.gl_account_code = 'TODO'
    """
    
    params = [start_date, end_date]
    
    # If specific entity, filter to transfers to that entity
    entity_filter = ""
    entity_params = []
    if entity:
        entity_filter = " AND b.entity = %s"
        entity_params = [entity]
    
    # Filter by active accounts if provided
    account_filter = ""
    account_params = []
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        account_filter = f" AND (a.source_account_code IN ({placeholders}) OR b.source_account_code IN ({placeholders}))"
        account_params = active_accounts + active_accounts
    
    all_params = params + entity_params + account_params
    
    results = execute_query(
        query + entity_filter + account_filter + " ORDER BY a.normalized_date",
        tuple(all_params)
    )
    
    # Filter to only Personal/Support → Business transfers
    owner_contributions = []
    for row in results or []:
        from_entity = row['from_entity']
        to_entity = row['to_entity']
        
        # Check for Personal/Support → Business
        if from_entity in PERSONAL_ACCOUNTS and to_entity in BUSINESS_ACCOUNTS:
            owner_contributions.append(row)
    
    return owner_contributions


def detect_mortgage_payments(entity, start_date, end_date, active_accounts=None):
    """Find mortgage payments: Any account → mortgage account transfers.
    If entity is None, find mortgage payments from all entities."""
    
    # Query for transfers TO accounts containing 'mortgage:'
    query = """
        SELECT 
            a.id as from_id,
            a.normalized_date,
            a.entity as from_entity,
            a.source_account_code as from_account,
            a.description as from_desc,
            a.amount as from_amount,
            b.id as to_id,
            b.entity as to_entity,
            b.source_account_code as to_account,
            b.description as to_desc,
            b.amount as to_amount
        FROM acc.bank_staging a
        JOIN acc.bank_staging b 
            ON a.normalized_date = b.normalized_date
            AND a.amount = -b.amount
            AND a.id < b.id
        WHERE a.amount < 0
          AND a.normalized_date BETWEEN %s AND %s
          AND a.gl_account_code = 'TODO'
          AND b.gl_account_code = 'TODO'
          AND LOWER(b.source_account_code) LIKE '%%mortgage:%%'
    """
    
    params = [start_date, end_date]
    
    # If specific entity, filter to transfers from that entity
    if entity:
        query += " AND a.entity = %s"
        params.append(entity)
    
    # Filter by active accounts if provided (must be non-empty list)
    if active_accounts and len(active_accounts) > 0:
        placeholders = ','.join(['%s'] * len(active_accounts))
        query += f" AND (a.source_account_code IN ({placeholders}) OR b.source_account_code IN ({placeholders}))"
        params.extend(active_accounts)
        params.extend(active_accounts)
    
    query += " ORDER BY a.normalized_date"
    
    results = execute_query(query, tuple(params))
    
    return results or []


def get_entity_expenses(entity_code, start_date, end_date, active_accounts=None):
    """Get unallocated expenses for a specific entity.
    Returns transactions that need GL code assignment."""
    
    query = """
        SELECT 
            id,
            entity,
            normalized_date,
            source_account_code,
            description,
            amount
        FROM acc.bank_staging
        WHERE entity = %s
          AND normalized_date BETWEEN %s AND %s
          AND gl_account_code = 'TODO'
    """
    
    params = [entity_code, start_date, end_date]
    
    # Filter by active accounts if provided
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        query += f" AND source_account_code IN ({placeholders})"
        params.extend(active_accounts)
    
    query += " ORDER BY normalized_date DESC"
    
    return execute_query(query, tuple(params))


def detect_and_assign_single_transfers(entity, start_date, end_date, active_accounts=None):
    """
    Detect and auto-assign single-sided transfers using smart transfer detection.
    Returns count of transactions assigned.
    
    This catches transfers where only one side is visible (no matching opposite transaction).
    """
    # Get all TODO transactions for the entity
    query = """
        SELECT 
            id,
            entity,
            description
        FROM acc.bank_staging
        WHERE normalized_date BETWEEN %s AND %s
          AND gl_account_code = 'TODO'
    """
    
    params = [start_date, end_date]
    
    if entity:
        query += " AND entity = %s"
        params.append(entity)
    
    # Filter by active accounts if provided
    if active_accounts:
        placeholders = ','.join(['%s'] * len(active_accounts))
        query += f" AND source_account_code IN ({placeholders})"
        params.extend(active_accounts)
    
    transactions = execute_query(query, tuple(params))
    
    if not transactions:
        return 0
    
    # Try to detect and assign transfers
    assigned_count = 0
    
    for trans in transactions:
        gl_code = detect_transfer_gl_code(trans['description'], trans['entity'])
        if gl_code:
            # Determine match_method based on GL code
            if gl_code.startswith('mortgage:'):
                match_method = 'mortgage'
            elif gl_code.startswith('loan:'):
                match_method = 'loan'
            elif gl_code.startswith('draw:'):
                match_method = 'draw'
            elif gl_code.startswith('contrib:'):
                match_method = 'contribution'
            else:
                match_method = 'transfer'
            
            # Update the transaction
            update_query = """
                UPDATE acc.bank_staging
                SET gl_account_code = %s,
                    match_method = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            execute_command(update_query, (gl_code, match_method, trans['id']))
            assigned_count += 1
    
    return assigned_count


def display_progress_bar(allocated, total, width=20):
    """Display ASCII progress bar"""
    if total == 0:
        return "░" * width + " 0%"
    pct = allocated / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {pct*100:.0f}%"


class WizardState:
    """Track wizard progress and statistics"""
    def __init__(self, entity, period, start_date, end_date):
        self.entity = entity  # Can be None for all entities
        self.period = period
        self.start_date = start_date
        self.end_date = end_date
        self.current_step = 1
        self.total_steps = 11  # Updated to include Step 5.5
        self.active_accounts = []  # List of non-skipped accounts
        self.active_entities = []  # List of entities with active accounts
        self.stats = {
            'related_party_loans_assigned': 0,
            'owner_draws_assigned': 0,
            'owner_contributions_assigned': 0,
            'mortgage_payments_assigned': 0,
            'smart_transfers_assigned': 0,  # New: single-sided transfers detected
            'bgs_expenses_assigned': 0,
            'mhb_expenses_assigned': 0,
            'csb_expenses_assigned': 0,
            'medical_expenses_assigned': 0,
            'tax_expenses_assigned': 0,
            'loans_assigned': 0,
            'recurring_assigned': 0,
            'manual_assigned': 0,
            'patterns_created': 0
        }


# ============================================================================
# Wizard Command
# ============================================================================

@allocate.command('wizard')
@click.option('--entity', '-e', required=False, help='Entity code (e.g., bgs). If omitted, shows all entities.')
@click.option('--period', '-p', required=True, help='Period: YYYY, YYYY-QN, or YYYY-MM')
def allocation_wizard(entity, period):
    """Guided allocation wizard for transaction categorization"""
    
    try:
        start_date, end_date = parse_period(period)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    # Initialize wizard state
    state = WizardState(entity, period, start_date, end_date)
    
    # Set header based on whether entity is specified
    if entity:
        header_entity = entity.upper()
    else:
        header_entity = "ALL ENTITIES"
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Allocation Wizard - {header_entity} - {period}[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
    
    # STEP 1: Import Status
    console.print(f"[bold cyan]STEP 1 of {state.total_steps}: Import Status[/bold cyan]")
    console.print("─" * 63)
    
    import_status = get_import_status(entity, start_date, end_date, period)
    
    if not import_status:
        if entity:
            console.print(f"[red]No accounts found for entity: {entity}[/red]\n")
        else:
            console.print("[red]No accounts found[/red]\n")
        return
    
    # Display and handle Step 1 - loop to allow skip/unskip operations
    while True:
        clear_screen()
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print(f"[bold cyan]   Allocation Wizard - {header_entity} - {period}[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
        console.print(f"[bold cyan]STEP 1 of {state.total_steps}: Import Status[/bold cyan]")
        console.print("─" * 63)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Entity", style="yellow")
        table.add_column("Account", style="white")
        table.add_column("Records", justify="right")
        table.add_column("Date Range", style="white")
        table.add_column("Status", style="white")
        
        for idx, row in enumerate(import_status, 1):
            if row['wizard_status'] == 'skipped':
                status = f"[dim]⊘ Skipped[/dim]"
                if row['skip_reason']:
                    status += f" [dim]({row['skip_reason'][:20]})[/dim]"
                date_range = ""
            elif row['record_count'] > 0:
                # Check if date range covers full period
                if row['min_date'] <= start_date and row['max_date'] >= end_date:
                    status = "[green]✓ Complete[/green]"
                else:
                    status = "[yellow]⚠ Partial[/yellow]"
                date_range = f"{row['min_date']} → {row['max_date']}"
            else:
                status = "[red]✗ Not imported[/red]"
                date_range = ""
            
            table.add_row(
                str(idx),
                row['entity'],
                row['account'],
                str(row['record_count']),
                date_range,
                status
            )
        
        console.print(table)
        console.print()
        
        # Check if we have any imports
        total_records = sum(row['record_count'] for row in import_status if row['wizard_status'] != 'skipped')
        if total_records == 0:
            console.print("[red]No transactions imported for this period (or all accounts skipped).[/red]")
            console.print("[dim]Use 'copilot import' to import bank statements first.[/dim]\n")
            return
        
        # Show commands
        console.print("[bold]Commands:[/bold]")
        console.print("  [c] Continue with imported accounts")
        console.print("  [s #,#] Skip account(s) - e.g., 's 3,4'")
        console.print("  [u #] Unskip account - e.g., 'u 3'")
        console.print("  [q] Quit")
        console.print()
        
        action = Prompt.ask("Enter command", default="c")
        
        if action.lower() == 'q':
            console.print("\n[yellow]Wizard cancelled[/yellow]\n")
            return
        elif action.lower() == 'c':
            # Store active (non-skipped) accounts in wizard state for later steps
            state.active_accounts = [row['account'] for row in import_status 
                                     if row['wizard_status'] != 'skipped']
            state.active_entities = list(set(row['entity'] for row in import_status 
                                             if row['wizard_status'] != 'skipped'))
            break
        elif action.lower().startswith('s '):
            # Parse account numbers to skip
            try:
                nums = [int(n.strip()) for n in action[2:].split(',')]
                for num in nums:
                    if 1 <= num <= len(import_status):
                        acc = import_status[num - 1]
                        if acc['wizard_status'] == 'skipped':
                            console.print(f"[yellow]Account {acc['account']} is already skipped[/yellow]")
                        else:
                            reason = Prompt.ask(f"Reason for skipping {acc['account']}", default="")
                            skip_account(acc['account'], acc['entity'], period, reason or None)
                            console.print(f"[yellow]Skipped: {acc['account']}[/yellow]")
                    else:
                        console.print(f"[red]Invalid account number: {num}[/red]")
                # Refresh display
                import_status = get_import_status(entity, start_date, end_date, period)
            except ValueError:
                console.print("[red]Invalid format. Use 's 3' or 's 3,4'[/red]")
                input("\nPress Enter to continue...")
        elif action.lower().startswith('u '):
            # Parse account number to unskip
            try:
                num = int(action[2:].strip())
                if 1 <= num <= len(import_status):
                    acc = import_status[num - 1]
                    if acc['wizard_status'] == 'skipped':
                        unskip_account(acc['account'], acc['entity'], period)
                        console.print(f"[green]Unskipped: {acc['account']}[/green]")
                    else:
                        console.print(f"[yellow]Account {acc['account']} is not skipped[/yellow]")
                else:
                    console.print(f"[red]Invalid account number: {num}[/red]")
                # Refresh display
                import_status = get_import_status(entity, start_date, end_date, period)
            except ValueError:
                console.print("[red]Invalid format. Use 'u 3'[/red]")
                input("\nPress Enter to continue...")
    
    # STEP 2: Business-to-Business Loans
    clear_screen()
    console.print(f"\n[bold cyan]STEP 2 of {state.total_steps}: Business-to-Business Loans[/bold cyan]")
    console.print("─" * 63)
    
    intercompany, entity_type_map = detect_intercompany_transfers(entity, start_date, end_date, state.active_accounts)
    
    if intercompany:
        console.print(f"[green]Found {len(intercompany)} business-to-business transfers:[/green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To", style="white")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Description", style="white")
        
        for row in intercompany[:10]:  # Show first 10
            table.add_row(
                str(row['normalized_date']),
                row['from_entity'],
                row['to_entity'],
                f"${abs(row['from_amount']):,.2f}",
                row['from_desc'][:30]
            )
        
        if len(intercompany) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(intercompany) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
        
        action = Prompt.ask(
            "[a] Auto-assign transfers    [r] Review one-by-one    [s] Skip",
            choices=['a', 'r', 's'],
            default='a'
        )
        
        if action == 'a':
            for row in intercompany:
                assign_intercompany(
                    row['from_id'], 
                    row['to_id'], 
                    row['from_entity'], 
                    row['to_entity'],
                    row['from_account'],
                    row['to_account'],
                    entity_type_map
                )
                state.stats['related_party_loans_assigned'] += 2
            console.print(f"\n[green]✓ Assigned {len(intercompany)} internal transfers ({state.stats['related_party_loans_assigned']} transactions)[/green]")
            input("\nPress Enter to continue...")
        elif action == 'r':
            console.print("\n[yellow]Review mode not implemented yet. Use auto-assign or skip.[/yellow]")
            input("\nPress Enter to continue...")
    else:
        console.print("[dim]No internal transfers detected[/dim]\n")
        input("Press Enter to continue...")
    
    # STEP 3: Owner Draws
    clear_screen()
    console.print(f"\n[bold cyan]STEP 3 of {state.total_steps}: Owner Draws[/bold cyan]")
    console.print("─" * 63)
    
    owner_draws = detect_owner_draws(entity, start_date, end_date, state.active_accounts, entity_type_map)
    
    if owner_draws:
        console.print(f"[green]Found {len(owner_draws)} owner draws (Business → Personal/Support):[/green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To", style="white")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Description", style="white")
        
        for row in owner_draws[:10]:  # Show first 10
            table.add_row(
                str(row['normalized_date']),
                row['from_entity'],
                row['to_entity'],
                f"${abs(row['from_amount']):,.2f}",
                row['from_desc'][:30]
            )
        
        if len(owner_draws) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(owner_draws) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
        
        action = Prompt.ask(
            "[a] Auto-assign draws    [r] Review one-by-one    [s] Skip",
            choices=['a', 'r', 's'],
            default='a'
        )
        
        if action == 'a':
            for row in owner_draws:
                assign_intercompany(
                    row['from_id'], 
                    row['to_id'], 
                    row['from_entity'], 
                    row['to_entity'],
                    row['from_account'],
                    row['to_account'],
                    entity_type_map
                )
                state.stats['owner_draws_assigned'] += 2
            console.print(f"\n[green]✓ Assigned {len(owner_draws)} owner draws ({state.stats['owner_draws_assigned']} transactions)[/green]")
            input("\nPress Enter to continue...")
        elif action == 'r':
            console.print("\n[yellow]Review mode not implemented yet. Use auto-assign or skip.[/yellow]")
            input("\nPress Enter to continue...")
    else:
        console.print("[dim]No owner draws detected[/dim]\n")
        input("Press Enter to continue...")
    
    # STEP 4: Owner Contributions
    clear_screen()
    console.print(f"\n[bold cyan]STEP 4 of {state.total_steps}: Owner Contributions[/bold cyan]")
    console.print("─" * 63)
    
    owner_contributions = detect_owner_contributions(entity, start_date, end_date, state.active_accounts, entity_type_map)
    
    if owner_contributions:
        console.print(f"[green]Found {len(owner_contributions)} owner contributions (Personal/Support → Business):[/green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To", style="white")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Description", style="white")
        
        for row in owner_contributions[:10]:  # Show first 10
            table.add_row(
                str(row['normalized_date']),
                row['from_entity'],
                row['to_entity'],
                f"${abs(row['from_amount']):,.2f}",
                row['from_desc'][:30]
            )
        
        if len(owner_contributions) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(owner_contributions) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
        
        action = Prompt.ask(
            "[a] Auto-assign contributions    [r] Review one-by-one    [s] Skip",
            choices=['a', 'r', 's'],
            default='a'
        )
        
        if action == 'a':
            for row in owner_contributions:
                assign_intercompany(
                    row['from_id'], 
                    row['to_id'], 
                    row['from_entity'], 
                    row['to_entity'],
                    row['from_account'],
                    row['to_account'],
                    entity_type_map
                )
                state.stats['owner_contributions_assigned'] += 2
            console.print(f"\n[green]✓ Assigned {len(owner_contributions)} owner contributions ({state.stats['owner_contributions_assigned']} transactions)[/green]")
            input("\nPress Enter to continue...")
        elif action == 'r':
            console.print("\n[yellow]Review mode not implemented yet. Use auto-assign or skip.[/yellow]")
            input("\nPress Enter to continue...")
    else:
        console.print("[dim]No owner contributions detected[/dim]\n")
        input("Press Enter to continue...")
    
    # STEP 5: Mortgage Payments
    clear_screen()
    console.print(f"\n[bold cyan]STEP 5 of {state.total_steps}: Mortgage Payments[/bold cyan]")
    console.print("─" * 63)
    
    mortgage_payments = detect_mortgage_payments(entity, start_date, end_date, state.active_accounts)
    
    if mortgage_payments:
        console.print(f"[green]Found {len(mortgage_payments)} mortgage payments:[/green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To Account", style="white")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Description", style="white")
        
        for row in mortgage_payments[:10]:  # Show first 10
            table.add_row(
                str(row['normalized_date']),
                row['from_entity'],
                row['to_account'],
                f"${abs(row['from_amount']):,.2f}",
                row['from_desc'][:30]
            )
        
        if len(mortgage_payments) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(mortgage_payments) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
        
        action = Prompt.ask(
            "[a] Auto-assign mortgages    [r] Review one-by-one    [s] Skip",
            choices=['a', 'r', 's'],
            default='a'
        )
        
        if action == 'a':
            for row in mortgage_payments:
                assign_intercompany(
                    row['from_id'], 
                    row['to_id'], 
                    row['from_entity'], 
                    row['to_entity'],
                    row['from_account'],
                    row['to_account'],
                    entity_type_map
                )
                state.stats['mortgage_payments_assigned'] += 2
            console.print(f"\n[green]✓ Assigned {len(mortgage_payments)} mortgage payments ({state.stats['mortgage_payments_assigned']} transactions)[/green]")
            input("\nPress Enter to continue...")
        elif action == 'r':
            console.print("\n[yellow]Review mode not implemented yet. Use auto-assign or skip.[/yellow]")
            input("\nPress Enter to continue...")
    else:
        console.print("[dim]No mortgage payments detected[/dim]\n")
        input("Press Enter to continue...")
    
    # STEP 5.5: Auto-detect Single-Sided Transfers
    clear_screen()
    console.print(f"\n[bold cyan]STEP 5.5 of {state.total_steps}: Smart Transfer Detection[/bold cyan]")
    console.print("─" * 63)
    console.print("[dim]Scanning for unmatched transfers with account numbers in description...[/dim]\n")
    
    single_transfer_count = detect_and_assign_single_transfers(entity, start_date, end_date, state.active_accounts)
    
    if single_transfer_count > 0:
        console.print(f"[green]✓ Auto-assigned {single_transfer_count} single-sided transfers using smart detection![/green]\n")
        state.stats['smart_transfers_assigned'] += single_transfer_count
    else:
        console.print("[dim]No additional single-sided transfers detected[/dim]\n")
    
    input("Press Enter to continue...")
    
    # STEP 6: BGS Business Expenses
    clear_screen()
    console.print(f"\n[bold cyan]STEP 6 of {state.total_steps}: BGS Business Expenses[/bold cyan]")
    console.print("─" * 63)
    
    bgs_expenses = get_entity_expenses('bgs', start_date, end_date, state.active_accounts)
    
    if bgs_expenses:
        console.print(f"[green]Found {len(bgs_expenses)} unallocated BGS expenses:[/green]\n")
        console.print("[dim]Use 'copilot staging assign-todo --entity bgs' for interactive assignment[/dim]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right")
        
        for row in bgs_expenses[:10]:  # Show first 10
            amount_style = "green" if row['amount'] > 0 else "red"
            table.add_row(
                str(row['normalized_date']),
                row['source_account_code'],
                row['description'][:40],
                f"[{amount_style}]${row['amount']:,.2f}[/{amount_style}]"
            )
        
        if len(bgs_expenses) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(bgs_expenses) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
    else:
        console.print("[green]✓ All BGS expenses allocated![/green]\n")
    
    input("Press Enter to continue...")
    
    # STEP 7: MHB Business Expenses
    clear_screen()
    console.print(f"\n[bold cyan]STEP 7 of {state.total_steps}: MHB Business Expenses[/bold cyan]")
    console.print("─" * 63)
    
    mhb_expenses = get_entity_expenses('mhb', start_date, end_date, state.active_accounts)
    
    if mhb_expenses:
        console.print(f"[green]Found {len(mhb_expenses)} unallocated MHB expenses:[/green]\n")
        console.print("[dim]Use 'copilot staging assign-todo --entity mhb' for interactive assignment[/dim]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right")
        
        for row in mhb_expenses[:10]:  # Show first 10
            amount_style = "green" if row['amount'] > 0 else "red"
            table.add_row(
                str(row['normalized_date']),
                row['source_account_code'],
                row['description'][:40],
                f"[{amount_style}]${row['amount']:,.2f}[/{amount_style}]"
            )
        
        if len(mhb_expenses) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(mhb_expenses) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
    else:
        console.print("[green]✓ All MHB expenses allocated![/green]\n")
    
    input("Press Enter to continue...")
    
    # STEP 8: CSB Personal Expenses
    clear_screen()
    console.print(f"\n[bold cyan]STEP 8 of {state.total_steps}: CSB Personal Expenses[/bold cyan]")
    console.print("─" * 63)
    
    csb_expenses = get_entity_expenses('csb', start_date, end_date, state.active_accounts)
    
    if csb_expenses:
        console.print(f"[green]Found {len(csb_expenses)} unallocated CSB expenses:[/green]\n")
        console.print("[dim]Use 'copilot staging assign-todo --entity csb' for interactive assignment[/dim]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right")
        
        for row in csb_expenses[:10]:  # Show first 10
            amount_style = "green" if row['amount'] > 0 else "red"
            table.add_row(
                str(row['normalized_date']),
                row['source_account_code'],
                row['description'][:40],
                f"[{amount_style}]${row['amount']:,.2f}[/{amount_style}]"
            )
        
        if len(csb_expenses) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(csb_expenses) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
    else:
        console.print("[green]✓ All CSB expenses allocated![/green]\n")
    
    input("Press Enter to continue...")
    
    # STEP 9: Medical Payments
    clear_screen()
    console.print(f"\n[bold cyan]STEP 9 of {state.total_steps}: Medical Payments[/bold cyan]")
    console.print("─" * 63)
    
    medical_expenses = get_entity_expenses('medical', start_date, end_date, state.active_accounts)
    
    if medical_expenses:
        console.print(f"[green]Found {len(medical_expenses)} unallocated medical payments:[/green]\n")
        console.print("[dim]Use 'copilot staging assign-todo --entity medical' for interactive assignment[/dim]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right")
        
        for row in medical_expenses[:10]:  # Show first 10
            amount_style = "green" if row['amount'] > 0 else "red"
            table.add_row(
                str(row['normalized_date']),
                row['source_account_code'],
                row['description'][:40],
                f"[{amount_style}]${row['amount']:,.2f}[/{amount_style}]"
            )
        
        if len(medical_expenses) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(medical_expenses) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
    else:
        console.print("[green]✓ All medical payments allocated![/green]\n")
    
    input("Press Enter to continue...")
    
    # STEP 10: Tax Payments
    clear_screen()
    console.print(f"\n[bold cyan]STEP 10 of {state.total_steps}: Tax Payments[/bold cyan]")
    console.print("─" * 63)
    
    tax_expenses = get_entity_expenses('tax', start_date, end_date, state.active_accounts)
    
    if tax_expenses:
        console.print(f"[green]Found {len(tax_expenses)} unallocated tax payments:[/green]\n")
        console.print("[dim]Use 'copilot staging assign-todo --entity tax' for interactive assignment[/dim]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right")
        
        for row in tax_expenses[:10]:  # Show first 10
            amount_style = "green" if row['amount'] > 0 else "red"
            table.add_row(
                str(row['normalized_date']),
                row['source_account_code'],
                row['description'][:40],
                f"[{amount_style}]${row['amount']:,.2f}[/{amount_style}]"
            )
        
        if len(tax_expenses) > 10:
            console.print(table)
            console.print(f"[dim]... and {len(tax_expenses) - 10} more[/dim]\n")
        else:
            console.print(table)
            console.print()
    else:
        console.print("[green]✓ All tax payments allocated![/green]\n")
    
    input("[Enter] to view summary    [q] Quit")

    
    # Summary Screen
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Allocation Complete![/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"[bold]Summary for {header_entity} - {period}:[/bold]\n")
    
    final_progress = get_allocation_progress(entity, start_date, end_date)
    
    console.print(f"  Total transactions:      {final_progress['total']}")
    console.print(f"  Allocated:               {final_progress['allocated']} ({final_progress['allocated']/final_progress['total']*100 if final_progress['total'] > 0 else 0:.0f}%)")
    console.print(f"  Remaining:               {final_progress['remaining']}\n")
    
    console.print("  [bold]By category:[/bold]")
    console.print(f"    Business-to-Business:   {state.stats['related_party_loans_assigned']}")
    console.print(f"    Owner Draws:            {state.stats['owner_draws_assigned']}")
    console.print(f"    Owner Contributions:    {state.stats['owner_contributions_assigned']}")
    console.print(f"    Mortgage Payments:      {state.stats['mortgage_payments_assigned']}")
    console.print(f"    Smart Transfers:        {state.stats['smart_transfers_assigned']}")
    console.print(f"    BGS Expenses:           {state.stats['bgs_expenses_assigned']}")
    console.print(f"    MHB Expenses:           {state.stats['mhb_expenses_assigned']}")
    console.print(f"    CSB Expenses:           {state.stats['csb_expenses_assigned']}")
    console.print(f"    Medical Expenses:       {state.stats['medical_expenses_assigned']}")
    console.print(f"    Tax Expenses:           {state.stats['tax_expenses_assigned']}")
    console.print()
    console.print(f"  Patterns created:         {state.stats['patterns_created']}\n")
    
    console.print("[dim]Use 'copilot report' to generate reports or 'copilot staging' for more details[/dim]\n")


@allocate.command('apply-patterns')
@click.option('--dry-run', is_flag=True, help='Preview matches without updating')
@click.option('--entity', '-e', help='Filter by entity (e.g., bgs, mhb)')
@click.option('--from', 'from_date', help='Filter by date range start (YYYY-MM-DD)')
@click.option('--to', 'to_date', help='Filter by date range end (YYYY-MM-DD)')
def apply_patterns(dry_run, entity, from_date, to_date):
    """Apply vendor GL patterns to TODO transactions"""
    
    if dry_run:
        console.print("\n[bold cyan]Dry Run - Pattern Matching Preview[/bold cyan]")
        console.print("─" * 38)
        console.print()
    else:
        console.print("\n[bold cyan]Applying Patterns to TODO Transactions[/bold cyan]")
        console.print("─" * 38)
        console.print()
    
    # Build WHERE clause for filtering
    # Note: where_clauses contains only static SQL fragments (safe)
    # User input goes into params list (parameterized)
    where_clauses = ["bs.gl_account_code = 'TODO'"]
    params = []
    
    if entity:
        where_clauses.append("bs.entity = %s")
        params.append(entity)
    
    if from_date:
        where_clauses.append("bs.normalized_date >= %s")
        params.append(from_date)
    
    if to_date:
        where_clauses.append("bs.normalized_date <= %s")
        params.append(to_date)
    
    # Join static SQL clauses (no user input in the structure)
    where_clause = " AND ".join(where_clauses)
    
    # Get all active patterns
    pattern_query = """
        SELECT id, pattern, pattern_type, gl_account_code, entity
        FROM acc.vendor_gl_patterns
        WHERE is_active = true
    """
    pattern_params = []
    
    # If entity filter is specified, get patterns for that entity AND wildcard patterns (entity IS NULL)
    if entity:
        pattern_query += " AND (entity IS NULL OR entity = %s)"
        pattern_params.append(entity)
    
    pattern_query += " ORDER BY priority DESC, id"
    
    patterns = execute_query(pattern_query, tuple(pattern_params) if pattern_params else None)
    
    if not patterns:
        console.print("[yellow]No active patterns found[/yellow]\n")
        return
    
    # For each pattern, find matching transactions
    total_matched = 0
    pattern_matches = []
    
    for pattern in patterns:
        # Build the ILIKE condition based on pattern_type
        # Returns static SQL clause and parameterized value (safe)
        like_condition, like_param = build_like_condition(pattern['pattern_type'], pattern['pattern'])
        
        # Query to find matching transactions in the pattern's entity
        # Copy base WHERE clauses and parameters
        pattern_where_clauses = where_clauses.copy()
        pattern_params = params.copy()
        
        # Add pattern entity filter (pattern['entity'] comes from DB, safe)
        # If pattern entity is NULL, it's a wildcard that matches all entities
        if pattern['entity'] is not None:
            pattern_where_clauses.append("bs.entity = %s")
            pattern_params.append(pattern['entity'])
        
        # Join static SQL clauses (no user input in the structure)
        pattern_where_clause = " AND ".join(pattern_where_clauses)
        
        # Build query using f-string for structure (safe: only static SQL clauses)
        # All user input is passed as parameters
        match_query = f"""
            SELECT 
                bs.id,
                bs.description,
                bs.amount,
                bs.normalized_date
            FROM acc.bank_staging bs
            WHERE {pattern_where_clause}
              AND {like_condition}
            ORDER BY bs.normalized_date DESC
        """
        
        # Combine parameters: pattern_where_clause params + like_param
        query_params = pattern_params + [like_param]
        
        matches = execute_query(match_query, tuple(query_params))
        
        if matches:
            pattern_matches.append({
                'pattern': pattern,
                'matches': matches
            })
            total_matched += len(matches)
    
    if total_matched == 0:
        console.print("[yellow]No TODO transactions match active patterns[/yellow]\n")
        return
    
    # Display results based on mode
    if dry_run:
        # Dry run: show preview grouped by pattern
        for pm in pattern_matches:
            pattern = pm['pattern']
            matches = pm['matches']
            
            pattern_type = pattern['pattern_type'] or 'contains'
            console.print(f"[bold]Pattern:[/bold] {pattern['pattern']} ({pattern_type}) → [cyan]{pattern['gl_account_code']}[/cyan]")
            
            for match in matches:
                amount_str = format_currency(match['amount'])
                console.print(f"  • {match['description'][:MAX_DESCRIPTION_LENGTH]:<{MAX_DESCRIPTION_LENGTH}} {amount_str:>12}")
            
            console.print()
        
        console.print("─" * 38)
        console.print(f"[bold]Total:[/bold] {total_matched} transactions would be updated")
        console.print()
        console.print("[dim]Run without --dry-run to apply changes.[/dim]\n")
    
    else:
        # Apply mode: update transactions
        updated_count = 0
        
        for pm in pattern_matches:
            pattern = pm['pattern']
            matches = pm['matches']
            
            if matches:
                # Update all matching transactions for this pattern
                # Extract IDs (integers from database query, validated for safety)
                transaction_ids = [m['id'] for m in matches if isinstance(m['id'], int)]
                
                if not transaction_ids:
                    console.print(f"[red]Error: No valid transaction IDs found for pattern {pattern['pattern']}[/red]")
                    continue
                
                # Build UPDATE query with parameterized IN clause
                # Generate placeholders: one %s per ID (safe: known count)
                placeholders = ','.join(['%s'] * len(transaction_ids))
                # Use f-string for structure (safe: placeholders is just a string of "%s,%s,...")
                update_query = f"""
                    UPDATE acc.bank_staging
                    SET gl_account_code = %s,
                        match_method = 'pattern',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """
                
                # Combine GL code with all transaction IDs (all parameterized)
                update_params = [pattern['gl_account_code']] + transaction_ids
                execute_command(update_query, tuple(update_params))
                
                pattern_type = pattern['pattern_type'] or 'contains'
                console.print(f"[bold]Pattern:[/bold] {pattern['pattern']} ({pattern_type}) → [cyan]{pattern['gl_account_code']}[/cyan]")
                console.print(f"  [green]✓[/green] {len(matches)} transactions updated")
                console.print()
                
                updated_count += len(matches)
        
        # Get remaining TODO count
        # Use f-string for structure (safe: where_clause is static SQL clauses)
        remaining_query = f"""
            SELECT COUNT(*) as count
            FROM acc.bank_staging bs
            WHERE {where_clause}
        """
        remaining_result = execute_query(remaining_query, tuple(params))
        remaining_count = remaining_result[0]['count'] if remaining_result else 0
        
        console.print("─" * 38)
        console.print(f"[bold]Total:[/bold] {updated_count} transactions updated")
        console.print(f"[bold]Remaining TODOs:[/bold] {remaining_count}")
        console.print()
