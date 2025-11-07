"""
Project initialization - Create directories for all active projects
"""
import click
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query
from copilot.utils import get_project_directory_name
import os
from pathlib import Path

console = Console()

# Project base directory
PROJECT_BASE_DIR = "/mnt/sda1/01_bgm_projman/Active"
PROJECT_FALLBACK_DIR = os.path.expanduser("~/bgm_projects/Active")

def get_base_dir():
    """Get base project directory"""
    if os.path.exists(PROJECT_BASE_DIR):
        return PROJECT_BASE_DIR
    else:
        console.print(f"[yellow]⚠ Mount not available: {PROJECT_BASE_DIR}[/yellow]")
        console.print(f"[yellow]  Using fallback: {PROJECT_FALLBACK_DIR}[/yellow]")
        return PROJECT_FALLBACK_DIR

def create_project_directories(client_code, project_code, project_name=None, base_dir=None):
    """
    Create complete project directory structure with abbreviated name
    """
    if not base_dir:
        base_dir = get_base_dir()
    
    # Generate directory name with abbreviated project name
    dir_name = get_project_directory_name(project_code, project_name)
    
    # Project root directory
    project_root = os.path.join(base_dir, client_code, dir_name)
    
    # Subdirectories
    subdirs = [
        '01_baseline',
        '02_invoices',
        '03_authorization',
        '04_subcontractors',
        '05_reports'
    ]
    
    # Create all directories
    created = []
    for subdir in subdirs:
        dir_path = os.path.join(project_root, subdir)
        if not os.path.exists(dir_path):
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            created.append(subdir)
    
    return project_root, created, dir_name

@click.command('init-all')
@click.option('--dry-run', is_flag=True, help='Show what would be created without creating')
def init_all_projects(dry_run):
    """Initialize directory structure for all ACTIVE projects"""
    
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Initialize Active Project Directories[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    base_dir = get_base_dir()
    console.print(f"[bold]Base Directory:[/bold] {base_dir}")
    console.print(f"[bold]Status Filter:[/bold] active only\n")
    
    # Get ONLY active projects
    projects = execute_query("""
        SELECT 
            p.project_code,
            p.project_name,
            p.client_code,
            c.name as client_name,
            p.status
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.status = 'active'
        ORDER BY p.client_code, p.project_code
    """)
    
    if not projects:
        console.print(f"[yellow]No active projects found[/yellow]")
        return
    
    console.print(f"[bold]Found {len(projects)} active projects[/bold]\n")
    
    if dry_run:
        console.print("[yellow]DRY RUN - No directories will be created[/yellow]\n")
    
    # Track statistics
    total_projects = 0
    total_dirs_created = 0
    errors = []
    
    # Create table for results
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan", width=15)
    table.add_column("Client", style="green", width=8)
    table.add_column("Directory Name", style="white", width=45)
    table.add_column("Status", style="white", width=18)
    table.add_column("Dirs", justify="right", style="yellow", width=6)
    
    for proj in projects:
        total_projects += 1
        
        try:
            dir_name = get_project_directory_name(proj['project_code'], proj['project_name'])
            
            if not dry_run:
                project_root, created, dir_name = create_project_directories(
                    proj['client_code'], 
                    proj['project_code'],
                    proj['project_name'],
                    base_dir
                )
                dirs_created = len(created)
                total_dirs_created += dirs_created
                
                if dirs_created > 0:
                    status_text = f"✓ Created {dirs_created}"
                    status_style = "green"
                elif dirs_created == 0:
                    status_text = "Already exists"
                    status_style = "dim"
            else:
                project_root = os.path.join(base_dir, proj['client_code'], dir_name)
                if os.path.exists(project_root):
                    # Check if all subdirs exist
                    subdirs_exist = all(
                        os.path.exists(os.path.join(project_root, subdir))
                        for subdir in ['01_baseline', '02_invoices', '03_authorization', 
                                     '04_subcontractors', '05_reports']
                    )
                    if subdirs_exist:
                        status_text = "Skip (exists)"
                        status_style = "dim"
                        dirs_created = 0
                    else:
                        status_text = "Would update"
                        status_style = "yellow"
                        dirs_created = 1
                else:
                    status_text = "Would create"
                    status_style = "yellow"
                    dirs_created = 5
            
            # Truncate directory name for display
            display_name = dir_name if len(dir_name) <= 43 else dir_name[:40] + "..."
            
            table.add_row(
                proj['project_code'],
                proj['client_code'],
                display_name,
                f"[{status_style}]{status_text}[/{status_style}]",
                str(dirs_created) if dirs_created > 0 else "-"
            )
            
        except Exception as e:
            error_msg = str(e)
            errors.append(f"{proj['project_code']}: {error_msg}")
            table.add_row(
                proj['project_code'],
                proj['client_code'],
                "ERROR",
                f"[red]✗ Failed[/red]",
                "-"
            )
    
    console.print(table)
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total active projects: {total_projects}")
    if not dry_run:
        console.print(f"  Directories created: {total_dirs_created}")
    console.print(f"  Errors: {len(errors)}")
    
    if errors:
        console.print("\n[red]Errors:[/red]")
        for error in errors[:5]:  # Show first 5 errors
            console.print(f"  [red]✗[/red] {error}")
        if len(errors) > 5:
            console.print(f"  [dim]... and {len(errors) - 5} more errors[/dim]")
    
    if not dry_run and total_dirs_created > 0:
        console.print(f"\n[bold green]✓ Directory initialization complete![/bold green]\n")
    elif dry_run:
        console.print(f"\n[yellow]This was a dry run. Run without --dry-run to create directories.[/yellow]\n")
    else:
        console.print(f"\n[dim]All active project directories already exist.[/dim]\n")

