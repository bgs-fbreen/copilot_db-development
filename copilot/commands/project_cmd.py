"""
Project management command with automatic directory structure creation
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, get_connection
from datetime import datetime
import os
from pathlib import Path

console = Console()

# Base directory for all project management
PROJECT_BASE_DIR = "/mnt/sda1/01_bgm_projman/Active"

# Fallback if mount not available
PROJECT_FALLBACK_DIR = os.path.expanduser("~/bgm_projects/Active")

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_base_dir():
    """Get base project directory, use fallback if mount unavailable"""
    if os.path.exists(PROJECT_BASE_DIR):
        return PROJECT_BASE_DIR
    else:
        console.print(f"[yellow]⚠ Mount not available: {PROJECT_BASE_DIR}[/yellow]")
        console.print(f"[yellow]  Using fallback: {PROJECT_FALLBACK_DIR}[/yellow]")
        return PROJECT_FALLBACK_DIR

def create_project_directories(client_code, project_code):
    """
    Create project directory structure:
    /mnt/sda1/01_bgm_projman/Active/{client_code}/{project_code}/
        ├── 01_baseline/
        ├── 02_invoices/
        ├── 03_authorization/
        ├── 04_subcontractors/
        └── 05_reports/
    """
    base_dir = get_base_dir()
    
    # Project root directory
    project_root = os.path.join(base_dir, client_code, project_code)
    
    # Subdirectories
    subdirs = [
        '01_baseline',
        '02_invoices',
        '03_authorization',
        '04_subcontractors',
        '05_reports'
    ]
    
    # Create all directories
    for subdir in subdirs:
        dir_path = os.path.join(project_root, subdir)
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    return project_root

@click.group()
def project():
    """Project management commands"""
    pass

@project.command('create-dirs')
@click.argument('project_code')
def create_dirs(project_code):
    """Create directory structure for existing project"""
    
    # Get project info
    proj = execute_query("""
        SELECT 
            p.project_code,
            p.project_name,
            p.client_code,
            c.name as client_name
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, (project_code,))
    
    if not proj:
        console.print(f"[red]Project '{project_code}' not found[/red]")
        return
    
    p = proj[0]
    
    console.print(f"\n[bold cyan]Create Directory Structure[/bold cyan]\n")
    console.print(f"[bold]Project:[/bold] {p['project_name']}")
    console.print(f"[bold]Client:[/bold] {p['client_name']}")
    console.print(f"[bold]Project Code:[/bold] {p['project_code']}\n")
    
    if not Confirm.ask("Create directories?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    try:
        project_root = create_project_directories(p['client_code'], p['project_code'])
        
        console.print(f"\n[bold green]✓ Directories created![/bold green]")
        console.print(f"[dim]Location: {project_root}[/dim]\n")
        
        console.print("Structure:")
        console.print(f"  {p['client_code']}/")
        console.print(f"    └── {p['project_code']}/")
        console.print(f"        ├── 01_baseline/")
        console.print(f"        ├── 02_invoices/")
        console.print(f"        ├── 03_authorization/")
        console.print(f"        ├── 04_subcontractors/")
        console.print(f"        └── 05_reports/\n")
        
    except Exception as e:
        console.print(f"[red]Error creating directories: {e}[/red]")

@project.command('list')
@click.option('--client', '-c', help='Filter by client code')
@click.option('--status', '-s', help='Filter by status', default='active')
def list_projects(client, status):
    """List projects"""
    
    where_clauses = []
    params = []
    
    if client:
        where_clauses.append("p.client_code = %s")
        params.append(client)
    
    if status:
        where_clauses.append("p.status = %s")
        params.append(status)
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    projects = execute_query(f"""
        SELECT 
            p.project_code,
            p.project_name,
            p.client_code,
            c.name as client_name,
            p.start_date,
            p.status
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        {where_sql}
        ORDER BY p.project_code DESC
    """, params if params else None)
    
    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Projects[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project Code", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Project Name", style="white")
    table.add_column("Start Date", style="yellow")
    table.add_column("Status")
    
    for p in projects:
        start = p['start_date'].strftime('%Y-%m-%d') if p['start_date'] else ""
        table.add_row(
            p['project_code'],
            p['client_code'],
            (p['project_name'] or '')[:50],
            start,
            p['status']
        )
    
    console.print(table)
    console.print()

# Import and register init-all command
from copilot.commands.project_init_cmd import init_all_projects
project.add_command(init_all_projects)


# Import and register setup-all command
from copilot.commands.project_setup_cmd import setup_all_projects
project.add_command(setup_all_projects)
