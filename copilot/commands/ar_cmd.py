"""
Accounts Receivable aging report command
"""
import click
from rich.console import Console
from rich.table import Table
from copilot.db import execute_query
from datetime import datetime, date, timedelta
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.command()
@click.option('--all', is_flag=True, help='Show all invoices including paid')
def ar(all):
    """Accounts Receivable aging report"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Accounts Receivable Report[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    today = date.today()
    console.print(f"[bold]Report Date:[/bold] {today.strftime('%B %d, %Y')}\n")
    
    # Query for outstanding invoices
    if all:
        status_filter = ""
    else:
        status_filter = "WHERE i.status = 'pending'"
    
    invoices = execute_query(f"""
        SELECT 
            i.invoice_code,
            i.project_code,
            c.code as client_code,
            c.name as client_name,
            i.invoice_number,
            i.invoice_date,
            i.due_date,
            i.amount,
            i.paid_amount,
            i.status,
            p.project_name
        FROM bgs.invoice i
        JOIN bgs.project p ON p.project_code = i.project_code
        JOIN bgs.client c ON c.code = p.client_code
        {status_filter}
        ORDER BY i.project_code ASC, i.invoice_number ASC
    """)
    
    if not invoices:
        console.print("[yellow]No outstanding invoices found[/yellow]\n")
        return
    
    # Create aging report table
    table = Table(
        show_header=True,
        header_style="bold magenta",
        title="[bold white]Outstanding Invoices - Aging Report[/bold white]",
        title_style="bold cyan"
    )
    
    table.add_column("Client", style="cyan")
    table.add_column("Project", style="green")
    table.add_column("Inv#", justify="right", style="yellow")
    table.add_column("Invoice Date", style="white")
    table.add_column("Due Date", style="white")
    table.add_column("Days", justify="right")
    table.add_column("Current\n(<30)", justify="right", style="green")
    table.add_column("30-60", justify="right", style="yellow")
    table.add_column("61-90", justify="right", style="red")
    table.add_column(">90", justify="right", style="bold red")
    table.add_column("Total", justify="right", style="bold white")
    
    # Totals
    total_current = 0
    total_30_60 = 0
    total_61_90 = 0
    total_over_90 = 0
    total_amount = 0
    
    # Client aging dictionary
    client_aging = {}
    
    for inv in invoices:
        invoice_date = inv['invoice_date']
        
        # Calculate due date: 30 days from invoice date if not specified
        if inv['due_date']:
            due_date = inv['due_date']
        else:
            due_date = invoice_date + timedelta(days=30)
        
        # Calculate days outstanding from invoice date (not due date)
        days_from_invoice = (today - invoice_date).days
        
        amount = float(inv['amount'] or 0)
        paid = float(inv['paid_amount'] or 0)
        balance = amount - paid
        
        # Skip if fully paid (when not showing all)
        if balance <= 0 and not all:
            continue
        
        # Categorize by aging based on invoice date
        current = 0
        days_30_60 = 0
        days_61_90 = 0
        over_90 = 0
        
        if days_from_invoice < 30:
            current = balance
        elif days_from_invoice < 61:
            days_30_60 = balance
        elif days_from_invoice < 91:
            days_61_90 = balance
        else:
            over_90 = balance
        
        total_current += current
        total_30_60 += days_30_60
        total_61_90 += days_61_90
        total_over_90 += over_90
        total_amount += balance
        
        # Track client aging
        client_code = inv['client_code']
        client_name = inv['client_name']
        
        if client_code not in client_aging:
            client_aging[client_code] = {
                'name': client_name,
                'current': 0,
                'days_30_60': 0,
                'days_61_90': 0,
                'over_90': 0,
                'total': 0
            }
        
        client_aging[client_code]['current'] += current
        client_aging[client_code]['days_30_60'] += days_30_60
        client_aging[client_code]['days_61_90'] += days_61_90
        client_aging[client_code]['over_90'] += over_90
        client_aging[client_code]['total'] += balance
        
        # Color code days outstanding
        if days_from_invoice < 30:
            days_color = "green"
            days_text = f"[{days_color}]{days_from_invoice}[/{days_color}]"
        elif days_from_invoice < 61:
            days_color = "yellow"
            days_text = f"[{days_color}]{days_from_invoice}[/{days_color}]"
        elif days_from_invoice < 91:
            days_color = "red"
            days_text = f"[{days_color}]{days_from_invoice}[/{days_color}]"
        else:
            days_color = "bold red"
            days_text = f"[{days_color}]{days_from_invoice}[/{days_color}]"
        
        # Status indicator
        status_style = ""
        if inv['status'] == 'paid':
            status_style = "[dim]"
        
        # Format invoice number as 4-digit suffix
        inv_display = f".{inv['invoice_number']:04d}"
        
        table.add_row(
            f"{status_style}{inv['client_code']}",
            f"{status_style}{inv['project_code']}",
            f"{status_style}{inv_display}",
            f"{status_style}{invoice_date.strftime('%Y-%m-%d')}",
            f"{status_style}{due_date.strftime('%Y-%m-%d')}",
            days_text if inv['status'] != 'paid' else f"{status_style}{days_from_invoice}",
            f"{status_style}${current:,.2f}" if current > 0 else "",
            f"{status_style}${days_30_60:,.2f}" if days_30_60 > 0 else "",
            f"{status_style}${days_61_90:,.2f}" if days_61_90 > 0 else "",
            f"{status_style}${over_90:,.2f}" if over_90 > 0 else "",
            f"{status_style}${balance:,.2f}"
        )
    
    # Add totals row
    table.add_section()
    table.add_row(
        "[bold]TOTAL",
        "",
        "",
        "",
        "",
        "",
        f"[bold green]${total_current:,.2f}[/bold green]" if total_current > 0 else "",
        f"[bold yellow]${total_30_60:,.2f}[/bold yellow]" if total_30_60 > 0 else "",
        f"[bold red]${total_61_90:,.2f}[/bold red]" if total_61_90 > 0 else "",
        f"[bold red]${total_over_90:,.2f}[/bold red]" if total_over_90 > 0 else "",
        f"[bold]${total_amount:,.2f}[/bold]"
    )
    
    console.print(table)
    
    # Summary statistics
    console.print("\n[bold]Aging Summary:[/bold]")
    
    if total_amount > 0:
        pct_current = (total_current / total_amount) * 100
        pct_30_60 = (total_30_60 / total_amount) * 100
        pct_61_90 = (total_61_90 / total_amount) * 100
        pct_over_90 = (total_over_90 / total_amount) * 100
        
        console.print(f"  Current (<30 days):  ${total_current:>10,.2f}  ({pct_current:>5.1f}%)")
        console.print(f"  30-60 days:          ${total_30_60:>10,.2f}  ({pct_30_60:>5.1f}%)")
        console.print(f"  61-90 days:          ${total_61_90:>10,.2f}  ({pct_61_90:>5.1f}%)")
        console.print(f"  Over 90 days:        ${total_over_90:>10,.2f}  ({pct_over_90:>5.1f}%)")
        console.print(f"  {'─' * 42}")
        console.print(f"  [bold]Total Outstanding:   ${total_amount:>10,.2f}[/bold]")
    
    # Client Aging Summary Table
    console.print("\n")
    client_table = Table(
        show_header=True,
        header_style="bold magenta",
        title="[bold white]Aging Summary by Client[/bold white]",
        title_style="bold cyan"
    )
    
    client_table.add_column("Client", style="cyan")
    client_table.add_column("Client Name", style="white")
    client_table.add_column("Current\n(<30)", justify="right", style="green")
    client_table.add_column("30-60", justify="right", style="yellow")
    client_table.add_column("61-90", justify="right", style="red")
    client_table.add_column(">90", justify="right", style="bold red")
    client_table.add_column("Total", justify="right", style="bold white")
    client_table.add_column("%", justify="right")
    
    # Sort clients by total outstanding (descending)
    sorted_clients = sorted(client_aging.items(), key=lambda x: x[1]['total'], reverse=True)
    
    for client_code, aging in sorted_clients:
        client_pct = (aging['total'] / total_amount) * 100 if total_amount > 0 else 0
        
        client_table.add_row(
            client_code,
            aging['name'][:30],
            f"${aging['current']:,.2f}" if aging['current'] > 0 else "",
            f"${aging['days_30_60']:,.2f}" if aging['days_30_60'] > 0 else "",
            f"${aging['days_61_90']:,.2f}" if aging['days_61_90'] > 0 else "",
            f"${aging['over_90']:,.2f}" if aging['over_90'] > 0 else "",
            f"${aging['total']:,.2f}",
            f"{client_pct:.1f}%"
        )
    
    # Add client totals row
    client_table.add_section()
    client_table.add_row(
        "[bold]TOTAL",
        "",
        f"[bold green]${total_current:,.2f}[/bold green]" if total_current > 0 else "",
        f"[bold yellow]${total_30_60:,.2f}[/bold yellow]" if total_30_60 > 0 else "",
        f"[bold red]${total_61_90:,.2f}[/bold red]" if total_61_90 > 0 else "",
        f"[bold red]${total_over_90:,.2f}[/bold red]" if total_over_90 > 0 else "",
        f"[bold]${total_amount:,.2f}[/bold]",
        "[bold]100.0%[/bold]"
    )
    
    console.print(client_table)
    console.print()
