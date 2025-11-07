"""
Timesheet entry command - matches your bash script workflow
"""
import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query, execute_insert
import os
from decimal import Decimal

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def should_quit(value):
    """Check if user wants to quit"""
    if isinstance(value, str) and value.lower() in ['quit', 'exit', 'q', '']:
        return True
    return False

@click.command()
@click.option('--project', '-p', help='Project code (e.g., tbls.25.1904)')
@click.option('--date', '-d', help='Work date (YYYY-MM-DD), default: today')
@click.option('--hours', '-h', type=float, help='Hours worked')
@click.option('--loop/--no-loop', default=True, help='Continue entering multiple timesheets')
def timesheet(project, date, hours, loop):
    """Enter time for BGS projects (replaces ts_entry.sh)"""
    
    # Clear screen at start
    clear_screen()
    
    # Loop for multiple entries
    while True:
        if not enter_timesheet(project, date, hours):
            break
        
        if not loop:
            break
        
        # Clear screen after each entry
        clear_screen()
        
        console.print("\n[bold cyan]Enter another timesheet?[/bold cyan]")
        if not click.confirm('', default=True):
            break
        
        # Clear again before next entry
        clear_screen()
        
        # Reset for next entry
        project = None
        date = None
        hours = None
    
    clear_screen()
    console.print("\n[bold green]✓ Timesheet entry session complete![/bold green]\n")

