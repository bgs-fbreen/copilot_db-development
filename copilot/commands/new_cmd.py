"""
New project setup command - replaces manual database entry
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, execute_insert
from datetime import datetime
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.command()
def new():
    """Set up a new BGS project with tasks and baseline"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    BGS New Project Setup[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Step 1: Client
    client_code = setup_client()
    if not client_code:
        return
    
    # Step 2: Project
    project_code = setup_project(client_code)
    if not project_code:
        return
    
    # Step 3: Tasks
    if not setup_tasks(project_code):
        return
    
    # Step 4: Baseline
    if not setup_baseline(project_code):
        return
    
    clear_screen()
    console.print("\n[bold green]✓ Project setup complete![/bold green]")
    console.print(f"\n[cyan]Project Code:[/cyan] [bold]{project_code}[/bold]")
    console.print(f"[dim]You can now enter time with:[/dim] copilot timesheet -p {project_code}\n")

def setup_client():
    """Step 1: Select or create client"""
    
    console.print("[bold yellow]STEP 1: Client[/bold yellow]\n")
    
    # Show existing clients
    clients = execute_query("""
        SELECT code, name, contact_name, phone 
        FROM bgs.client 
        WHERE status = 'active'
        ORDER BY code
    """)
    
    if clients:
        console.print("[cyan]Existing Clients:[/cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Code", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Contact", style="green")
        
        for c in clients:
            table.add_row(
                c['code'],
                c['name'],
                c['contact_name'] or ''
            )
        
        console.print(table)
        console.print()
    
    client_code = Prompt.ask("\nClient Code (or 'new' to create)", default="").strip()
    
    if not client_code or client_code.lower() in ['quit', 'exit', 'q']:
        return None
    
    if client_code.lower() == 'new':
        return create_new_client()
    
    # Verify client exists
    check = execute_query("SELECT code FROM bgs.client WHERE code = %s", (client_code,))
    if not check:
        console.print(f"[red]Client '{client_code}' not found[/red]")
        if Confirm.ask("Create new client?", default=True):
            return create_new_client(client_code)
        return None
    
    return client_code

def create_new_client(code=None):
    """Create a new client"""
    
    console.print("\n[yellow]Creating New Client[/yellow]")
    
    if not code:
        code = Prompt.ask("Client Code (e.g., tbls, cnh)").strip()
        if not code or code.lower() in ['quit', 'exit', 'q']:
            return None
    
    name = Prompt.ask("Client Name").strip()
    contact_name = Prompt.ask("Contact Name", default="").strip()
    email = Prompt.ask("Email", default="").strip()
    phone = Prompt.ask("Phone", default="").strip()
    
    try:
        execute_insert("""
            INSERT INTO bgs.client (code, name, contact_name, email, phone, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (code, name, contact_name or None, email or None, phone or None))
        
        console.print(f"[green]✓ Client '{code}' created[/green]")
        return code
    except Exception as e:
        console.print(f"[red]Error creating client: {e}[/red]")
        return None

def setup_project(client_code):
    """Step 2: Create project"""
    
    console.print("\n[bold yellow]STEP 2: Project[/bold yellow]\n")
    
    # Get project details
    project_year = Prompt.ask("Project Year (YY)", default=str(datetime.now().year)[2:]).strip()
    project_number = Prompt.ask("Project Number (e.g., 1904)").strip()
    
    if not project_number or project_number.lower() in ['quit', 'exit', 'q']:
        return None
    
    # Build project code
    project_code = f"{client_code}.{project_year}.{project_number}"
    
    console.print(f"\n[cyan]Project Code:[/cyan] [bold]{project_code}[/bold]\n")
    
    project_name = Prompt.ask("Project Name").strip()
    project_desc = Prompt.ask("Project Description", default="").strip()
    client_po = Prompt.ask("Client PO Number", default="").strip()
    
    try:
        execute_insert("""
            INSERT INTO bgs.project 
            (project_code, client_code, project_year, project_number,
             project_name, project_desc, client_po, status, start_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', CURRENT_DATE)
        """, (project_code, client_code, int('20' + project_year), int(project_number),
              project_name, project_desc or None, client_po or None))
        
        console.print(f"[green]✓ Project '{project_code}' created[/green]")
        return project_code
    except Exception as e:
        console.print(f"[red]Error creating project: {e}[/red]")
        return None

def setup_tasks(project_code):
    """Step 3: Create tasks and subtasks"""
    
    console.print("\n[bold yellow]STEP 3: Tasks[/bold yellow]\n")
    console.print("[dim]Enter tasks for this project. Type 'done' when finished.[/dim]\n")
    
    task_count = 0
    
    while True:
        task_no = Prompt.ask(f"\nTask {task_count + 1} (e.g., T01, T02, or 'done')", default="done").strip()
        
        if task_no.lower() in ['done', 'quit', 'exit', 'q', '']:
            break
        
        task_name = Prompt.ask("Task Name").strip()
        task_notes = Prompt.ask("Task Notes", default="").strip()
        
        # Ask about subtasks
        has_subtasks = Confirm.ask("Add subtasks?", default=False)
        
        if has_subtasks:
            subtask_count = 0
            while True:
                sub_task_no = Prompt.ask(f"  SubTask {subtask_count + 1} (e.g., S01, S02, or 'done')", default="done").strip()
                
                if sub_task_no.lower() in ['done', '']:
                    break
                
                sub_task_name = Prompt.ask("  SubTask Name").strip()
                
                try:
                    execute_insert("""
                        INSERT INTO bgs.task 
                        (project_code, task_no, task_name, task_notes, sub_task_no, sub_task_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (project_code, task_no, task_name, task_notes or None, 
                          sub_task_no, sub_task_name))
                    
                    console.print(f"  [green]✓ Added subtask {sub_task_no}[/green]")
                    subtask_count += 1
                except Exception as e:
                    console.print(f"  [red]Error: {e}[/red]")
        else:
            # No subtasks - add task with 'na' subtask
            try:
                execute_insert("""
                    INSERT INTO bgs.task 
                    (project_code, task_no, task_name, task_notes, sub_task_no, sub_task_name)
                    VALUES (%s, %s, %s, %s, 'na', 'na')
                """, (project_code, task_no, task_name, task_notes or None))
                
                console.print(f"[green]✓ Added task {task_no}[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        task_count += 1
    
    if task_count == 0:
        console.print("[yellow]No tasks added[/yellow]")
    
    return True

def show_baseline_screen(project_code):
    """Show tasks, resources, and existing baseline"""
    clear_screen()
    
    console.print("\n[bold yellow]STEP 4: Baseline Budget[/bold yellow]\n")
    
    # Show tasks
    tasks = execute_query("""
        SELECT DISTINCT task_no, sub_task_no, task_name
        FROM bgs.task
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if tasks:
        console.print("[cyan]Tasks for this project:[/cyan]")
        task_table = Table(show_header=True, header_style="bold magenta")
        task_table.add_column("Task", style="cyan")
        task_table.add_column("SubTask", style="yellow")
        task_table.add_column("Task Name", style="white")
        
        for t in tasks:
            task_table.add_row(
                t['task_no'],
                t['sub_task_no'],
                t['task_name'] or ''
            )
        
        console.print(task_table)
    
    # Show resources
    resources = execute_query("SELECT res_id, res_name FROM bgs.resource ORDER BY res_id")
    
    console.print("\n[cyan]Available Resources:[/cyan]")
    for r in resources:
        console.print(f"  {r['res_id']} - {r['res_name']}")
    
    # Show existing baseline
    baseline = execute_query("""
        SELECT task_no, sub_task_no, res_id, base_units, base_rate
        FROM bgs.baseline
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no, res_id
    """, (project_code,))
    
    if baseline:
        console.print("\n[cyan]Baseline Entries:[/cyan]")
        baseline_table = Table(show_header=True, header_style="bold magenta")
        baseline_table.add_column("Task", style="cyan")
        baseline_table.add_column("SubTask", style="yellow")
        baseline_table.add_column("Resource", style="green")
        baseline_table.add_column("Hours", justify="right")
        baseline_table.add_column("Rate", justify="right")
        baseline_table.add_column("Amount", justify="right")
        
        for b in baseline:
            hours = float(b['base_units'] or 0)
            rate = float(b['base_rate'] or 0)
            amount = hours * rate
            baseline_table.add_row(
                b['task_no'],
                b['sub_task_no'],
                b['res_id'],
                f"{hours:.1f}",
                f"${rate:.2f}",
                f"${amount:.2f}"
            )
        
        console.print(baseline_table)
    
    console.print("\n[dim]Enter baseline for each task/resource. Type 'done' when finished.[/dim]\n")

def setup_baseline(project_code):
    """Step 4: Create baseline budget"""
    
    # Get tasks for this project
    tasks = execute_query("""
        SELECT DISTINCT task_no, sub_task_no, task_name
        FROM bgs.task
        WHERE project_code = %s
        ORDER BY task_no, sub_task_no
    """, (project_code,))
    
    if not tasks:
        console.print("[yellow]No tasks found. Skipping baseline.[/yellow]")
        return True
    
    # Show initial screen
    show_baseline_screen(project_code)
    
    baseline_count = 0
    
    while True:
        task_no = Prompt.ask(f"\nTask (or 'done')", default="done").strip()
        
        if task_no.lower() in ['done', 'quit', 'exit', 'q', '']:
            break
        
        sub_task_no = Prompt.ask("SubTask", default="na").strip()
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
            baseline_count += 1
            
            # Refresh screen after each entry
            show_baseline_screen(project_code)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    if baseline_count == 0:
        console.print("[yellow]No baseline added[/yellow]")
    
    return True
