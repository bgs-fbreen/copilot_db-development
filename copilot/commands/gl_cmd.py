"""GL account code management commands"""
import click
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query

console = Console()


@click.group('gl')
def gl_cmd():
    """GL account code commands"""
    pass


@gl_cmd.command('list')
@click.option('--type', '-t', 'account_type', help='Filter by account type (expense, income, asset, etc.)')
def gl_list(account_type):
    """List available GL account codes"""
    
    if account_type:
        query = """
            SELECT code, name, account_type
            FROM acc.bank_account
            WHERE status = 'active'
              AND account_type ILIKE %s
            ORDER BY code
        """
        codes = execute_query(query, (f'%{account_type}%',))
    else:
        query = """
            SELECT code, name, account_type
            FROM acc.bank_account
            WHERE status = 'active'
            ORDER BY account_type, code
        """
        codes = execute_query(query)
    
    if not codes:
        console.print("[yellow]No GL account codes found[/yellow]")
        return
    
    table = Table(title="GL Account Codes", show_header=True, header_style="bold magenta")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    
    for code in codes:
        table.add_row(code['code'], code['name'], code['account_type'])
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(codes)} codes[/dim]")


@gl_cmd.command('search')
def gl_search():
    """Interactive GL code search - search multiple times without restarting"""
    
    console.print("\n[bold cyan]GL Account Code Search (type 'q' to quit)[/bold cyan]")
    console.print("[bold cyan]─────────────────────────────────────────[/bold cyan]\n")
    
    while True:
        search_term = console.input("[bold yellow]Search: [/bold yellow]").strip()
        
        # Check for quit
        if search_term.lower() == 'q':
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        # Empty search or 'all' shows all codes
        if not search_term or search_term.lower() == 'all':
            query = """
                SELECT code, name, account_type
                FROM acc.bank_account
                WHERE status = 'active'
                ORDER BY account_type, code
            """
            codes = execute_query(query)
        else:
            # Search by code or name
            query = """
                SELECT code, name, account_type
                FROM acc.bank_account
                WHERE status = 'active'
                  AND (code ILIKE %s OR name ILIKE %s)
                ORDER BY code
            """
            search = f'%{search_term}%'
            codes = execute_query(query, (search, search))
        
        console.print()  # Blank line before table
        
        if not codes:
            console.print(f"[yellow]No GL codes found matching '{search_term}'[/yellow]\n")
            continue
        
        # Display results in table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Code", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Type", style="green")
        
        for code in codes:
            table.add_row(code['code'], code['name'], code['account_type'])
        
        console.print(table)
        console.print()
