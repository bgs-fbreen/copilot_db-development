import click
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from copilot.db import execute_query, execute_command

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.group('journal')
def journal_cmd():
    """Manage journal entries (final accounting records)"""
    pass


@journal_cmd.command('post')
@click.option('--entity', '-e', help='Filter by entity')
@click.option('--dry-run', is_flag=True, help='Show what would be posted without posting')
@click.option('--posted-by', '-p', default='cli', help='User/system posting the entries')
def journal_post(entity, dry_run, posted_by):
    """Post validated trial entries to journal"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Post to Journal[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Check what's ready to post
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE entity = %s"
        params.append(entity)
    
    preview_query = f"""
        SELECT 
            entity,
            COUNT(*) as ready_count,
            SUM(total_debit) as total_amount
        FROM acc.vw_trial_ready_to_post
        {entity_filter}
        GROUP BY entity
    """
    
    preview = execute_query(preview_query, tuple(params) if params else None)
    
    if not preview:
        console.print("[yellow]No entries ready to post[/yellow]")
        console.print("[dim]Run 'copilot trial validate' to check pending entries[/dim]")
        return
    
    console.print("[bold]Ready to post:[/bold]\n")
    for row in preview:
        console.print(f"  Entity [cyan]{row['entity']}[/cyan]: {row['ready_count']} entries (${row['total_amount']:,.2f})")
    
    if dry_run:
        console.print("\n[dim]Dry run - no entries posted. Remove --dry-run to post.[/dim]")
        return
    
    # Confirm
    if not click.confirm("\nPost these entries to journal?"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Post entries
    result = execute_query(
        "SELECT * FROM acc.fn_post_to_journal(%s, %s)",
        (entity, posted_by)
    )
    
    if result:
        posted = result[0]['entries_posted']
        skipped = result[0]['entries_skipped']
        console.print(f"\n[green]✓ Posted {posted} entries to journal[/green]")
        if skipped:
            console.print(f"[yellow]  Skipped {skipped} entries[/yellow]")


@journal_cmd.command('list')
@click.option('--entity', '-e', help='Filter by entity')
@click.option('--date-from', '-f', help='Start date (YYYY-MM-DD)')
@click.option('--date-to', '-t', help='End date (YYYY-MM-DD)')
@click.option('--limit', '-l', default=50, help='Number of records to show')
def journal_list(entity, date_from, date_to, limit):
    """List journal entries"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Journal Entries[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    conditions = []
    params = []
    
    if entity:
        conditions.append("entity = %s")
        params.append(entity)
    if date_from:
        conditions.append("entry_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("entry_date <= %s")
        params.append(date_to)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    
    query = f"""
        SELECT 
            j.id,
            j.entry_date,
            SUBSTRING(j.description, 1, 35) as description,
            j.entity,
            j.reference_num,
            j.check_number,
            b.total_debit,
            b.total_credit,
            b.balance_status,
            CASE 
                WHEN j.reversed_by IS NOT NULL THEN 'REVERSED'
                WHEN j.reversal_of IS NOT NULL THEN 'REVERSAL'
                ELSE 'ACTIVE'
            END as status
        FROM acc.journal j
        JOIN acc.vw_journal_entry_balance b ON b.id = j.id
        {where_clause}
        ORDER BY j.entry_date DESC, j.id DESC
        LIMIT %s
    """
    
    results = execute_query(query, tuple(params))
    
    if not results:
        console.print("[yellow]No journal entries found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Entity", style="white")
    table.add_column("Ref", style="dim")
    table.add_column("Check #", style="cyan")
    table.add_column("Debit", justify="right", style="red")
    table.add_column("Credit", justify="right", style="green")
    table.add_column("Status")
    
    for row in results:
        status_style = "green" if row['status'] == 'ACTIVE' else ("red" if row['status'] == 'REVERSED' else "yellow")
        table.add_row(
            str(row['id']),
            str(row['entry_date']),
            row['description'] or '-',
            row['entity'],
            row['reference_num'] or '-',
            row['check_number'] or '-',
            f"{row['total_debit'] or 0:,.2f}",
            f"{row['total_credit'] or 0:,.2f}",
            f"[{status_style}]{row['status']}[/{status_style}]"
        )
    
    console.print(table)


@journal_cmd.command('view')
@click.argument('journal_id', type=int)
def journal_view(journal_id):
    """View journal entry details with lines"""
    
    clear_screen()
    
    # Get entry header
    entry = execute_query("""
        SELECT j.*, b.total_debit, b.total_credit, b.balance_status
        FROM acc.journal j
        JOIN acc.vw_journal_entry_balance b ON b.id = j.id
        WHERE j.id = %s
    """, (journal_id,))
    
    if not entry:
        console.print(f"[red]Journal entry {journal_id} not found[/red]")
        return
    
    entry = entry[0]
    
    # Determine status
    if entry['reversed_by']:
        status = f"[red]REVERSED by #{entry['reversed_by']}[/red]"
    elif entry['reversal_of']:
        status = f"[yellow]REVERSAL of #{entry['reversal_of']}[/yellow]"
    else:
        status = "[green]ACTIVE[/green]"
    
    console.print(f"\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Journal Entry #{journal_id}[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"  Date:        [cyan]{entry['entry_date']}[/cyan]")
    console.print(f"  Entity:      {entry['entity']}")
    console.print(f"  Description: {entry['description'] or '-'}")
    console.print(f"  Reference:   {entry['reference_num'] or '-'}")
    console.print(f"  Check #:     {entry['check_number'] or '-'}")
    console.print(f"  Posted:      {entry['posted_at']} by {entry['posted_by'] or 'system'}")
    console.print(f"  Status:      {status}")
    console.print(f"  Balance:     [{('green' if entry['balance_status'] == 'BALANCED' else 'red')}]{entry['balance_status']}[/]")
    
    # Get lines
    lines = execute_query("""
        SELECT line_num, gl_account_code, debit, credit, memo
        FROM acc.journal_line
        WHERE journal_id = %s
        ORDER BY line_num
    """, (journal_id,))
    
    console.print("\n[bold]Entry Lines:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", justify="right")
    table.add_column("GL Account", style="cyan")
    table.add_column("Debit", justify="right", style="red")
    table.add_column("Credit", justify="right", style="green")
    table.add_column("Memo", style="dim")
    
    for line in lines:
        table.add_row(
            str(line['line_num']),
            line['gl_account_code'],
            f"{line['debit']:,.2f}" if line['debit'] else "",
            f"{line['credit']:,.2f}" if line['credit'] else "",
            line['memo'][:30] if line['memo'] else ""
        )
    
    console.print(table)
    console.print(f"\n  [bold]Total:[/bold]  Debit: [red]{entry['total_debit']:,.2f}[/red]  Credit: [green]{entry['total_credit']:,.2f}[/green]")


@journal_cmd.command('reverse')
@click.argument('journal_id', type=int)
@click.option('--reason', '-r', default='Manual reversal', help='Reason for reversal')
@click.option('--reversed-by', '-b', default='cli', help='User creating the reversal')
def journal_reverse(journal_id, reason, reversed_by):
    """Create a reversal entry for a journal entry"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Reverse Journal Entry[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Get entry to reverse
    entry = execute_query("""
        SELECT j.*, b.total_debit
        FROM acc.journal j
        JOIN acc.vw_journal_entry_balance b ON b.id = j.id
        WHERE j.id = %s
    """, (journal_id,))
    
    if not entry:
        console.print(f"[red]Journal entry {journal_id} not found[/red]")
        return
    
    entry = entry[0]
    
    if entry['reversed_by']:
        console.print(f"[red]Entry {journal_id} has already been reversed by entry #{entry['reversed_by']}[/red]")
        return
    
    console.print(f"  Entry:       #{journal_id}")
    console.print(f"  Date:        {entry['entry_date']}")
    console.print(f"  Description: {entry['description'] or '-'}")
    console.print(f"  Amount:      ${entry['total_debit']:,.2f}")
    console.print(f"  Reason:      {reason}")
    
    if not click.confirm("\nCreate reversal entry?"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    try:
        result = execute_query(
            "SELECT acc.fn_reverse_journal_entry(%s, %s, %s) as reversal_id",
            (journal_id, reason, reversed_by)
        )
        
        if result:
            reversal_id = result[0]['reversal_id']
            console.print(f"\n[green]✓ Created reversal entry #{reversal_id}[/green]")
            console.print(f"[dim]Original entry #{journal_id} is now marked as reversed[/dim]")
        else:
            console.print(f"[red]Error: Failed to create reversal entry[/red]")
    except Exception as e:
        console.print(f"[red]Error creating reversal: {e}[/red]")


@journal_cmd.command('balances')
@click.option('--entity', '-e', help='Filter by entity')
def journal_balances(entity):
    """Show GL account balances"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   GL Account Balances[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT * FROM acc.vw_gl_balances
        {entity_filter}
        ORDER BY gl_account_code
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No balances found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("GL Account", style="cyan")
    table.add_column("Entity", style="white")
    table.add_column("Total Debit", justify="right", style="red")
    table.add_column("Total Credit", justify="right", style="green")
    table.add_column("Balance", justify="right")
    
    total_debit = 0
    total_credit = 0
    
    for row in results:
        balance_style = "red" if row['balance'] > 0 else "green"
        table.add_row(
            row['gl_account_code'],
            row['entity'],
            f"{row['total_debit'] or 0:,.2f}",
            f"{row['total_credit'] or 0:,.2f}",
            f"[{balance_style}]{row['balance'] or 0:,.2f}[/{balance_style}]"
        )
        total_debit += row['total_debit'] or 0
        total_credit += row['total_credit'] or 0
    
    console.print(table)
    console.print(f"\n[bold]Totals:[/bold]  Debit: [red]{total_debit:,.2f}[/red]  Credit: [green]{total_credit:,.2f}[/green]")


@journal_cmd.command('trial-balance')
@click.option('--entity', '-e', help='Filter by entity')
def journal_trial_balance(entity):
    """Show trial balance report"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Trial Balance Report[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT * FROM acc.vw_trial_balance
        {entity_filter}
        ORDER BY gl_account_code
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No balances found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("GL Account", style="cyan")
    table.add_column("Entity", style="white")
    table.add_column("Debit Balance", justify="right", style="red")
    table.add_column("Credit Balance", justify="right", style="green")
    
    total_debit = 0
    total_credit = 0
    
    for row in results:
        table.add_row(
            row['gl_account_code'],
            row['entity'],
            f"{row['debit_balance']:,.2f}" if row['debit_balance'] else "",
            f"{row['credit_balance']:,.2f}" if row['credit_balance'] else ""
        )
        total_debit += row['debit_balance'] or 0
        total_credit += row['credit_balance'] or 0
    
    console.print(table)
    
    # Check if balanced
    difference = total_debit - total_credit
    if abs(difference) < 0.01:
        console.print(f"\n[green]✓ BALANCED[/green]  Debit: {total_debit:,.2f}  Credit: {total_credit:,.2f}")
    else:
        console.print(f"\n[red]✗ UNBALANCED[/red]  Debit: {total_debit:,.2f}  Credit: {total_credit:,.2f}  Difference: {difference:,.2f}")


@journal_cmd.command('summary')
@click.option('--entity', '-e', help='Filter by entity')
def journal_summary(entity):
    """Show journal summary statistics"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Journal Summary[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    params = []
    entity_filter = ""
    if entity:
        entity_filter = "WHERE j.entity = %s"
        params.append(entity)
    
    query = f"""
        SELECT 
            j.entity,
            COUNT(*) as total_entries,
            COUNT(*) FILTER (WHERE j.reversed_by IS NULL AND j.reversal_of IS NULL) as active,
            COUNT(*) FILTER (WHERE j.reversed_by IS NOT NULL) as reversed,
            COUNT(*) FILTER (WHERE j.reversal_of IS NOT NULL) as reversals,
            SUM(b.total_debit) FILTER (WHERE j.reversed_by IS NULL) as total_amount
        FROM acc.journal j
        JOIN acc.vw_journal_entry_balance b ON b.id = j.id
        {entity_filter}
        GROUP BY j.entity
        ORDER BY j.entity
    """
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No journal entries[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Entity", style="white")
    table.add_column("Total", justify="right")
    table.add_column("Active", justify="right", style="green")
    table.add_column("Reversed", justify="right", style="red")
    table.add_column("Reversals", justify="right", style="yellow")
    table.add_column("Amount", justify="right")
    
    for row in results:
        table.add_row(
            row['entity'],
            str(row['total_entries']),
            str(row['active']),
            str(row['reversed']),
            str(row['reversals']),
            f"${row['total_amount'] or 0:,.2f}"
        )
    
    console.print(table)
