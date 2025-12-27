"""
Project Budget Status Report - Baseline vs Actual comparison
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

def show_budget_status(project_code):
    """Display budget status (baseline vs actual) for a specific project"""
    
    # Get project info
    project = execute_query("""
        SELECT 
            p.project_code, 
            p.project_name, 
            p.client_code,
            c.name as client_name,
            p.client_po,
            p.project_desc
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, [project_code])
    
    if not project:
        console.print(f"[red]Project '{project_code}' not found[/red]")
        return
    
    proj = project[0]
    
    # Display header
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Project Budget Status[/bold cyan]")
    console.print(f"[bold cyan]   {project_code}[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"[bold]Project:[/bold]     {proj['client_name']} - {proj['project_name']}")
    console.print(f"[bold]Client:[/bold]      {proj['client_name']} ({proj['client_code']})")
    if proj['client_po']:
        console.print(f"[bold]Job No.:[/bold]     {proj['client_po']}")
    if proj['project_desc']:
        console.print(f"[bold]Description:[/bold] {proj['project_desc'][:60]}")
    
    # Get budget by task
    budget_data = execute_query("""
        WITH baseline_totals AS (
            SELECT 
                b.task_no,
                b.sub_task_no,
                SUM(COALESCE(b.base_units, 0) * COALESCE(b.base_rate, 0) 
                  + COALESCE(b.base_miles, 0) * COALESCE(b.base_miles_rate, 0) 
                  + COALESCE(b.base_expense, 0)) as baseline
            FROM bgs.baseline b
            WHERE b.project_code = %s
            GROUP BY b.task_no, b.sub_task_no
        ),
        actual_totals AS (
            SELECT 
                ts.task_no,
                ts.sub_task_no,
                SUM(COALESCE(ts.ts_units, 0) * COALESCE(bl.base_rate, 0) 
                  + COALESCE(ts.ts_mileage, 0) * COALESCE(bl.base_miles_rate, 0) 
                  + COALESCE(ts.ts_expense, 0)) as actual
            FROM bgs.timesheet ts
            LEFT JOIN bgs.baseline bl ON bl.project_code = ts.project_code 
                AND bl.task_no = ts.task_no 
                AND bl.sub_task_no = ts.sub_task_no 
                AND bl.res_id = ts.res_id
            WHERE ts.project_code = %s
            GROUP BY ts.task_no, ts.sub_task_no
        )
        SELECT 
            COALESCE(b.task_no, a.task_no) as task_no,
            COALESCE(b.sub_task_no, a.sub_task_no) as sub_task_no,
            COALESCE(t.task_name, '') as task_name,
            COALESCE(b.baseline, 0) as baseline,
            COALESCE(a.actual, 0) as actual,
            COALESCE(b.baseline, 0) - COALESCE(a.actual, 0) as remaining
        FROM baseline_totals b
        FULL OUTER JOIN actual_totals a ON b.task_no = a.task_no AND b.sub_task_no = a.sub_task_no
        LEFT JOIN bgs.task t ON t.project_code = %s 
            AND t.task_no = COALESCE(b.task_no, a.task_no) 
            AND t.sub_task_no = COALESCE(b.sub_task_no, a.sub_task_no)
        ORDER BY COALESCE(b.task_no, a.task_no), COALESCE(b.sub_task_no, a.sub_task_no)
    """, [project_code, project_code, project_code])
    
    if not budget_data:
        console.print(f"\n[yellow]No budget data found for project '{project_code}'[/yellow]")
        return
    
    # Display budget table
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Baseline vs Actual by Task[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task", style="cyan")
    table.add_column("Sub", style="cyan")
    table.add_column("Task Name", style="white")
    table.add_column("Baseline", justify="right", style="white")
    table.add_column("Actual", justify="right", style="yellow")
    table.add_column("Remaining", justify="right")
    
    total_baseline = 0
    total_actual = 0
    
    for row in budget_data:
        baseline = float(row['baseline'] or 0)
        actual = float(row['actual'] or 0)
        remaining = float(row['remaining'] or 0)
        
        total_baseline += baseline
        total_actual += actual
        
        remaining_color = "green" if remaining >= 0 else "red"
        
        table.add_row(
            row['task_no'],
            row['sub_task_no'],
            (row['task_name'] or '')[:24],
            f"${baseline:,.0f}",
            f"${actual:,.0f}",
            f"[{remaining_color}]${remaining:,.0f}[/{remaining_color}]"
        )
    
    console.print(table)
    
    # Display totals
    total_remaining = total_baseline - total_actual
    budget_used_pct = (total_actual / total_baseline * 100) if total_baseline > 0 else 0
    
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Project Totals[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"   Total Baseline:     ${total_baseline:>12,.2f}")
    console.print(f"   Total Actual:       ${total_actual:>12,.2f}")
    
    remaining_color = "green" if total_remaining >= 0 else "red"
    console.print(f"   [{remaining_color}]Remaining:          ${total_remaining:>12,.2f}[/{remaining_color}]")
    
    pct_color = "green" if budget_used_pct <= 100 else "red"
    console.print(f"   [{pct_color}]Budget Used:         {budget_used_pct:>12.1f}%[/{pct_color}]")
    
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")

@click.command()
@click.argument('project_code', required=False)
def budget(project_code):
    """Display project budget status (baseline vs actual)"""
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
    
    show_budget_status(project_code)
