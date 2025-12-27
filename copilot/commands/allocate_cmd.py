"""
Transaction allocation command - Categorize transactions
"""
import click
import os
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, get_connection

console = Console()


def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


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
