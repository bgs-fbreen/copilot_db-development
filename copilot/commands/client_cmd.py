"""
Client management command
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from copilot.db import execute_query, get_connection
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.group()
def client():
    """Manage client information"""
    pass

@client.command('list')
def list_clients():
    """List all clients"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Clients[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    clients = execute_query("""
        SELECT 
            code,
            name,
            contact_name,
            contact_phone,
            city,
            state,
            status
        FROM bgs.client
        ORDER BY code
    """)
    
    if not clients:
        console.print("[yellow]No clients found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Code", style="cyan")
    table.add_column("Client Name", style="green")
    table.add_column("Contact", style="white")
    table.add_column("Phone", style="yellow")
    table.add_column("Location")
    table.add_column("Status")
    
    for c in clients:
        location = f"{c['city']}, {c['state']}" if c['city'] and c['state'] else ""
        table.add_row(
            c['code'],
            c['name'],
            c['contact_name'] or "",
            c['contact_phone'] or "",
            location,
            c['status']
        )
    
    console.print(table)
    console.print()

@client.command('update')
@click.argument('client_code')
def update_client(client_code):
    """Update client contact and address information"""
    
    # Get current client data
    client = execute_query("""
        SELECT * FROM bgs.client WHERE code = %s
    """, (client_code,))
    
    if not client:
        console.print(f"[red]Client '{client_code}' not found[/red]")
        return
    
    c = client[0]
    
    clear_screen()
    console.print(f"\n[bold cyan]Update Client: {c['name']}[/bold cyan]\n")
    
    console.print("[dim]Press Enter to keep current value[/dim]\n")
    
    # Prompt for each field
    name = Prompt.ask("Client Name", default=c['name'] or "")
    
    console.print("\n[bold]Contact Information:[/bold]")
    contact_name = Prompt.ask("Contact Name", default=c['contact_name'] or "")
    contact_title = Prompt.ask("Contact Title", default=c.get('contact_title') or "")
    contact_phone = Prompt.ask("Contact Phone", default=c.get('contact_phone') or "")
    contact_email = Prompt.ask("Contact Email", default=c.get('contact_email') or c['email'] or "")
    
    console.print("\n[bold]Mailing Address:[/bold]")
    street = Prompt.ask("Street Address", default=c.get('street_address') or c['address'] or "")
    street2 = Prompt.ask("Street Address 2", default=c.get('street_address2') or "")
    city = Prompt.ask("City", default=c['city'] or "")
    state = Prompt.ask("State (2-letter)", default=c['state'] or "")
    zip_code = Prompt.ask("ZIP Code", default=c['zip'] or "")
    
    # Confirm update
    console.print("\n[bold yellow]Confirm Update:[/bold yellow]")
    console.print(f"  Client: {name}")
    console.print(f"  Contact: {contact_name}, {contact_title}")
    console.print(f"  Phone: {contact_phone}")
    console.print(f"  Email: {contact_email}")
    console.print(f"  Address: {street}")
    if street2:
        console.print(f"           {street2}")
    console.print(f"           {city}, {state} {zip_code}\n")
    
    if not click.confirm('Save changes?', default=True):
        console.print("[yellow]Update cancelled[/yellow]")
        return
    
    # Update database
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE bgs.client
                SET 
                    name = %s,
                    contact_name = %s,
                    contact_title = %s,
                    contact_phone = %s,
                    email = %s,
                    contact_email = %s,
                    street_address = %s,
                    street_address2 = %s,
                    address = %s,
                    city = %s,
                    state = %s,
                    zip = %s
                WHERE code = %s
            """, (name, contact_name, contact_title, contact_phone, 
                  contact_email, contact_email, street, street2,
                  street, city, state, zip_code, client_code))
            conn.commit()
            console.print("\n[bold green]✓ Client updated successfully![/bold green]\n")
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error updating client: {e}[/red]")
    finally:
        conn.close()

@client.command('show')
@click.argument('client_code')
def show_client(client_code):
    """Show detailed client information"""
    
    client = execute_query("""
        SELECT * FROM bgs.client WHERE code = %s
    """, (client_code,))
    
    if not client:
        console.print(f"[red]Client '{client_code}' not found[/red]")
        return
    
    c = client[0]
    
    console.print(f"\n[bold cyan]Client: {c['name']}[/bold cyan]\n")
    console.print(f"[bold]Code:[/bold] {c['code']}")
    console.print(f"[bold]Status:[/bold] {c['status']}\n")
    
    console.print("[bold]Contact Information:[/bold]")
    console.print(f"  Name: {c['contact_name'] or 'Not set'}")
    if c.get('contact_title'):
        console.print(f"  Title: {c['contact_title']}")
    console.print(f"  Phone: {c.get('contact_phone') or c['phone'] or 'Not set'}")
    console.print(f"  Email: {c.get('contact_email') or c['email'] or 'Not set'}\n")
    
    console.print("[bold]Mailing Address:[/bold]")
    if c.get('street_address'):
        console.print(f"  {c['street_address']}")
        if c.get('street_address2'):
            console.print(f"  {c['street_address2']}")
    elif c['address']:
        console.print(f"  {c['address']}")
    
    if c['city'] and c['state']:
        console.print(f"  {c['city']}, {c['state']} {c['zip'] or ''}\n")
    
    if c['notes']:
        console.print(f"[bold]Notes:[/bold]\n{c['notes']}\n")

