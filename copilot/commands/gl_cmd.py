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
@click.argument('term')
def gl_search(term):
    """Search GL codes by name or code"""
    
    query = """
        SELECT code, name, account_type
        FROM acc.bank_account
        WHERE status = 'active'
          AND (code ILIKE %s OR name ILIKE %s)
        ORDER BY code
    """
    search = f'%{term}%'
    codes = execute_query(query, (search, search))
    
    if not codes:
        console.print(f"[yellow]No GL codes found matching '{term}'[/yellow]")
        return
    
    table = Table(title=f"GL Codes matching '{term}'", show_header=True, header_style="bold magenta")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    
    for code in codes:
        table.add_row(code['code'], code['name'], code['account_type'])
    
    console.print(table)
    console.print(f"\n[dim]Found {len(codes)} matches[/dim]")
