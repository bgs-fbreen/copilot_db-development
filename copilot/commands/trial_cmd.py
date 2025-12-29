import click
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from copilot.db import execute_query, execute_command, get_connection

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.group('trial')
def trial_cmd():
    """Manage trial entries (pre-journal review)"""
    pass


@trial_cmd.command('generate')
@click.option('--entity', '-e', help='Filter by entity')
@click.option('--date-from', '-f', help='Start date (YYYY-MM-DD)')
@click.option('--date-to', '-t', help='End date (YYYY-MM-DD)')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without creating')
def trial_generate(entity, date_from, date_to, dry_run):
    """Generate trial entries from staged transactions"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Generate Trial Entries[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Check for TODOs first
    todo_query = """
        SELECT COUNT(*) as count FROM acc.bank_staging 
        WHERE gl_account_code = 'TODO'
    """
    params = []
    if entity:
        todo_query += " AND entity = %s"
        params.append(entity)
    
    todos = execute_query(todo_query, tuple(params) if params else None)
    if todos and todos[0]['count'] > 0:
        console.print(f"[yellow]⚠ Warning: {todos[0]['count']} transactions still have TODO status[/yellow]")
        console.print("[dim]These will be skipped. Use 'copilot staging todos' to review.[/dim]\n")
    
    if dry_run:
        # Show what would be generated
        preview_query = """
            SELECT 
                s.entity,
                COUNT(*) as eligible,
                SUM(ABS(s.amount)) as total_amount
            FROM acc.bank_staging s
            WHERE s.gl_account_code != 'TODO'
              AND NOT EXISTS (SELECT 1 FROM acc.trial_entry t WHERE t.source_staging_id = s.id)
        """
        if entity:
            preview_query += " AND s.entity = %s"
        preview_query += " GROUP BY s.entity"
        
        preview = execute_query(preview_query, (entity,) if entity else None)
        
        if not preview:
            console.print("[yellow]No eligible transactions to generate[/yellow]")
            return
        
        console.print("[bold]Would generate:[/bold]\n")
        for row in preview:
            console.print(f"  Entity [cyan]{row['entity']}[/cyan]: {row['eligible']} entries (${row['total_amount']:,.2f})")
        
        console.print("\n[dim]Run without --dry-run to create entries[/dim]")
        return
    
    # Generate entries
    result = execute_query(
        "SELECT * FROM acc.fn_generate_trial_entries(%s, %s, %s)",
        (entity, date_from, date_to)
    )
    
    if result:
        created = result[0]['entries_created']
        skipped = result[0]['entries_skipped']
        console.print(f"[green]✓ Created {created} trial entries[/green]")
        if skipped:
            console.print(f"[yellow]  Skipped {skipped} (TODO or already processed)[/yellow]")


@trial_cmd.command('validate')
def trial_validate():
    """Validate pending trial entries"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Validate Trial Entries[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    result = execute_query("SELECT * FROM acc.fn_validate_trial_entries()")
    
    if result:
        validated = result[0]['validated']
        errors = result[0]['errors']
        console.print(f"[green]✓ Validated: {validated} entries ready to post[/green]")
        if errors:
            console.print(f"[red]✗ Errors: {errors} entries have issues[/red]")
            console.print("[dim]Use 'copilot trial errors' to review[/dim]")


