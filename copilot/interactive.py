"""Interactive menu system for Copilot Accounting System"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from click.testing import CliRunner
import sys

console = Console()


def clear_screen():
    """Clear the terminal screen using Rich"""
    console.clear()


def pause():
    """Pause and wait for user to press Enter"""
    console.print("\n[dim]Press Enter to continue...[/dim]", end="")
    input()


def show_header(title):
    """Show a formatted header"""
    console.print(f"\n[bold cyan]{'═' * 51}[/bold cyan]")
    console.print(f"[bold cyan]   {title}[/bold cyan]")
    console.print(f"[bold cyan]{'═' * 51}[/bold cyan]\n")


def run_command(command_func, args=None):
    """Run a Click command programmatically"""
    runner = CliRunner()
    try:
        if args is None:
            args = []
        result = runner.invoke(command_func, args, catch_exceptions=False)
        if result.output:
            console.print(result.output)
        if result.exit_code != 0 and result.exception:
            console.print(f"[red]Error: {result.exception}[/red]")
        return result.exit_code == 0
    except Exception as e:
        console.print(f"[red]Error executing command: {str(e)}[/red]")
        return False


def show_main_menu():
    """Display the main menu"""
    clear_screen()
    show_header("Copilot Accounting System v0.1.0")
    console.print("   [dim]BGS | MHB (711pine, 905brown, 819helen)[/dim]\n")
    
    console.print("   1) Projects")
    console.print("   2) Clients")
    console.print("   3) Timesheets")
    console.print("   4) Invoices")
    console.print("   5) Accounts Receivable")
    console.print("   6) Reports")
    console.print("   7) Maintenance")
    console.print()
    console.print("   v) Version Info")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_projects_menu():
    """Display the Projects submenu"""
    clear_screen()
    show_header("Projects")
    
    console.print("   1) List Projects (active)")
    console.print("   2) List Projects (all)")
    console.print("   3) Create New Project")
    console.print("   4) Create Baseline")
    console.print("   5) Create Directories")
    console.print("   6) Delete Project")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_clients_menu():
    """Display the Clients submenu"""
    clear_screen()
    show_header("Clients")
    
    console.print("   1) List Clients")
    console.print("   2) Add New Client")
    console.print("   3) Edit Client")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_timesheets_menu():
    """Display the Timesheets submenu"""
    clear_screen()
    show_header("Timesheets")
    
    console.print("   1) Enter Time")
    console.print("   2) View Recent Entries")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_invoices_menu():
    """Display the Invoices submenu"""
    clear_screen()
    show_header("Invoices")
    
    console.print("   1) Create Invoice")
    console.print("   2) List Invoices")
    console.print("   3) Export Invoice")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_ar_menu():
    """Display the Accounts Receivable submenu"""
    clear_screen()
    show_header("Accounts Receivable")
    
    console.print("   1) AR Aging Report")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_reports_menu():
    """Display the Reports submenu"""
    clear_screen()
    show_header("Reports")
    
    console.print("   1) [dim](Coming Soon)[/dim]")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def show_maintenance_menu():
    """Display the Maintenance submenu"""
    clear_screen()
    show_header("Maintenance")
    
    console.print("   1) Cleanup")
    console.print("   2) Edit Data")
    console.print()
    console.print("   b) Back to Main Menu")
    console.print("   q) Quit")
    console.print(f"\n[dim]{'─' * 51}[/dim]")


def handle_projects_menu():
    """Handle Projects submenu interactions"""
    from copilot.commands import project, new
    
    while True:
        show_projects_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # List active projects
            run_command(project, ['list', '--status', 'active'])
            pause()
        elif choice == '2':
            # List all projects
            run_command(project, ['list'])
            pause()
        elif choice == '3':
            # Create new project
            run_command(new, [])
            pause()
        elif choice == '4':
            # Create baseline
            project_code = Prompt.ask("Enter project code")
            if project_code:
                run_command(project, ['create-baseline', project_code])
                pause()
        elif choice == '5':
            # Create directories
            project_code = Prompt.ask("Enter project code")
            if project_code:
                run_command(project, ['create-dirs', project_code])
                pause()
        elif choice == '6':
            # Delete project
            project_code = Prompt.ask("Enter project code to delete")
            if project_code:
                run_command(project, ['delete', project_code])
                pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_clients_menu():
    """Handle Clients submenu interactions"""
    from copilot.commands import client
    
    while True:
        show_clients_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # List clients
            run_command(client, ['list'])
            pause()
        elif choice == '2':
            # Add new client
            run_command(client, ['add'])
            pause()
        elif choice == '3':
            # Edit client
            client_code = Prompt.ask("Enter client code")
            if client_code:
                run_command(client, ['edit', client_code])
                pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_timesheets_menu():
    """Handle Timesheets submenu interactions"""
    from copilot.commands import timesheet
    
    while True:
        show_timesheets_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # Enter time
            run_command(timesheet, [])
            pause()
        elif choice == '2':
            # View recent entries (placeholder)
            console.print("\n[yellow]Feature coming soon: View recent timesheet entries[/yellow]")
            pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_invoices_menu():
    """Handle Invoices submenu interactions"""
    from copilot.commands import invoice
    
    while True:
        show_invoices_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # Create invoice
            run_command(invoice, ['create'])
            pause()
        elif choice == '2':
            # List invoices
            run_command(invoice, ['list'])
            pause()
        elif choice == '3':
            # Export invoice
            invoice_code = Prompt.ask("Enter invoice code")
            if invoice_code:
                run_command(invoice, ['export', invoice_code])
                pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_ar_menu():
    """Handle Accounts Receivable submenu interactions"""
    from copilot.commands import ar
    
    while True:
        show_ar_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # AR aging report
            run_command(ar, [])
            pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_reports_menu():
    """Handle Reports submenu interactions"""
    while True:
        show_reports_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            console.print("\n[yellow]Reports feature coming soon![/yellow]")
            pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def handle_maintenance_menu():
    """Handle Maintenance submenu interactions"""
    from copilot.commands import cleanup, edit
    
    while True:
        show_maintenance_menu()
        choice = Prompt.ask("Select option").strip().lower()
        
        if choice == 'q':
            return 'quit'
        elif choice == 'b':
            return 'back'
        elif choice == '1':
            # Cleanup
            run_command(cleanup, [])
            pause()
        elif choice == '2':
            # Edit data
            run_command(edit, [])
            pause()
        else:
            console.print("[yellow]Invalid option, please try again[/yellow]")
            pause()


def run_interactive_menu():
    """Main interactive menu loop"""
    from copilot.commands import version
    
    try:
        while True:
            show_main_menu()
            choice = Prompt.ask("Select option").strip().lower()
            
            if choice == 'q':
                if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                    clear_screen()
                    console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                    sys.exit(0)
            elif choice == 'v':
                run_command(version, [])
                pause()
            elif choice == '1':
                result = handle_projects_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '2':
                result = handle_clients_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '3':
                result = handle_timesheets_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '4':
                result = handle_invoices_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '5':
                result = handle_ar_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '6':
                result = handle_reports_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            elif choice == '7':
                result = handle_maintenance_menu()
                if result == 'quit':
                    if Confirm.ask("\n[yellow]Are you sure you want to quit?[/yellow]", default=False):
                        clear_screen()
                        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
                        sys.exit(0)
            else:
                console.print("[yellow]Invalid option, please try again[/yellow]")
                pause()
    
    except KeyboardInterrupt:
        clear_screen()
        console.print("\n[cyan]Thank you for using Copilot![/cyan]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        console.print("[yellow]Returning to main menu...[/yellow]")
        pause()
