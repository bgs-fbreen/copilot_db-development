"""
Comprehensive project setup - Generate all baselines and invoices for active projects
"""
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from copilot.db import execute_query
import os

console = Console()

@click.command('setup-all')
@click.option('--dry-run', is_flag=True, help='Show what would be created without creating')
@click.option('--skip-baseline', is_flag=True, help='Skip baseline generation')
@click.option('--skip-invoices', is_flag=True, help='Skip invoice generation')
def setup_all_projects(dry_run, skip_baseline, skip_invoices):
    """
    Comprehensive setup for all active projects:
    1. Create directory structure
    2. Generate PDF baseline (01_baseline/)
    3. Generate XLSX workbook with baseline sheet (02_invoices/)
    4. Add all invoices as sheets to XLSX workbook
    """
    
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Setup All Active Projects[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    if dry_run:
        console.print("[yellow]DRY RUN - No files will be created[/yellow]\n")
    
    # Import required modules
    try:
        from copilot.commands.project_init_cmd import create_project_directories
        from copilot.commands.baseline_export_cmd import export_baseline_pdf, get_baseline_data
        from copilot.commands.project_workbook_cmd import (
            create_baseline_sheet, add_invoice_sheet, get_or_create_workbook
        )
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        return
    
    # Get all active projects
    projects = execute_query("""
        SELECT 
            p.project_code,
            p.project_name,
            p.client_code,
            c.name as client_name
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.status = 'active'
        ORDER BY p.client_code, p.project_code
    """)
    
    if not projects:
        console.print("[yellow]No active projects found[/yellow]")
        return
    
    console.print(f"[bold]Found {len(projects)} active projects[/bold]\n")
    
    # Statistics
    stats = {
        'total_projects': len(projects),
        'dirs_created': 0,
        'baseline_pdfs': 0,
        'baseline_xlsx': 0,
        'invoices_added': 0,
        'errors': []
    }
    
    # Process each project
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing projects...", total=len(projects))
        
        for proj in projects:
            project_code = proj['project_code']
            project_name = proj['project_name']
            client_code = proj['client_code']
            
            progress.update(task, description=f"[cyan]Processing {project_code}...")
            
            try:
                if not dry_run:
                    # 1. Create directory structure
                    create_project_directories(client_code, project_code, project_name)
                    stats['dirs_created'] += 1
                    
                    # 2. Generate PDF baseline
                    if not skip_baseline:
                        baseline_data = get_baseline_data(project_code)
                        if baseline_data:
                            from copilot.utils import get_project_directory_name
                            base_dir = "/mnt/sda1/01_bgm_projman/Active"
                            if not os.path.exists(base_dir):
                                base_dir = os.path.expanduser("~/bgm_projects/Active")
                            
                            dir_name = get_project_directory_name(project_code, project_name)
                            output_dir = os.path.join(base_dir, client_code, dir_name, '01_baseline')
                            
                            pdf_file = export_baseline_pdf(baseline_data, output_dir)
                            if pdf_file:
                                stats['baseline_pdfs'] += 1
                    
                    # 3. Create/update XLSX workbook with baseline
                    if not skip_baseline:
                        wb, filepath, is_new = get_or_create_workbook(client_code, project_code, project_name)
                        
                        # Add/update baseline sheet
                        if create_baseline_sheet(wb, project_code):
                            stats['baseline_xlsx'] += 1
                        
                        # Save workbook
                        wb.save(filepath)
                    
                    # 4. Add all invoices to workbook
                    if not skip_invoices:
                        # Get all invoices for this project
                        invoices = execute_query("""
                            SELECT invoice_code, invoice_number
                            FROM bgs.invoice
                            WHERE project_code = %s
                            ORDER BY invoice_number
                        """, (project_code,))
                        
                        if invoices:
                            # Get or load workbook
                            wb, filepath, is_new = get_or_create_workbook(client_code, project_code, project_name)
                            
                            for inv in invoices:
                                if add_invoice_sheet(wb, inv['invoice_code']):
                                    stats['invoices_added'] += 1
                            
                            # Save workbook with all invoices
                            wb.save(filepath)
                
                else:
                    # Dry run - just count what would be done
                    baseline_data = get_baseline_data(project_code)
                    if baseline_data:
                        stats['baseline_pdfs'] += 1
                        stats['baseline_xlsx'] += 1
                    
                    # Count invoices
                    invoices = execute_query("""
                        SELECT COUNT(*) as count
                        FROM bgs.invoice
                        WHERE project_code = %s
                    """, (project_code,))
                    
                    if invoices:
                        stats['invoices_added'] += invoices[0]['count']
                
            except Exception as e:
                error_msg = f"{project_code}: {str(e)}"
                stats['errors'].append(error_msg)
                console.print(f"[red]✗ Error processing {project_code}: {e}[/red]")
            
            progress.update(task, advance=1)
    
    # Display summary
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Summary[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Item", style="cyan")
    table.add_column("Count", justify="right", style="white")
    
    table.add_row("Projects processed", str(stats['total_projects']))
    if not skip_baseline:
        table.add_row("PDF baselines created", str(stats['baseline_pdfs']))
        table.add_row("XLSX baselines created", str(stats['baseline_xlsx']))
    if not skip_invoices:
        table.add_row("Invoice sheets added", str(stats['invoices_added']))
    table.add_row("Errors", f"[red]{len(stats['errors'])}[/red]" if stats['errors'] else "0")
    
    console.print(table)
    
    if stats['errors']:
        console.print("\n[red]Errors:[/red]")
        for error in stats['errors'][:10]:  # Show first 10 errors
            console.print(f"  [red]✗[/red] {error}")
        if len(stats['errors']) > 10:
            console.print(f"  [dim]... and {len(stats['errors']) - 10} more errors[/dim]")
    
    if not dry_run:
        console.print("\n[bold green]✓ Setup complete![/bold green]\n")
        console.print("Generated files:")
        console.print("  • PDF baselines in: {client}/{project}/01_baseline/")
        console.print("  • XLSX workbooks in: {client}/{project}/02_invoices/")
        console.print("    - Sheet 1: Baseline")
        console.print("    - Sheet 2+: Invoices (0001, 0002, ...)\n")
    else:
        console.print("\n[yellow]This was a dry run.[/yellow]")
        console.print("Run without --dry-run to generate files.\n")