@trial_cmd.command('list')
@click.option('--entity', '-e', help='Filter by entity')
@click.option('--status', '-s', type=click.Choice(['pending', 'balanced', 'error', 'posted', 'all']), default='all')
@click.option('--limit', '-l', default=50, help='Number of records to show')
def trial_list(entity, status, limit):
    """List trial entries"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Trial Entries[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    conditions = []
    params = []
    
    if entity:
        conditions.append("entity = %s")
        params.append(entity)
    if status and status != 'all':
        conditions.append("status = %s")
        params.append(status)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    
    query = f"""
        SELECT 
            id,
            entry_date,
            SUBSTRING(description, 1, 35) as description,
            entity,
            total_debit,
            total_credit,
            balance_status,
            status
        FROM acc.vw_trial_entry_balance
        {where_clause}
        ORDER BY entry_date DESC, id DESC
        LIMIT %s
    """
    
    results = execute_query(query, tuple(params))
    
    if not results:
        console.print("[yellow]No trial entries found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Entity", style="white")
    table.add_column("Debit", justify="right", style="red")
    table.add_column("Credit", justify="right", style="green")
    table.add_column("Balance", style="yellow")
    table.add_column("Status")
    
    for row in results:
        balance_style = "green" if row['balance_status'] == 'BALANCED' else "red bold"
        status_style = "green" if row['status'] == 'balanced' else ("red" if row['status'] == 'error' else "yellow")
        table.add_row(
            str(row['id']),
            str(row['entry_date']),
            row['description'] or '-',
            row['entity'],
            f"{row['total_debit'] or 0:,.2f}",
            f"{row['total_credit'] or 0:,.2f}",
            f"[{balance_style}]{row['balance_status']}[/{balance_style}]",
            f"[{status_style}]{row['status']}[/{status_style}]"
        )
    
    console.print(table)


@trial_cmd.command('errors')
@click.option('--entity', '-e', help='Filter by entity')
def trial_errors(entity):
    """Show trial entries with errors"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Trial Entry Errors[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "AND entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT 
            id,
            entry_date,
            description,
            entity,
            error_message
        FROM acc.trial_entry
        WHERE status = 'error'
        {entity_filter}
        ORDER BY entry_date DESC
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[green]✓ No errors found![/green]")
        return
    
    console.print(f"[red]Found {len(results)} entries with errors[/red]\n")
    
    for row in results:
        console.print(Panel(
            f"[white]{row['description'][:60]}[/white]\n"
            f"[red]Error: {row['error_message']}[/red]",
            title=f"[cyan]ID {row['id']}[/cyan] | {row['entry_date']} | {row['entity']}",
            border_style="red"
        ))


@trial_cmd.command('match-transfers')
@click.option('--entity', '-e', help='Filter by entity')
def trial_match_transfers(entity):
    """Match internal transfer pairs"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Match Transfer Pairs[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    result = execute_query("SELECT acc.fn_match_transfer_pairs(%s) as matched", (entity,))
    
    if result:
        matched = result[0]['matched']
        if matched > 0:
            console.print(f"[green]✓ Matched {matched} transfer pairs[/green]")
        else:
            console.print("[yellow]No new transfer pairs found to match[/yellow]")
    
    # Show remaining unmatched
    unmatched = execute_query("SELECT COUNT(*) as count FROM acc.vw_unmatched_transfers")
    if unmatched and unmatched[0]['count'] > 0:
        console.print(f"\n[dim]{unmatched[0]['count']} transfers still unmatched[/dim]")
        console.print("[dim]Use 'copilot staging transfers' to review[/dim]")


@trial_cmd.command('summary')
@click.option('--entity', '-e', help='Filter by entity')
def trial_summary(entity):
    """Show trial entry summary by status"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Trial Entry Summary[/bold cyan]")
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
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'balanced') as balanced,
            COUNT(*) FILTER (WHERE status = 'error') as errors,
            COUNT(*) FILTER (WHERE status = 'posted') as posted,
            SUM(total_debit) as total_amount
        FROM acc.vw_trial_entry_balance
        {entity_filter}
        GROUP BY entity
        ORDER BY entity
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No trial entries[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Entity", style="white")
    table.add_column("Total", justify="right")
    table.add_column("Pending", justify="right", style="yellow")
    table.add_column("Balanced", justify="right", style="green")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Posted", justify="right", style="cyan")
    table.add_column("Amount", justify="right")
    
    for row in results:
        table.add_row(
            row['entity'],
            str(row['total']),
            str(row['pending']),
            str(row['balanced']),
            str(row['errors']),
            str(row['posted']),
            f"${row['total_amount'] or 0:,.2f}"
        )
    
    console.print(table)


@trial_cmd.command('ready')
@click.option('--entity', '-e', help='Filter by entity')
def trial_ready(entity):
    """Show entries ready to post to journal"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Ready to Post[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT * FROM acc.vw_trial_ready_to_post
        {entity_filter}
        ORDER BY entry_date, id
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No entries ready to post[/yellow]")
        console.print("[dim]Run 'copilot trial validate' to check pending entries[/dim]")
        return
    
    console.print(f"[green]{len(results)} entries ready to post to journal[/green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Entity", style="white")
    table.add_column("Amount", justify="right", style="green")
    
    for row in results:
        table.add_row(
            str(row['id']),
            str(row['entry_date']),
            row['description'][:40] if row['description'] else '-',
            row['entity'],
            f"${row['total_debit']:,.2f}"
        )
    
    console.print(table)
    console.print(f"\n[dim]Use 'copilot journal post' to post these entries[/dim]")
