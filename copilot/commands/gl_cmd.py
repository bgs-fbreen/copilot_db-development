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
            SELECT gl_account_code as code, description as name, account_type
            FROM acc.gl_accounts
            WHERE is_active = true
              AND account_type ILIKE %s
            ORDER BY gl_account_code
        """
        codes = execute_query(query, (f'%{account_type}%',))
    else:
        query = """
            SELECT gl_account_code as code, description as name, account_type
            FROM acc.gl_accounts
            WHERE is_active = true
            ORDER BY account_type, gl_account_code
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
                SELECT gl_account_code as code, description as name, account_type
                FROM acc.gl_accounts
                WHERE is_active = true
                ORDER BY account_type, gl_account_code
            """
            codes = execute_query(query)
        else:
            # Search by code or name
            query = """
                SELECT gl_account_code as code, description as name, account_type
                FROM acc.gl_accounts
                WHERE is_active = true
                  AND (gl_account_code ILIKE %s OR description ILIKE %s)
                ORDER BY gl_account_code
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


@gl_cmd.command('help')
def help_command():
    """Display comprehensive GL account code cheat sheet"""
    show_gl_help()


def show_gl_help():
    """Display GL account code help content"""
    from copilot.commands.help_utils import print_header, print_section, print_examples
    
    print_header("GL ACCOUNT CODE CHEAT SHEET")
    
    # List Commands
    list_commands = [
        ("list [--type]", "List all GL account codes"),
        ("", "  Filter by account type: expense, income, asset, liability, equity"),
    ]
    print_section("LIST COMMANDS", list_commands)
    
    # Search Commands
    search_commands = [
        ("search", "Interactive GL code search"),
        ("", "  Search by code or description, type 'q' to quit"),
    ]
    print_section("SEARCH COMMANDS", search_commands)
    
    # Common GL Account Types
    types_info = [
        ("expense", "Operating expenses (rent, utilities, supplies, etc.)"),
        ("income", "Revenue and income accounts"),
        ("asset", "Assets (cash, equipment, property, etc.)"),
        ("liability", "Liabilities (loans, payables, etc.)"),
        ("equity", "Owner's equity and retained earnings"),
    ]
    print_section("ACCOUNT TYPES", types_info)
    
    # Examples
    examples = [
        ("List all expense accounts",
         "copilot gl list --type expense"),
        
        ("List all accounts (no filter)",
         "copilot gl list"),
        
        ("Interactive search for specific code",
         "copilot gl search\n  Search: rent\n  [Shows all accounts containing 'rent']"),
        
        ("Search and quit",
         "copilot gl search\n  Search: utilities\n  Search: q"),
    ]
    print_examples("EXAMPLES", examples)

