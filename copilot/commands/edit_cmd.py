"""
Edit existing project command - add tasks, change orders, update baseline
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, execute_insert
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.command()
@click.option('--project', '-p', help='BGS Project No. to edit')
def edit(project):
    """Edit existing BGS project - add tasks, change orders, baseline"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    Edit BGS Project[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Get project
    if not project:
        project = select_project()
        if not project:
            return
    
    # Verify project exists
    proj = execute_query(
        "SELECT project_code, project_name, status FROM bgs.project WHERE project_code = %s",
        (project,)
    )
    
    if not proj:
        console.print(f"[red]BGS Project No. '{project}' not found[/red]")
        return
    
    proj = proj[0]
    
    while True:
        clear_screen()
        show_project_summary(proj['project_code'])
        
        console.print("\n[bold yellow]What would you like to do?[/bold yellow]\n")
        console.print("  [cyan]1.[/cyan] Add new task")
        console.print("  [cyan]2.[/cyan] Add change order to existing task")
        console.print("  [cyan]3.[/cyan] Add/update baseline")
        console.print("  [cyan]4.[/cyan] View project utilization")
        console.print("  [cyan]5.[/cyan] Update project details")
        console.print("  [cyan]q.[/cyan] Quit\n")
        
        choice = Prompt.ask("Select option", default="q").strip().lower()
        
        if choice in ['q', 'quit', 'exit', '']:
            break
        elif choice == '1':
            add_task(proj['project_code'])
        elif choice == '2':
            add_change_order(proj['project_code'])
        elif choice == '3':
            add_baseline(proj['project_code'])
        elif choice == '4':
            view_utilization(proj['project_code'])
        elif choice == '5':
            update_project_details(proj['project_code'])
        else:
            console.print("[red]Invalid option[/red]")
            input("\nPress Enter to continue...")
    
    clear_screen()
    console.print("\n[bold green]✓ Project editing complete![/bold green]\n")

