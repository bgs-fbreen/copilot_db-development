"""
Data cleanup commands
"""
import click
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query, get_connection
from datetime import date

console = Console()

@click.group()
def cleanup():
    """Data cleanup commands"""
    pass

@cleanup.command('delete-client')
@click.argument('client_code')
@click.option('--force', is_flag=True, help='Skip confirmation')
def delete_client(client_code, force):
    """Delete a client and all related data"""
    
    # Get client info
    client = execute_query("""
        SELECT 
            c.code,
            c.name,
            COUNT(p.project_code) as project_count
        FROM bgs.client c
        LEFT JOIN bgs.project p ON p.client_code = c.code
        WHERE c.code = %s
        GROUP BY c.code, c.name
    """, (client_code,))
    
    if not client:
        console.print(f"[red]Client '{client_code}' not found[/red]")
        return
    
    c = client[0]
    
    console.print(f"\n[bold red]⚠ DELETE CLIENT[/bold red]\n")
    console.print(f"[bold]Client:[/bold] {c['name']} ({c['code']})")
    console.print(f"[bold]Projects:[/bold] {c['project_count']}\n")
    
    console.print("[yellow]This will DELETE:[/yellow]")
    console.print("  • Client record")
    console.print("  • All projects")
    console.print("  • All timesheets")
    console.print("  • All baseline data")
    console.print("  • All tasks")
    console.print("  • All invoices and invoice items\n")
    
    if not force:
        if not click.confirm('Are you absolutely sure?', default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Delete in transaction
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get project codes for this client
            cur.execute("SELECT project_code FROM bgs.project WHERE client_code = %s", (client_code,))
            projects = [row[0] for row in cur.fetchall()]
            
            if projects:
                # Delete timesheets
                cur.execute("""
                    DELETE FROM bgs.timesheet 
                    WHERE project_code = ANY(%s)
                """, (projects,))
                
                # Delete baseline
                cur.execute("""
                    DELETE FROM bgs.baseline 
                    WHERE project_code = ANY(%s)
                """, (projects,))
                
                # Delete tasks
                cur.execute("""
                    DELETE FROM bgs.task 
                    WHERE project_code = ANY(%s)
                """, (projects,))
                
                # Delete invoice items
                cur.execute("""
                    DELETE FROM bgs.invoice_item 
                    WHERE invoice_code IN (
                        SELECT invoice_code FROM bgs.invoice 
                        WHERE project_code = ANY(%s)
                    )
                """, (projects,))
                
                # Delete invoices
                cur.execute("""
                    DELETE FROM bgs.invoice 
                    WHERE project_code = ANY(%s)
                """, (projects,))
                
                # Delete projects
                cur.execute("""
                    DELETE FROM bgs.project 
                    WHERE client_code = %s
                """, (client_code,))
            
            # Delete client
            cur.execute("DELETE FROM bgs.client WHERE code = %s", (client_code,))
            
            conn.commit()
            console.print(f"\n[bold green]✓ Client '{client_code}' deleted[/bold green]\n")
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error: {e}[/red]")
    finally:
        conn.close()

@cleanup.command('close-projects')
@click.argument('client_code')
@click.option('--force', is_flag=True, help='Skip confirmation')
def close_projects(client_code, force):
    """Close all projects for a client"""
    
    # Get projects
    projects = execute_query("""
        SELECT 
            p.project_code,
            p.project_name,
            p.status,
            c.name as client_name
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.client_code = %s
        ORDER BY p.project_code
    """, (client_code,))
    
    if not projects:
        console.print(f"[yellow]No projects found for client '{client_code}'[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Close Projects for {projects[0]['client_name']}[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project Code", style="cyan")
    table.add_column("Project Name", style="white")
    table.add_column("Current Status", style="yellow")
    
    active_count = 0
    for p in projects:
        table.add_row(
            p['project_code'],
            p['project_name'][:50] if p['project_name'] else '',
            p['status']
        )
        if p['status'] == 'active':
            active_count += 1
    
    console.print(table)
    console.print(f"\n[bold]Will close {active_count} active projects[/bold]\n")
    
    if active_count == 0:
        console.print("[yellow]No active projects to close[/yellow]")
        return
    
    if not force:
        if not click.confirm('Close all active projects?', default=True):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Close projects
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE bgs.project 
                SET 
                    status = 'complete',
                    end_date = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE client_code = %s
                  AND status = 'active'
            """, (date.today(), client_code))
            
            conn.commit()
            console.print(f"\n[bold green]✓ Closed {active_count} projects[/bold green]\n")
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error: {e}[/red]")
    finally:
        conn.close()

