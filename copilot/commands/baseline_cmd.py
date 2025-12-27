"""
Project Baseline Report - displays budget/baseline for a project
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from copilot.db import execute_query
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def show_project_list():
    """Display list of active projects and return selected project code"""
    projects = execute_query("""
        SELECT 
            p.project_code,
            p.client_code,
            p.project_name
        FROM bgs.project p
        WHERE p.status = 'active'
        ORDER BY p.project_code
    """)
    
    if not projects:
        console.print("[yellow]No active projects found[/yellow]")
        return None
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Client", style="cyan")
    table.add_column("Project Name", style="white")
    table.add_column("Project Code", style="yellow")
    
    for proj in projects:
        table.add_row(
            proj['client_code'],
            (proj['project_name'] or '')[:28],
            proj['project_code']
        )
    
    console.print(table)
    console.print()
    
    project_code = Prompt.ask("[yellow]Project Code[/yellow]")
    return project_code if project_code else None

def show_baseline(project_code):
    """Display baseline for a specific project"""
    
    # Get project info
    project = execute_query("""
        SELECT p.project_code, p.project_name, c.name as client_name
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, [project_code])
    
    if not project:
        console.print(f"[red]Project '{project_code}' not found[/red]")
        return
    
    proj = project[0]
    
    # Get baseline data
    baseline = execute_query("""
        SELECT DISTINCT
            b.task_no,
            b.sub_task_no,
            b.res_id,
            COALESCE(t.task_name, '') as task_name,
            COALESCE(t.sub_task_name, 'na') as sub_task_name,
            COALESCE(b.base_units, 0) as base_units,
            COALESCE(b.base_rate, 0) as base_rate,
            COALESCE(b.base_miles, 0) as base_miles,
            COALESCE(b.base_miles_rate, 0) as base_miles_rate,
            COALESCE(b.base_expense, 0) as base_expense
        FROM bgs.baseline b
        LEFT JOIN bgs.task t
            ON t.project_code = b.project_code
            AND t.task_no = b.task_no
            AND t.sub_task_no = b.sub_task_no
        WHERE b.project_code = %s
        ORDER BY b.task_no, b.sub_task_no, b.res_id
    """, [project_code])
    
    if not baseline:
        console.print(f"[yellow]No baseline found for project '{project_code}'[/yellow]")
        return
    
    # Display header
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Project Baseline[/bold cyan]")
    console.print(f"[bold cyan]   {project_code} - {proj['client_name']}[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task", style="cyan")
    table.add_column("Sub", style="cyan")
    table.add_column("Res", style="white")
    table.add_column("Task Name", style="white")
    table.add_column("SubName", style="dim")
    table.add_column("Hrs", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Labor", justify="right", style="green")
    table.add_column("Mi", justify="right")
    table.add_column("MiRate", justify="right")
    table.add_column("Miles", justify="right", style="green")
    table.add_column("Exp", justify="right", style="yellow")
    table.add_column("Total", justify="right", style="bold white")
    
    grand_total = 0
    
    for row in baseline:
        units = float(row['base_units'])
        rate = float(row['base_rate'])
        miles = float(row['base_miles'])
        miles_rate = float(row['base_miles_rate'])
        expense = float(row['base_expense'])
        
        labor = units * rate
        miles_cost = miles * miles_rate
        total = labor + miles_cost + expense
        grand_total += total
        
        sub_name = row['sub_task_name'][:12] if row['sub_task_name'] else 'na'
        
        table.add_row(
            row['task_no'],
            row['sub_task_no'],
            row['res_id'],
            (row['task_name'] or '')[:24],
            sub_name,
            f"{units:.2f}",
            f"{rate:.2f}",
            f"${labor:,.0f}",
            f"{miles:.2f}",
            f"{miles_rate:.2f}",
            f"${miles_cost:,.0f}",
            f"${expense:,.0f}",
            f"${total:,.0f}"
        )
    
    console.print(table)
    
    # Display total
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"   [bold]TOTAL BASELINE{' ' * 22} ${grand_total:>12,.2f}[/bold]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"\n[dim]Total includes all baseline entries (including change orders).[/dim]\n")

@click.command()
@click.argument('project_code', required=False)
def baseline(project_code):
    """Display project baseline/budget report"""
    clear_screen()
    
    if not project_code:
        # Interactive mode - show project list
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   Select Project (Ctrl-C to exit)[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        project_code = show_project_list()
        if not project_code:
            return
        
        clear_screen()
    
    show_baseline(project_code)