def select_project():
    """Select a project to edit"""
    
    console.print("[cyan]Active Projects:[/cyan]\n")
    
    projects = execute_query("""
        SELECT project_code, project_name, client_code
        FROM bgs.project
        WHERE status = 'active'
        ORDER BY project_code DESC
    """)
    
    if not projects:
        console.print("[yellow]No active projects found[/yellow]")
        return None
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("BGS Project No.", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Project Name", style="white")
    
    for p in projects:
        table.add_row(
            p['project_code'],
            p['client_code'],
            (p['project_name'] or '')[:50]
        )
    
    console.print(table)
    
    project = Prompt.ask("\nBGS Project No.", default="").strip()
    if not project or project.lower() in ['quit', 'exit', 'q']:
        return None
    
    return project

def show_project_summary(project_code):
    """Show project summary with tasks and baseline"""
    
    proj = execute_query(
        "SELECT project_code, project_name, client_code, client_po FROM bgs.project WHERE project_code = %s",
        (project_code,)
    )[0]
    
    console.print(f"\n[bold]BGS Project No.:[/bold] {proj['project_code']}")
    console.print(f"[bold]Name:[/bold] {proj['project_name']}")
    console.print(f"[bold]Client:[/bold] {proj['client_code']}")
    if proj['client_po']:
        console.print(f"[bold]PO:[/bold] {proj['client_po']}")
    
    # Show tasks
    tasks = execute_query("""
        SELECT DISTINCT task_no, sub_task_no, task_name, task_co_no
        FROM bgs.task
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if tasks:
        console.print("\n[cyan]Tasks:[/cyan]")
        task_table = Table(show_header=True, header_style="bold magenta", box=None)
        task_table.add_column("Task", style="cyan")
        task_table.add_column("SubTask", style="yellow")
        task_table.add_column("Task Name", style="white")
        task_table.add_column("Change Order", style="red")
        
        for t in tasks:
            task_table.add_row(
                t['task_no'],
                t['sub_task_no'] or 'na',
                t['task_name'] or '',
                t['task_co_no'] or ''
            )
        
        console.print(task_table)
    
    # Show baseline summary
    baseline = execute_query("""
        SELECT 
            COUNT(*) as entries,
            SUM(base_units) as total_hours,
            SUM(base_units * base_rate) as total_budget
        FROM bgs.baseline
        WHERE project_code = %s
    """, (project_code,))
    
    if baseline and baseline[0]['entries']:
        b = baseline[0]
        console.print(f"\n[cyan]Baseline:[/cyan] {b['entries']} entries, {float(b['total_hours'] or 0):.1f} hours, ${float(b['total_budget'] or 0):,.2f}")

def add_task(project_code):
    """Add a new task to the project"""
    
    clear_screen()
    console.print(f"\n[bold yellow]Add New Task to {project_code}[/bold yellow]\n")
    
    # Show existing tasks
    tasks = execute_query("""
        SELECT DISTINCT task_no FROM bgs.task WHERE project_code = %s ORDER BY task_no
    """, (project_code,))
    
    if tasks:
        console.print("[cyan]Existing tasks:[/cyan]", ', '.join([t['task_no'] for t in tasks]))
        console.print()
    
    task_no = Prompt.ask("New Task Number (e.g., T05)").strip()
    if not task_no or task_no.lower() in ['quit', 'exit', 'q']:
        return
    
    task_name = Prompt.ask("Task Name").strip()
    task_notes = Prompt.ask("Task Notes", default="").strip()
    
    # Ask about subtasks
    has_subtasks = Confirm.ask("Add subtasks?", default=False)
    
    if has_subtasks:
        while True:
            sub_task_no = Prompt.ask("SubTask (e.g., S01, or 'done')", default="done").strip()
            if sub_task_no.lower() in ['done', 'quit', 'exit', 'q', '']:
                break
            
            sub_task_name = Prompt.ask("SubTask Name").strip()
            
            try:
                execute_insert("""
                    INSERT INTO bgs.task 
                    (project_code, task_no, task_name, task_notes, sub_task_no, sub_task_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (project_code, task_no, task_name, task_notes or None, 
                      sub_task_no, sub_task_name))
                
                console.print(f"[green]✓ Added subtask {sub_task_no}[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    else:
        try:
            execute_insert("""
                INSERT INTO bgs.task 
                (project_code, task_no, task_name, task_notes, sub_task_no, sub_task_name)
                VALUES (%s, %s, %s, %s, 'na', 'na')
            """, (project_code, task_no, task_name, task_notes or None))
            
            console.print(f"[green]✓ Added task {task_no}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    input("\nPress Enter to continue...")

def add_change_order(project_code):
    """Add a change order to an existing task"""
    
    clear_screen()
    console.print(f"\n[bold yellow]Add Change Order to {project_code}[/bold yellow]\n")
    
    # Show existing tasks
    tasks = execute_query("""
        SELECT DISTINCT task_no, task_name FROM bgs.task 
        WHERE project_code = %s 
        ORDER BY task_no
    """, (project_code,))
    
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        input("\nPress Enter to continue...")
        return
    
    console.print("[cyan]Existing tasks:[/cyan]")
    for t in tasks:
        console.print(f"  {t['task_no']} - {t['task_name']}")
    console.print()
    
    base_task = Prompt.ask("Base Task (e.g., T01)").strip()
    if not base_task or base_task.lower() in ['quit', 'exit', 'q']:
        return
    
    co_number = Prompt.ask("Change Order Number (e.g., CH01, CH02)").strip()
    if not co_number or co_number.lower() in ['quit', 'exit', 'q']:
        return
    
    # New task number format: T01:CH01
    new_task_no = f"{base_task}:{co_number}"
    
    task_name = Prompt.ask("Change Order Description").strip()
    task_notes = Prompt.ask("Change Order Notes", default="").strip()
    
    try:
        execute_insert("""
            INSERT INTO bgs.task 
            (project_code, task_no, task_name, task_notes, sub_task_no, sub_task_name, task_co_no, task_co_name)
            VALUES (%s, %s, %s, %s, 'na', 'na', %s, %s)
        """, (project_code, new_task_no, task_name, task_notes or None, co_number, task_name))
        
        console.print(f"[green]✓ Added change order {new_task_no}[/green]")
        
        # Ask if they want to add baseline for this change order
        if Confirm.ask("\nAdd baseline for this change order?", default=True):
            add_baseline_for_task(project_code, new_task_no, 'na')
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    
    input("\nPress Enter to continue...")

def add_baseline(project_code):
    """Add or update baseline entries"""
    
    clear_screen()
    console.print(f"\n[bold yellow]Add/Update Baseline for {project_code}[/bold yellow]\n")
    
    # Show tasks
    tasks = execute_query("""
        SELECT DISTINCT task_no, sub_task_no, task_name
        FROM bgs.task
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        input("\nPress Enter to continue...")
        return
    
    console.print("[cyan]Tasks:[/cyan]")
    task_table = Table(show_header=True, header_style="bold magenta", box=None)
    task_table.add_column("Task", style="cyan")
    task_table.add_column("SubTask", style="yellow")
    task_table.add_column("Task Name", style="white")
    
    for t in tasks:
        task_table.add_row(t['task_no'], t['sub_task_no'], t['task_name'] or '')
    
    console.print(task_table)
    
    # Show resources
    resources = execute_query("SELECT res_id, res_name FROM bgs.resource ORDER BY res_id")
    console.print("\n[cyan]Resources:[/cyan]")
    for r in resources:
        console.print(f"  {r['res_id']} - {r['res_name']}")
    
    # Show existing baseline
    baseline = execute_query("""
        SELECT task_no, sub_task_no, res_id, base_units, base_rate
        FROM bgs.baseline
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if baseline:
        console.print("\n[cyan]Current Baseline:[/cyan]")
        baseline_table = Table(show_header=True, header_style="bold magenta", box=None)
        baseline_table.add_column("Task")
        baseline_table.add_column("SubTask")
        baseline_table.add_column("Resource")
        baseline_table.add_column("Hours", justify="right")
        baseline_table.add_column("Rate", justify="right")
        
        for b in baseline:
            baseline_table.add_row(
                b['task_no'],
                b['sub_task_no'],
                b['res_id'],
                f"{float(b['base_units'] or 0):.1f}",
                f"${float(b['base_rate'] or 0):.2f}"
            )
        
        console.print(baseline_table)
    
    console.print("\n")
    
    task_no = Prompt.ask("Task", default="").strip()
    if not task_no or task_no.lower() in ['quit', 'exit', 'q']:
        return
    
    sub_task_no = Prompt.ask("SubTask", default="na").strip()
    
    add_baseline_for_task(project_code, task_no, sub_task_no)
    
    input("\nPress Enter to continue...")

def add_baseline_for_task(project_code, task_no, sub_task_no):
    """Add baseline entry for a specific task"""
    
    res_id = Prompt.ask("Resource ID", default="F.Breen").strip()
    base_units = float(Prompt.ask("Budgeted Hours", default="0").strip() or 0)
    base_rate = float(Prompt.ask("Billing Rate ($/hr)", default="150").strip() or 150)
    base_miles = float(Prompt.ask("Budgeted Miles", default="0").strip() or 0)
    base_miles_rate = float(Prompt.ask("Mileage Rate ($/mile)", default="0.67").strip() or 0.67)
    base_expense = float(Prompt.ask("Budgeted Expenses ($)", default="0").strip() or 0)
    
    try:
        execute_insert("""
            INSERT INTO bgs.baseline 
            (project_code, task_no, sub_task_no, res_id,
             base_units, base_rate, base_miles, base_expense, base_miles_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (project_code, task_no, sub_task_no, res_id,
              base_units, base_rate, base_miles, base_expense, base_miles_rate))
        
        console.print(f"[green]✓ Baseline added: {task_no}/{sub_task_no} - {res_id} ({base_units} hrs @ ${base_rate}/hr)[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def view_utilization(project_code):
    """View project utilization report"""
    
    clear_screen()
    
    # Get project details
    proj = execute_query(
        "SELECT project_code, project_name, client_code FROM bgs.project WHERE project_code = %s",
        (project_code,)
    )[0]
    
    console.print(f"\n[bold yellow]Project Utilization Report[/bold yellow]\n")
    
    util = execute_query("""
        SELECT 
            task_no,
            sub_task_no,
            res_name,
            budgeted_hours,
            actual_hours,
            remaining_hours,
            base_rate,
            budgeted_amount,
            actual_amount
        FROM bgs.vw_project_utilization
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if not util:
        console.print("[yellow]No utilization data found[/yellow]")
    else:
        # Create table with project info in title
        table = Table(
            show_header=True, 
            header_style="bold magenta",
            title=f"[bold cyan]BGS Project No. {proj['project_code']}[/bold cyan]\n{proj['project_name']}\nClient: {proj['client_code']}",
            title_style="bold white"
        )
        
        table.add_column("Task", style="cyan")
        table.add_column("Sub", style="yellow")
        table.add_column("Resource", style="green")
        table.add_column("Bdgt Hrs", justify="right")
        table.add_column("Act Hrs", justify="right")
        table.add_column("Rem Hrs", justify="right")
        table.add_column("Rate", justify="right")
        table.add_column("Bdgt $", justify="right")
        table.add_column("Act $", justify="right")
        table.add_column("Rem $", justify="right")
        
        total_budget_hrs = 0
        total_actual_hrs = 0
        total_budget_amt = 0
        total_actual_amt = 0
        
        for u in util:
            budget_hrs = float(u['budgeted_hours'] or 0)
            actual_hrs = float(u['actual_hours'] or 0)
            remaining_hrs = float(u['remaining_hours'] or 0)
            rate = float(u['base_rate'] or 0)
            budget_amt = float(u['budgeted_amount'] or 0)
            actual_amt = float(u['actual_amount'] or 0)
            remaining_amt = budget_amt - actual_amt
            
            total_budget_hrs += budget_hrs
            total_actual_hrs += actual_hrs
            total_budget_amt += budget_amt
            total_actual_amt += actual_amt
            
            remaining_hrs_color = "green" if remaining_hrs > 0 else "red"
            remaining_amt_color = "green" if remaining_amt > 0 else "red"
            
            table.add_row(
                u['task_no'],
                u['sub_task_no'],
                u['res_name'][:20],
                f"{budget_hrs:.1f}",
                f"{actual_hrs:.1f}",
                f"[{remaining_hrs_color}]{remaining_hrs:.1f}[/{remaining_hrs_color}]",
                f"${rate:.0f}",
                f"${budget_amt:,.0f}",
                f"${actual_amt:,.0f}",
                f"[{remaining_amt_color}]${remaining_amt:,.0f}[/{remaining_amt_color}]"
            )
        
        # Add totals row
        total_remaining_hrs = total_budget_hrs - total_actual_hrs
        total_remaining_amt = total_budget_amt - total_actual_amt
        remaining_hrs_color = "green" if total_remaining_hrs > 0 else "red"
        remaining_amt_color = "green" if total_remaining_amt > 0 else "red"
        
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            f"[bold]{total_budget_hrs:.1f}[/bold]",
            f"[bold]{total_actual_hrs:.1f}[/bold]",
            f"[bold {remaining_hrs_color}]{total_remaining_hrs:.1f}[/bold {remaining_hrs_color}]",
            "",
            f"[bold]${total_budget_amt:,.0f}[/bold]",
            f"[bold]${total_actual_amt:,.0f}[/bold]",
            f"[bold {remaining_amt_color}]${total_remaining_amt:,.0f}[/bold {remaining_amt_color}]"
        )
        
        console.print(table)
        
        # Summary stats
        if total_budget_hrs > 0:
            pct_complete_hrs = (total_actual_hrs / total_budget_hrs) * 100
            pct_complete_amt = (total_actual_amt / total_budget_amt) * 100 if total_budget_amt > 0 else 0
            
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"  Hours: {pct_complete_hrs:.1f}% complete")
            console.print(f"  Budget: {pct_complete_amt:.1f}% spent")
    
    input("\nPress Enter to continue...")

def update_project_details(project_code):
    """Update project name, PO, status, etc."""
    
    clear_screen()
    console.print(f"\n[bold yellow]Update Project Details: {project_code}[/bold yellow]\n")
    
    proj = execute_query(
        "SELECT project_name, project_desc, client_po, status FROM bgs.project WHERE project_code = %s",
        (project_code,)
    )[0]
    
    console.print(f"[bold]Current Details:[/bold]")
    console.print(f"  Name: {proj['project_name']}")
    console.print(f"  Description: {proj['project_desc'] or '(none)'}")
    console.print(f"  PO: {proj['client_po'] or '(none)'}")
    console.print(f"  Status: {proj['status']}")
    console.print()
    
    if Confirm.ask("Update project name?", default=False):
        new_name = Prompt.ask("New project name", default=proj['project_name']).strip()
        execute_insert("UPDATE bgs.project SET project_name = %s WHERE project_code = %s", (new_name, project_code))
        console.print("[green]✓ Project name updated[/green]")
    
    if Confirm.ask("Update PO number?", default=False):
        new_po = Prompt.ask("New PO number", default=proj['client_po'] or "").strip()
        execute_insert("UPDATE bgs.project SET client_po = %s WHERE project_code = %s", (new_po or None, project_code))
        console.print("[green]✓ PO updated[/green]")
    
    if Confirm.ask("Update project status?", default=False):
        console.print("\nStatus options: active, on-hold, completed, invoiced, closed")
        new_status = Prompt.ask("New status", default=proj['status']).strip()
        execute_insert("UPDATE bgs.project SET status = %s WHERE project_code = %s", (new_status, project_code))
        console.print("[green]✓ Status updated[/green]")
    
    input("\nPress Enter to continue...")
