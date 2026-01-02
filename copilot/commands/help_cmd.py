"""
Global help command for Copilot CLI.

Provides overview of all modules and can display complete cheat sheets.
"""

import click
from copilot.commands.help_utils import (
    print_header, 
    print_module_overview,
    console
)


@click.command('help')
@click.option('--all', 'show_all', is_flag=True, help='Show complete cheat sheet for all modules')
def help_cmd(show_all):
    """Show help and available commands for Copilot CLI"""
    
    print_header("COPILOT CLI HELP")
    
    if show_all:
        # Import and call each module's help function
        console.print("[bold yellow]Complete Help Reference for All Modules[/bold yellow]\n")
        
        # Import all help functions
        try:
            from copilot.commands.lease_cmd import show_lease_help
            from copilot.commands.allocate_cmd import show_allocate_help
            from copilot.commands.gl_cmd import show_gl_help
            from copilot.commands.staging_cmd import show_staging_help
            from copilot.commands.import_cmd import show_import_help
            from copilot.commands.project_cmd import show_project_help
            
            # Display all helps with separators
            modules = [
                ("LEASE MANAGEMENT", show_lease_help),
                ("TRANSACTION ALLOCATION", show_allocate_help),
                ("GL ACCOUNT CODES", show_gl_help),
                ("BANK STAGING", show_staging_help),
                ("IMPORT", show_import_help),
                ("BGS PROJECT MANAGEMENT", show_project_help),
            ]
            
            for i, (title, help_func) in enumerate(modules):
                if i > 0:
                    console.print("\n" + "=" * 79 + "\n")
                help_func()
                
        except ImportError as e:
            console.print(f"[yellow]Warning: Could not load all help modules: {e}[/yellow]")
    else:
        # Show module overview
        modules = [
            ("lease", "Rental property and lease management"),
            ("mortgage", "Mortgage tracking and payment analysis"),
            ("property", "Property investment analysis and portfolio management"),
            ("allocate", "Transaction allocation and pattern matching"),
            ("gl", "General ledger and accounting"),
            ("staging", "Bank transaction staging and review"),
            ("import", "Import bank statements and data"),
            ("project", "BGS project management and tracking"),
        ]
        
        print_module_overview(modules)