def enter_timesheet(project, date, hours):
    """Single timesheet entry"""
    
    # Show active projects with baseline info
    console.print("\n[bold cyan]Active BGS Projects:[/bold cyan]\n")
    
    projects = execute_query("""
        SELECT DISTINCT
            p.project_code,
            p.client_code,
            p.project_name,
            p.status
        FROM bgs.project p
        WHERE p.status = 'active'
        ORDER BY p.project_code DESC
    """)
    
    if not projects:
        console.print("[yellow]No active projects found.[/yellow]")
        return False
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project Code", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Project Name", style="white")
    
    for p in projects:
        table.add_row(
            p['project_code'],
            p['client_code'],
            (p['project_name'] or '')[:50]
        )
    
    console.print(table)
    console.print()
    
    # Get project code if not provided
    if not project:
        project = click.prompt('\nProject Code (or "quit" to exit)', type=str, default='')
        if should_quit(project):
            return False
    
    # Verify project exists
    proj_check = execute_query(
        "SELECT project_code, project_name FROM bgs.project WHERE project_code = %s",
        (project,)
    )
    
    if not proj_check:
        console.print(f"[red]Error: Project '{project}' not found[/red]")
        return False
    
    proj = proj_check[0]
    console.print(f"\n[green]Project:[/green] {proj['project_name']}")
    
    # Show tasks for this project
    tasks = execute_query("""
        SELECT DISTINCT task_no, sub_task_no, task_name
        FROM bgs.task
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project,))
    
    if tasks:
        console.print("\n[cyan]Tasks:[/cyan]")
        for t in tasks[:10]:  # Show first 10
            console.print(f"  {t['task_no']} / {t['sub_task_no']} - {t['task_name']}")
    
    # Get yr_mon (yymm format)
    if not date:
        date = click.prompt('\nWork Date (YYYY-MM-DD)', 
                           default=datetime.now().strftime('%Y-%m-%d'))
        if should_quit(date):
            return False
    
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        yr_mon = date_obj.strftime('%y%m')
    except ValueError:
        console.print(f"[red]Invalid date format: {date}[/red]")
        return False
    
    # Get task info
    task_no = click.prompt('\nTask (e.g., T01, T01:CH01)', type=str)
    if should_quit(task_no):
        return False
    
    sub_task_no = click.prompt('SubTask (e.g., S01, na)', default='na', type=str)
    if should_quit(sub_task_no):
        return False
    
    # Get resource
    resources = execute_query("SELECT res_id, res_name FROM bgs.resource ORDER BY res_id")
    console.print("\n[cyan]Available Resources:[/cyan]")
    for r in resources:
        console.print(f"  {r['res_id']} - {r['res_name']}")
    
    res_id = click.prompt('\nResource ID', default='F.Breen', type=str)
    if should_quit(res_id):
        return False
    
    # Get hours
    if not hours:
        hours_str = click.prompt('Hours', type=str)
        if should_quit(hours_str):
            return False
        try:
            hours = float(hours_str)
        except ValueError:
            console.print(f"[red]Invalid hours: {hours_str}[/red]")
            return False
    
    # Get mileage and expenses
    mileage_str = click.prompt('Mileage', default='0.0', type=str)
    if should_quit(mileage_str):
        return False
    try:
        mileage = float(mileage_str)
    except ValueError:
        mileage = 0.0
    
    expense_str = click.prompt('Expense Amount', default='0.0', type=str)
    if should_quit(expense_str):
        return False
    try:
        expense = float(expense_str)
    except ValueError:
        expense = 0.0
    
    # Get description
    description = click.prompt('Description')
    if should_quit(description):
        return False
    
    # Get subject for org-mode heading
    subject = click.prompt('Subject (for org-mode heading)', default=description)
    if should_quit(subject):
        return False
    
    # Get rate from baseline
    rate_check = execute_query("""
        SELECT base_rate 
        FROM bgs.baseline 
        WHERE project_code = %s 
          AND task_no = %s 
          AND res_id = %s
        LIMIT 1
    """, (project, task_no, res_id))
    
    rate = float(rate_check[0]['base_rate']) if rate_check and rate_check[0]['base_rate'] else 0.0
    amount = hours * rate
    
    # Confirm entry
    console.print("\n[bold yellow]Confirm Entry:[/bold yellow]")
    console.print(f"  Project: {project}")
    console.print(f"  Date: {date} (yr_mon: {yr_mon})")
    console.print(f"  Task: {task_no} / SubTask: {sub_task_no}")
    console.print(f"  Resource: {res_id}")
    console.print(f"  Hours: {hours}")
    console.print(f"  Mileage: {mileage}")
    console.print(f"  Expense: ${expense:.2f}")
    console.print(f"  Description: {description}")
    console.print(f"  Subject: {subject}")
    console.print(f"  Rate: ${rate:.2f}/hr")
    console.print(f"  Amount: ${amount:.2f}\n")
    
    if not click.confirm('Save this entry?', default=True):
        console.print("[yellow]Entry cancelled[/yellow]")
        return True  # Continue loop
    
    # Insert into database
    try:
        execute_insert("""
            INSERT INTO bgs.timesheet 
            (yr_mon, project_code, task_no, sub_task_no, ts_date,
             res_id, ts_units, ts_mileage, ts_expense, ts_desc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (yr_mon, project, task_no, sub_task_no, date, 
              res_id, hours, mileage, expense, description))
        
        console.print("[bold green]✓ Time entry saved successfully![/bold green]")
        
        # Write to ORG-MODE file
        write_org_report(project, date, yr_mon, task_no, sub_task_no, res_id, 
                        hours, mileage, expense, description, subject, amount)
        
        # Show updated utilization
        show_utilization(project)
        
        # Pause before clearing
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
        
        return True  # Continue loop
        
    except Exception as e:
        console.print(f"[red]Error saving entry: {e}[/red]")
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
        return True  # Continue loop

def write_org_report(project, date, yr_mon, task_no, sub_task_no, res_id, 
                    hours, mileage, expense, description, subject, amount):
    """Write time entry to project ORG-MODE report"""
    
    # Use your preferred path
    report_dir = "/mnt/sda1/01_bgm_projman/Timesheets/proj_report"
    
    # Fallback to home directory if mount not available
    if not os.path.exists(report_dir):
        report_dir = os.path.expanduser("~/bgs_timesheets")
        os.makedirs(report_dir, exist_ok=True)
        console.print(f"[yellow]Note: Using fallback directory {report_dir}[/yellow]")
    
    report_file = f"{report_dir}/ts_report_{project}.org"
    
    # Append to ORG file (matching your bash script format)
    with open(report_file, 'a') as f:
        f.write(f"* {yr_mon}\n")
        f.write(f"** [{date}] {subject}\n")
        f.write(f":PROPERTIES:\n")
        f.write(f":Proj_No: {project}\n")
        f.write(f":Task_No: {task_no}\n")
        f.write(f":SubTask_No: {sub_task_no}\n")
        f.write(f":Resource: {res_id}\n")
        f.write(f":Hrs: {hours}\n")
        f.write(f":Mileage: {mileage}\n")
        f.write(f":Expense_Amt: ${expense:.2f}\n")
        f.write(f":END:\n")
        f.write(f"  - {description}\n\n")
    
    console.print(f"[dim]Report updated: {report_file}[/dim]")

def show_utilization(project_code):
    """Show project utilization summary"""
    util = execute_query("""
        SELECT 
            task_no,
            res_name,
            budgeted_hours,
            actual_hours,
            remaining_hours
        FROM bgs.vw_project_utilization
        WHERE project_code = %s
        ORDER BY task_no
    """, (project_code,))
    
    if not util:
        return
    
    console.print("\n[cyan]Project Utilization:[/cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task", style="cyan")
    table.add_column("Resource", style="green")
    table.add_column("Budget", justify="right")
    table.add_column("Actual", justify="right")
    table.add_column("Remaining", justify="right")
    
    for u in util:
        remaining = float(u['remaining_hours'] or 0)
        remaining_color = "green" if remaining > 0 else "red"
        table.add_row(
            u['task_no'],
            u['res_name'],
            f"{float(u['budgeted_hours'] or 0):.1f}",
            f"{float(u['actual_hours'] or 0):.1f}",
            f"[{remaining_color}]{remaining:.1f}[/{remaining_color}]"
        )
    
    console.print(table)
