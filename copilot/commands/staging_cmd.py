import click
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from copilot.db import execute_query, execute_command
from copilot.commands.allocate_cmd import detect_transfer_gl_code

console = Console()

# Constants
MAX_DESCRIPTION_LENGTH = 50
MAX_KEYWORD_LENGTH = 30

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


# ============================================================================
# Helper functions for assign-todo command
# ============================================================================

def get_todo_grouped(entity):
    """Return TODO transactions grouped by description with counts"""
    query = """
        SELECT description, COUNT(*) as cnt, SUM(amount) as total
        FROM acc.bank_staging
        WHERE gl_account_code = 'TODO'
          AND entity = %s
        GROUP BY description
        ORDER BY COUNT(*) DESC
    """
    return execute_query(query, (entity,))


def get_existing_patterns(description, entity):
    """Find matching patterns for a description"""
    query = """
        SELECT pattern, gl_account_code, notes
        FROM acc.vendor_gl_patterns
        WHERE %s ILIKE '%%' || pattern || '%%'
          AND entity = %s
          AND is_active = true
        ORDER BY priority DESC
    """
    return execute_query(query, (description, entity))


def get_similar_assignments(description, entity):
    """Find similar descriptions that have been assigned GL codes"""
    query = """
        SELECT DISTINCT description, gl_account_code, COUNT(*) as cnt
        FROM acc.bank_staging
        WHERE gl_account_code != 'TODO'
          AND entity = %s
          AND description != %s
        GROUP BY description, gl_account_code
        ORDER BY cnt DESC
        LIMIT 5
    """
    return execute_query(query, (entity, description))


def get_gl_usage_stats(entity):
    """Get GL code usage frequency for this entity"""
    query = """
        SELECT gl_account_code, COUNT(*) as cnt
        FROM acc.bank_staging
        WHERE gl_account_code != 'TODO'
          AND entity = %s
        GROUP BY gl_account_code
        ORDER BY cnt DESC
        LIMIT 10
    """
    return execute_query(query, (entity,))


def get_transactions_by_description(description, entity):
    """Fetch individual transactions for a description group"""
    query = """
        SELECT id, normalized_date, amount, check_number, source_account_code
        FROM acc.bank_staging
        WHERE description = %s
          AND entity = %s
          AND gl_account_code = 'TODO'
        ORDER BY normalized_date
    """
    return execute_query(query, (description, entity))


