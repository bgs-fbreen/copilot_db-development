import click
import os
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query, execute_command

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

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
            row['match_method'] or '-'
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
    
    for row in results:
        amount_style = "green" if row['amount'] > 0 else "red"
        table.add_row(
            str(row['id']),
            row['entity'],
            row['source_account_code'],
            str(row['normalized_date']),
            row['description'][:50],
            f"[{amount_style}]{row['amount']:,.2f}[/{amount_style}]"
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