def assign_single_transaction(transaction_id, gl_code):
    """Update a single transaction by ID - no pattern created"""
    query = """
        UPDATE acc.bank_staging
        SET gl_account_code = %s,
            match_method = 'manual',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    execute_command(query, (gl_code, transaction_id))


def assign_gl_code(description, gl_code, entity, notes=None):
    """Update all matching transactions and create/update pattern
    
    Returns:
        tuple: (count of updated transactions, 'created' or 'updated' for pattern)
    """
    
    try:
        # Count affected rows
        count_query = """
            SELECT COUNT(*) as cnt
            FROM acc.bank_staging
            WHERE description = %s
              AND gl_account_code = 'TODO'
              AND entity = %s
        """
        count_result = execute_query(count_query, (description, entity))
        count = count_result[0]['cnt'] if count_result else 0
        
        # Update bank_staging
        update_query = """
            UPDATE acc.bank_staging
            SET gl_account_code = %s,
                match_method = 'manual',
                updated_at = CURRENT_TIMESTAMP
            WHERE description = %s
              AND gl_account_code = 'TODO'
              AND entity = %s
        """
        execute_command(update_query, (gl_code, description, entity))
        
    except Exception as e:
        console.print(f"[red]Error updating transactions: {e}[/red]")
        raise
    
    try:
        # Create or update pattern for future imports
        pattern = description
        
        # Check if pattern exists
        check_query = """
            SELECT id FROM acc.vendor_gl_patterns
            WHERE pattern = %s AND entity = %s
        """
        existing = execute_query(check_query, (pattern, entity))
        
        pattern_action = 'updated' if existing else 'created'
        
        if existing:
            # Update existing pattern
            update_pattern_query = """
                UPDATE acc.vendor_gl_patterns
                SET gl_account_code = %s,
                    notes = %s
                WHERE pattern = %s AND entity = %s
            """
            execute_command(update_pattern_query, (gl_code, notes, pattern, entity))
        else:
            # Insert new pattern
            insert_pattern_query = """
                INSERT INTO acc.vendor_gl_patterns (pattern, gl_account_code, entity, notes, priority)
                VALUES (%s, %s, %s, %s, 100)
            """
            execute_command(insert_pattern_query, (pattern, gl_code, entity, notes))
            
    except Exception as e:
        console.print(f"[red]Error updating pattern: {e}[/red]")
        raise
    
    return count, pattern_action


def list_gl_codes(filter_type=None):
    """List available GL account codes"""
    if filter_type:
        query = """
            SELECT code, name, account_type
            FROM acc.bank_account
            WHERE status = 'active'
              AND account_type ILIKE %s
            ORDER BY code
        """
        return execute_query(query, (f'%{filter_type}%',))
    else:
        query = """
            SELECT code, name, account_type
            FROM acc.bank_account
            WHERE status = 'active'
            ORDER BY account_type, code
        """
        return execute_query(query)

@click.group('staging')
def staging_cmd():
    """Manage bank staging transactions"""
    pass


@staging_cmd.command('list')
@click.option('--entity', '-e', help='Filter by entity (bgs, per, mhb, etc.)')
@click.option('--account', '-a', help='Filter by account code')
@click.option('--status', '-s', type=click.Choice(['todo', 'pattern', 'manual', 'all']), default='all', help='Filter by match status')
@click.option('--limit', '-l', default=50, help='Number of records to show')
def staging_list(entity, account, status, limit):
    """List staged bank transactions"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Bank Staging Transactions[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    conditions = []
    params = []
    
    if entity:
        conditions.append("entity = %s")
        params.append(entity)
    if account:
        conditions.append("source_account_code = %s")
        params.append(account)
    if status and status != 'all':
        if status == 'todo':
            conditions.append("gl_account_code = 'TODO'")
        else:
            conditions.append("match_method = %s")
            params.append(status)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    
    query = f"""
        SELECT 
            id,
            source_account_code,
            normalized_date,
            SUBSTRING(description, 1, 40) as description,
            amount,
            gl_account_code,
            match_method,
            check_number,
            entity
        FROM acc.bank_staging
        {where_clause}
        ORDER BY normalized_date DESC, id DESC
        LIMIT %s
    """
    
    results = execute_query(query, tuple(params))
    
    if not results:
        console.print("[yellow]No staged transactions found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Account", style="white")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Amount", justify="right")
    table.add_column("GL Code", style="yellow")
    table.add_column("Match", style="dim")
    table.add_column("Check #", style="cyan")
    
    for row in results:
        amount_style = "green" if row['amount'] > 0 else "red"
        gl_style = "red bold" if row['gl_account_code'] == 'TODO' else "yellow"
        table.add_row(
            str(row['id']),
            row['source_account_code'],
            str(row['normalized_date']),
            row['description'],
            f"[{amount_style}]{row['amount']:,.2f}[/{amount_style}]",
            f"[{gl_style}]{row['gl_account_code']}[/{gl_style}]",
            row['match_method'] or '-',
            row['check_number'] or '-'
        )
    
    console.print(table)


@staging_cmd.command('todos')
@click.option('--entity', '-e', help='Filter by entity')
def staging_todos(entity):
    """List transactions needing GL assignment (TODO status)"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Transactions Needing GL Assignment[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "AND entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT 
            id,
            source_account_code,
            normalized_date,
            description,
            amount,
            check_number,
            entity
        FROM acc.bank_staging
        WHERE gl_account_code = 'TODO'
        {entity_filter}
        ORDER BY entity, normalized_date DESC
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[green]✓ No TODO transactions - all allocated![/green]")
        return
    
    console.print(f"[yellow]Found {len(results)} transactions needing GL assignment[/yellow]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Entity", style="white")
    table.add_column("Account", style="white")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Amount", justify="right")
    table.add_column("Check #", style="cyan")
    
    for row in results:
        amount_style = "green" if row['amount'] > 0 else "red"
        table.add_row(
            str(row['id']),
            row['entity'],
            row['source_account_code'],
            str(row['normalized_date']),
            row['description'][:50],
            f"[{amount_style}]{row['amount']:,.2f}[/{amount_style}]",
            row['check_number'] or '-'
        )
    
    console.print(table)
    console.print(f"\n[dim]Use 'copilot staging assign <id> <gl_code>' to assign GL codes[/dim]")


@staging_cmd.command('assign')
@click.argument('staging_id', type=int)
@click.argument('gl_code')
def staging_assign(staging_id, gl_code):
    """Assign GL code to a staged transaction"""
    
    # Verify staging record exists
    check = execute_query("SELECT id, description, amount FROM acc.bank_staging WHERE id = %s", (staging_id,))
    if not check:
        console.print(f"[red]Error: Staging record {staging_id} not found[/red]")
        return
    
    # Update the GL code
    execute_command("""
        UPDATE acc.bank_staging 
        SET gl_account_code = %s, match_method = 'manual', updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (gl_code, staging_id))
    
    console.print(f"[green]✓ Assigned GL code '{gl_code}' to staging ID {staging_id}[/green]")
    console.print(f"[dim]  {check[0]['description'][:50]} | {check[0]['amount']:,.2f}[/dim]")


@staging_cmd.command('summary')
@click.option('--entity', '-e', help='Filter by entity')
def staging_summary(entity):
    """Show staging summary by status"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Staging Summary[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT 
            entity,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE gl_account_code = 'TODO') as todos,
            COUNT(*) FILTER (WHERE match_method = 'pattern') as pattern_matched,
            COUNT(*) FILTER (WHERE match_method = 'manual') as manual,
            SUM(amount) FILTER (WHERE amount > 0) as total_credits,
            SUM(amount) FILTER (WHERE amount < 0) as total_debits
        FROM acc.bank_staging
        {entity_filter}
        GROUP BY entity
        ORDER BY entity
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No staged transactions[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Entity", style="white")
    table.add_column("Total", justify="right")
    table.add_column("TODOs", justify="right", style="red")
    table.add_column("Pattern", justify="right", style="cyan")
    table.add_column("Manual", justify="right", style="green")
    table.add_column("Credits", justify="right", style="green")
    table.add_column("Debits", justify="right", style="red")
    
    for row in results:
        table.add_row(
            row['entity'],
            str(row['total']),
            str(row['todos']),
            str(row['pattern_matched']),
            str(row['manual']),
            f"{row['total_credits'] or 0:,.2f}",
            f"{row['total_debits'] or 0:,.2f}"
        )
    
    console.print(table)


@staging_cmd.command('transfers')
@click.option('--entity', '-e', help='Filter by entity')
def staging_transfers(entity):
    """Show unmatched transfer transactions"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Unmatched Transfers[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "AND entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT * FROM acc.vw_unmatched_transfers
        WHERE 1=1 {entity_filter}
        ORDER BY normalized_date DESC
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[green]✓ All transfers matched![/green]")
        return
    
    console.print(f"[yellow]Found {len(results)} unmatched transfers[/yellow]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Account", style="white")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Amount", justify="right")
    table.add_column("Direction", style="yellow")
    
    for row in results:
        amount_style = "green" if row['amount'] > 0 else "red"
        table.add_row(
            str(row['staging_id']),
            row['source_account_code'],
            str(row['normalized_date']),
            row['description'][:40],
            f"[{amount_style}]{row['amount']:,.2f}[/{amount_style}]",
            row['direction']
        )
    
    console.print(table)


def handle_transaction_detail_selection(description, entity):
    """Handle sub-selection flow for individual transactions within a description group
    
    This function displays individual transactions within a description group and allows
    the user to assign GL codes either collectively (with pattern) or individually (no pattern).
    Always returns after user completes assignments or chooses to go back.
    """
    while True:
        clear_screen()
        
        # Get current transactions for this description
        transactions = get_transactions_by_description(description, entity)
        
        if not transactions:
            # All transactions assigned, return to main list
            console.print("[green]✓ All transactions in this group have been assigned![/green]")
            console.input("\nPress Enter to continue...")
            return
        
        # Display header
        console.print(f"\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print(f"[bold cyan]   \"{description}\" - {len(transactions)} transaction(s)[/bold cyan]")
        console.print(f"[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        # Display individual transactions table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Date", style="cyan")
        table.add_column("Amount", justify="right")
        table.add_column("Check#", style="yellow")
        table.add_column("Source Account", style="white")
        
        for idx, txn in enumerate(transactions, 1):
            amount_style = "green" if txn['amount'] > 0 else "red"
            table.add_row(
                str(idx),
                str(txn['normalized_date']),
                f"[{amount_style}]${txn['amount']:,.2f}[/{amount_style}]",
                txn['check_number'] or '-',
                txn['source_account_code']
            )
        
        console.print(table)
        console.print()
        
        # Display options
        console.print("[bold white]Options:[/bold white]")
        console.print("  [bold cyan][A][/bold cyan] Assign ALL to same GL code (creates pattern)")
        console.print(f"  [bold cyan][1-{len(transactions)}][/bold cyan] Select individual transaction (no pattern)")
        console.print("  [bold cyan][S][/bold cyan] Search GL codes")
        console.print("  [bold cyan][Q][/bold cyan] Back to main list")
        console.print()
        
        # Get user selection
        selection = console.input("[bold yellow]Enter choice: [/bold yellow]").strip().upper()
        
        if selection == 'Q':
            return
        
        elif selection == 'S':
            # Show GL code search/list
            console.print("\n[bold]Available GL Codes:[/bold]\n")
            codes = list_gl_codes()
            
            if codes:
                code_table = Table(show_header=True, header_style="bold magenta")
                code_table.add_column("Code", style="cyan")
                code_table.add_column("Name", style="white")
                code_table.add_column("Type", style="green")
                
                for code in codes[:30]:  # Show first 30
                    code_table.add_row(code['code'], code['name'], code['account_type'])
                
                console.print(code_table)
                if len(codes) > 30:
                    console.print(f"\n[dim]Showing 30 of {len(codes)} codes. Use 'copilot gl list' for full list.[/dim]")
            
            console.input("\n[dim]Press Enter to continue...[/dim]")
            continue
        
        elif selection == 'A':
            # Assign all transactions to same GL code
            console.print(f"\n[bold]Assigning ALL {len(transactions)} transactions[/bold]\n")
            
            # Get optional context from user
            user_context = console.input("Describe this transaction (optional, helps with recommendations): ")
            
            # Get GL code
            gl_code = console.input("\n[bold yellow]Enter GL code: [/bold yellow]").strip()
            
            if not gl_code:
                console.print("[yellow]No GL code entered, skipping...[/yellow]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Confirm
            confirmation = console.input(f"\n[bold yellow]Apply '{gl_code}' to all {len(transactions)} transactions? [Y/n]: [/bold yellow]").strip().lower()
            
            if confirmation in ('n', 'no'):
                console.print("[dim]Skipped - no changes made[/dim]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Assign the GL code using existing function (creates pattern)
            try:
                updated_count, pattern_action = assign_gl_code(description, gl_code, entity, user_context or None)
                
                console.print(f"\n[green]✓ Updated {updated_count} transaction(s) for \"{description}\" → {gl_code}[/green]")
                console.print(f"[green]✓ {pattern_action.capitalize()} pattern for future imports[/green]")
                if user_context:
                    console.print(f"[green]✓ Saved note: \"{user_context}\"[/green]")
                
                console.input("\n[dim]Press Enter to continue...[/dim]")
                return  # Return to main list
                
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.input("\nPress Enter to continue...")
                continue
        
        else:
            # Try to parse as individual transaction number
            try:
                idx = int(selection) - 1
                if idx < 0 or idx >= len(transactions):
                    console.print("[red]Invalid selection[/red]")
                    console.input("\nPress Enter to continue...")
                    continue
            except ValueError:
                console.print("[red]Invalid input[/red]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Assign individual transaction
            selected_txn = transactions[idx]
            
            console.print(f"\n[bold green]Selected transaction #{idx + 1}:[/bold green]")
            console.print(f"  Date: {selected_txn['normalized_date']}")
            console.print(f"  Amount: ${selected_txn['amount']:,.2f}")
            console.print(f"  Account: {selected_txn['source_account_code']}\n")
            
            # Get GL code
            gl_code = console.input("[bold yellow]Enter GL code: [/bold yellow]").strip()
            
            if not gl_code:
                console.print("[yellow]No GL code entered, skipping...[/yellow]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Assign the single transaction (no pattern)
            try:
                assign_single_transaction(selected_txn['id'], gl_code)
                console.print(f"\n[green]✓ Updated transaction #{idx + 1} → {gl_code}[/green]")
                console.print(f"[dim](No pattern created - individual assignment)[/dim]")
                console.input("\n[dim]Press Enter to continue...[/dim]")
                # Loop back to show remaining transactions
                
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.input("\nPress Enter to continue...")
                continue


@staging_cmd.command('assign-todo')
@click.option('--entity', '-e', required=True, help='Entity code (e.g., bgs)')
def assign_todo(entity):
    """Interactive GL code assignment for TODO transactions"""
    
    while True:
        clear_screen()
        
        # Display header
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print(f"[bold cyan]   Assign GL Codes - {entity.upper()} Entity[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        # Get grouped TODO transactions
        todos = get_todo_grouped(entity)
        
        if not todos:
            console.print("[green]✓ No TODO transactions - all assigned![/green]")
            return
        
        console.print("Transactions needing GL codes (grouped by description):\n")
        
        # Display grouped transactions table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Description", style="white")
        table.add_column("Count", justify="right", style="yellow")
        table.add_column("Total Amount", justify="right")
        
        for idx, row in enumerate(todos, 1):
            amount_style = "green" if row['total'] > 0 else "red"
            desc = row['description']
            # Truncate with ellipsis only if needed
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                desc = desc[:MAX_DESCRIPTION_LENGTH] + "..."
            table.add_row(
                str(idx),
                desc,
                str(row['cnt']),
                f"[{amount_style}]${row['total']:,.2f}[/{amount_style}]"
            )
        
        console.print(table)
        console.print()
        
        # Get user selection
        selection = console.input("[bold yellow]Enter # to assign (or 'q' to quit): [/bold yellow]")
        
        if selection.lower() == 'q':
            console.print("\n[dim]Exiting...[/dim]")
            break
        
        try:
            idx = int(selection) - 1
            if idx < 0 or idx >= len(todos):
                console.print("[red]Invalid selection[/red]")
                console.input("\nPress Enter to continue...")
                continue
        except ValueError:
            console.print("[red]Invalid input[/red]")
            console.input("\nPress Enter to continue...")
            continue
        
        selected = todos[idx]
        description = selected['description']
        
        # Enter sub-selection flow for individual transactions
        handle_transaction_detail_selection(description, entity)
        # After returning from sub-selection, loop back to main list (it will be refreshed)
