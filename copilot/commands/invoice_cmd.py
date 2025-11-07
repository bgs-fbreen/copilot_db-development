"""
Invoice management command for BGS
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, execute_insert, get_connection
from datetime import datetime, date, timedelta
from decimal import Decimal
import os

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

@click.group()
def invoice():
    """Invoice management for BGS projects"""
    pass

@invoice.command('create')
@click.option('--project', '-p', help='Project code to invoice')
@click.option('--date', '-d', help='Invoice date (YYYY-MM-DD), default: today')
@click.option('--auto', is_flag=True, help='Auto-generate invoice without prompts')
def create_invoice(project, date, auto):
    """Create invoice from unbilled timesheets"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Create Invoice[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Get invoice date
    if not date:
        if auto:
            invoice_date = datetime.now().date()
        else:
            date_str = Prompt.ask('Invoice Date', default=datetime.now().strftime('%Y-%m-%d'))
            try:
                invoice_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                console.print(f"[red]Invalid date format: {date_str}[/red]")
                return
    else:
        try:
            invoice_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            console.print(f"[red]Invalid date format: {date}[/red]")
            return
    
    # Get projects with unbilled time
    if project:
        projects = execute_query("""
            SELECT 
                p.project_code,
                p.project_name,
                p.client_code,
                c.name as client_name,
                COUNT(t.id) as unbilled_count,
                SUM(t.ts_units) as total_hours,
                SUM(t.ts_mileage) as total_miles,
                SUM(t.ts_expense) as total_expenses
            FROM bgs.project p
            JOIN bgs.client c ON c.code = p.client_code
            JOIN bgs.timesheet t ON t.project_code = p.project_code
            WHERE t.invoice_code IS NULL
              AND p.project_code = %s
            GROUP BY p.project_code, p.project_name, p.client_code, c.name
        """, (project,))
    else:
        projects = execute_query("""
            SELECT 
                p.project_code,
                p.project_name,
                p.client_code,
                c.name as client_name,
                COUNT(t.id) as unbilled_count,
                SUM(t.ts_units) as total_hours,
                SUM(t.ts_mileage) as total_miles,
                SUM(t.ts_expense) as total_expenses
            FROM bgs.project p
            JOIN bgs.client c ON c.code = p.client_code
            JOIN bgs.timesheet t ON t.project_code = p.project_code
            WHERE t.invoice_code IS NULL
            GROUP BY p.project_code, p.project_name, p.client_code, c.name
            ORDER BY p.project_code
        """)
    
    if not projects:
        console.print("[yellow]No unbilled time entries found.[/yellow]")
        if project:
            console.print(f"[yellow]Project: {project}[/yellow]")
        return
    
    # Display projects with unbilled time
    console.print("[bold]Projects with Unbilled Time:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Project Name", style="white")
    table.add_column("Entries", justify="right", style="yellow")
    table.add_column("Hours", justify="right")
    table.add_column("Miles", justify="right")
    table.add_column("Expenses", justify="right")
    
    for proj in projects:
        table.add_row(
            proj['project_code'],
            proj['client_code'],
            (proj['project_name'] or '')[:40],
            str(proj['unbilled_count']),
            f"{float(proj['total_hours']):.1f}",
            f"{float(proj['total_miles'] or 0):.1f}",
            f"${float(proj['total_expenses'] or 0):.2f}"
        )
    
    console.print(table)
    console.print()
    
    # Select project if not provided
    if not project:
        if auto:
            console.print("[red]Error: --project required with --auto[/red]")
            return
        project = Prompt.ask('Project Code to invoice')
    
    # Verify project
    proj_data = [p for p in projects if p['project_code'] == project]
    if not proj_data:
        console.print(f"[red]Project '{project}' not found or has no unbilled time[/red]")
        return
    
    proj = proj_data[0]
    
    # Get unbilled timesheets for this project
    timesheets = execute_query("""
        SELECT 
            t.id,
            t.ts_date,
            t.task_no,
            t.sub_task_no,
            t.res_id,
            r.res_name,
            t.ts_units,
            t.ts_mileage,
            t.ts_expense,
            t.ts_desc,
            b.base_rate,
            b.base_miles_rate
        FROM bgs.timesheet t
        LEFT JOIN bgs.resource r ON r.res_id = t.res_id
        LEFT JOIN bgs.baseline b ON 
            b.project_code = t.project_code AND
            b.task_no = t.task_no AND
            b.sub_task_no = t.sub_task_no AND
            b.res_id = t.res_id
        WHERE t.project_code = %s
          AND t.invoice_code IS NULL
        ORDER BY t.ts_date, t.task_no, t.sub_task_no
    """, (project,))
    
    if not timesheets:
        console.print(f"[yellow]No unbilled timesheets for project {project}[/yellow]")
        return
    
    # Show timesheet details
    console.print(f"\n[bold green]Project:[/bold green] {proj['project_name']}")
    console.print(f"[bold green]Client:[/bold green] {proj['client_name']}\n")
    
    ts_table = Table(show_header=True, header_style="bold magenta")
    ts_table.add_column("Date", style="cyan")
    ts_table.add_column("Task", style="yellow")
    ts_table.add_column("Resource", style="green")
    ts_table.add_column("Hours", justify="right")
    ts_table.add_column("Rate", justify="right")
    ts_table.add_column("Amount", justify="right", style="white")
    ts_table.add_column("Miles", justify="right")
    ts_table.add_column("M-Rate", justify="right")
    ts_table.add_column("M-Amt", justify="right", style="white")
    ts_table.add_column("Expense", justify="right", style="white")
    ts_table.add_column("Total", justify="right", style="bold white")
    
    total_amount = Decimal('0.00')
    
    for ts in timesheets:
        hours = Decimal(str(ts['ts_units']))
        rate = Decimal(str(ts['base_rate'] or 0))
        miles = Decimal(str(ts['ts_mileage'] or 0))
        mile_rate = Decimal(str(ts['base_miles_rate'] or 0))
        expense = Decimal(str(ts['ts_expense'] or 0))
        
        labor_amt = hours * rate
        mile_amt = miles * mile_rate
        line_total = labor_amt + mile_amt + expense
        
        total_amount += line_total
        
        task_display = f"{ts['task_no']}/{ts['sub_task_no']}"
        
        ts_table.add_row(
            ts['ts_date'].strftime('%Y-%m-%d'),
            task_display,
            ts['res_id'],
            f"{hours:.1f}",
            f"${rate:.2f}",
            f"${labor_amt:.2f}",
            f"{miles:.1f}" if miles > 0 else "",
            f"${mile_rate:.2f}" if miles > 0 else "",
            f"${mile_amt:.2f}" if miles > 0 else "",
            f"${expense:.2f}" if expense > 0 else "",
            f"${line_total:.2f}"
        )
    
    console.print(ts_table)
    console.print(f"\n[bold]Invoice Total: ${total_amount:,.2f}[/bold]\n")
    
    # Confirm creation
    if not auto:
        if not Confirm.ask(f"Create invoice for ${total_amount:,.2f}?", default=True):
            console.print("[yellow]Invoice creation cancelled[/yellow]")
            return
    
    # Generate invoice code and number
    year = invoice_date.year
    
    # Get next invoice number for this year
    last_invoice = execute_query("""
        SELECT MAX(invoice_number) as last_num
        FROM bgs.invoice
        WHERE project_code = %s
          AND EXTRACT(YEAR FROM invoice_date) = %s
    """, (project, year))
    
    if last_invoice and last_invoice[0]['last_num']:
        invoice_number = last_invoice[0]['last_num'] + 1
    else:
        invoice_number = 1
    
    invoice_code = f"{project}.{invoice_number:04d}"
    
    # Calculate due date (30 days from invoice date)
    due_date = invoice_date + timedelta(days=30)
    
    # Create invoice
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Insert invoice header
            cur.execute("""
                INSERT INTO bgs.invoice
                (invoice_code, project_code, invoice_number, invoice_date, 
                 due_date, amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (invoice_code, project, invoice_number, invoice_date,
                  due_date, total_amount, 'pending'))
            
            # Group timesheets by task for invoice line items
            line_num = 1
            task_groups = {}
            
            for ts in timesheets:
                task_key = f"{ts['task_no']}/{ts['sub_task_no']}"
                if task_key not in task_groups:
                    task_groups[task_key] = {
                        'hours': Decimal('0'),
                        'rate': Decimal(str(ts['base_rate'] or 0)),
                        'miles': Decimal('0'),
                        'mile_rate': Decimal(str(ts['base_miles_rate'] or 0)),
                        'expenses': Decimal('0'),
                        'description': f"Task {task_key}",
                        'res_name': ts['res_name'] or ts['res_id']
                    }
                
                task_groups[task_key]['hours'] += Decimal(str(ts['ts_units']))
                task_groups[task_key]['miles'] += Decimal(str(ts['ts_mileage'] or 0))
                task_groups[task_key]['expenses'] += Decimal(str(ts['ts_expense'] or 0))
            
            # Create invoice line items
            for task_key, group in task_groups.items():
                # Labor line
                if group['hours'] > 0:
                    labor_desc = f"{group['description']} - {group['res_name']}"
                    labor_amt = group['hours'] * group['rate']
                    
                    cur.execute("""
                        INSERT INTO bgs.invoice_item
                        (invoice_code, line_number, description, quantity, unit_price, amount)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (invoice_code, line_num, labor_desc, group['hours'], 
                          group['rate'], labor_amt))
                    line_num += 1
                
                # Mileage line
                if group['miles'] > 0:
                    mile_desc = f"{group['description']} - Mileage"
                    mile_amt = group['miles'] * group['mile_rate']
                    
                    cur.execute("""
                        INSERT INTO bgs.invoice_item
                        (invoice_code, line_number, description, quantity, unit_price, amount)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (invoice_code, line_num, mile_desc, group['miles'],
                          group['mile_rate'], mile_amt))
                    line_num += 1
                
                # Expense line
                if group['expenses'] > 0:
                    exp_desc = f"{group['description']} - Expenses"
                    
                    cur.execute("""
                        INSERT INTO bgs.invoice_item
                        (invoice_code, line_number, description, quantity, unit_price, amount)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (invoice_code, line_num, exp_desc, 1,
                          group['expenses'], group['expenses']))
                    line_num += 1
            
            # Update timesheets with invoice_code
            timesheet_ids = [ts['id'] for ts in timesheets]
            cur.execute("""
                UPDATE bgs.timesheet
                SET invoice_code = %s
                WHERE id = ANY(%s)
            """, (invoice_code, timesheet_ids))
            
            conn.commit()
            
            console.print(f"\n[bold green]✓ Invoice created successfully![/bold green]")
            console.print(f"[green]Invoice Code:[/green] {invoice_code}")
            console.print(f"[green]Invoice Number:[/green] {invoice_number}")
            console.print(f"[green]Amount:[/green] ${total_amount:,.2f}")
            console.print(f"[green]Due Date:[/green] {due_date.strftime('%Y-%m-%d')}\n")
            
            # Add invoice to project workbook
            try:
                from copilot.commands.project_workbook_cmd import add_invoice_sheet, get_or_create_workbook, create_baseline_sheet
                wb, filepath, is_new = get_or_create_workbook(proj['client_code'], project)
                
                # If new workbook, create baseline first
                if is_new:
                    console.print("[yellow]Creating baseline sheet in workbook...[/yellow]")
                    create_baseline_sheet(wb, project)
                
                # Add invoice sheet
                if add_invoice_sheet(wb, invoice_code):
                    wb.save(filepath)
                    console.print(f"[green]✓ Added to workbook:[/green] {filepath}")
                    console.print(f"[dim]Sheet: {invoice_number:04d}[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not add to workbook: {e}[/yellow]\n")
            
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error creating invoice: {e}[/red]")
    finally:
        conn.close()

@invoice.command('list')
@click.option('--project', '-p', help='Filter by project code')
@click.option('--status', '-s', help='Filter by status (pending/paid/cancelled)')
@click.option('--all', is_flag=True, help='Show all invoices including paid')
def list_invoices(project, status, all):
    """List invoices"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Invoice List[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Build query
    where_clauses = []
    params = []
    
    if project:
        where_clauses.append("i.project_code = %s")
        params.append(project)
    
    if status:
        where_clauses.append("i.status = %s")
        params.append(status)
    elif not all:
        where_clauses.append("i.status = 'pending'")
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    invoices = execute_query(f"""
        SELECT
            i.invoice_code,
            i.project_code,
            i.invoice_number,
            i.invoice_date,
            i.due_date,
            i.amount,
            i.paid_amount,
            i.status,
            i.payment_date,
            p.project_name,
            c.code as client_code,
            c.name as client_name
        FROM bgs.invoice i
        JOIN bgs.project p ON p.project_code = i.project_code
        JOIN bgs.client c ON c.code = p.client_code
        {where_sql}
        ORDER BY i.invoice_date DESC, i.invoice_number DESC
    """, params if params else None)
    
    if not invoices:
        console.print("[yellow]No invoices found[/yellow]\n")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Invoice", style="cyan")
    table.add_column("Project", style="green")
    table.add_column("Client", style="white")
    table.add_column("Date", style="yellow")
    table.add_column("Due Date")
    table.add_column("Amount", justify="right", style="white")
    table.add_column("Paid", justify="right", style="green")
    table.add_column("Balance", justify="right", style="bold white")
    table.add_column("Status")
    
    total_amount = Decimal('0')
    total_paid = Decimal('0')
    total_balance = Decimal('0')
    
    for inv in invoices:
        amount = Decimal(str(inv['amount'] or 0))
        paid = Decimal(str(inv['paid_amount'] or 0))
        balance = amount - paid
        
        total_amount += amount
        total_paid += paid
        total_balance += balance
        
        # Status styling
        status_styles = {
            'draft': 'dim',
            'pending': 'yellow',
            'paid': 'green',
            'cancelled': 'red'
        }
        status_style = status_styles.get(inv['status'], 'white')
        
        inv_display = f".{inv['invoice_number']:04d}"
        
        table.add_row(
            inv_display,
            inv['project_code'],
            inv['client_code'],
            inv['invoice_date'].strftime('%Y-%m-%d'),
            inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else '',
            f"${amount:,.2f}",
            f"${paid:,.2f}" if paid > 0 else "",
            f"${balance:,.2f}" if balance > 0 else "",
            f"[{status_style}]{inv['status']}[/{status_style}]"
        )
    
    console.print(table)
    
    # Totals
    console.print(f"\n[bold]Total Amount:[/bold] ${total_amount:,.2f}")
    console.print(f"[bold]Total Paid:[/bold] ${total_paid:,.2f}")
    console.print(f"[bold]Balance Due:[/bold] ${total_balance:,.2f}\n")

@invoice.command('show')
@click.argument('invoice_code')
def show_invoice(invoice_code):
    """Show detailed invoice information"""
    
    clear_screen()
    
    # Get invoice header
    invoice = execute_query("""
        SELECT
            i.*,
            p.project_name,
            c.code as client_code,
            c.name as client_name,
            c.address,
            c.city,
            c.state,
            c.zip
        FROM bgs.invoice i
        JOIN bgs.project p ON p.project_code = i.project_code
        JOIN bgs.client c ON c.code = p.client_code
        WHERE i.invoice_code = %s
    """, (invoice_code,))
    
    if not invoice:
        console.print(f"[red]Invoice '{invoice_code}' not found[/red]")
        return
    
    inv = invoice[0]
    
    # Get invoice line items
    items = execute_query("""
        SELECT *
        FROM bgs.invoice_item
        WHERE invoice_code = %s
        ORDER BY line_number
    """, (invoice_code,))
    
    # Display invoice
    console.print(f"\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Invoice {inv['invoice_number']:04d}[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"[bold]Invoice Code:[/bold] {inv['invoice_code']}")
    console.print(f"[bold]Status:[/bold] {inv['status']}")
    console.print(f"[bold]Invoice Date:[/bold] {inv['invoice_date'].strftime('%Y-%m-%d')}")
    console.print(f"[bold]Due Date:[/bold] {inv['due_date'].strftime('%Y-%m-%d')}" if inv['due_date'] else "")
    console.print()
    
    console.print(f"[bold green]Client:[/bold green] {inv['client_name']}")
    console.print(f"[bold green]Project:[/bold green] {inv['project_code']} - {inv['project_name']}")
    console.print()
    
    # Line items table
    table = Table(show_header=True, header_style="bold magenta", title="Invoice Line Items")
    table.add_column("Line", justify="right", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Quantity", justify="right")
    table.add_column("Unit Price", justify="right")
    table.add_column("Amount", justify="right", style="bold white")
    
    for item in items:
        qty = Decimal(str(item['quantity'] or 0))
        price = Decimal(str(item['unit_price'] or 0))
        amount = Decimal(str(item['amount'] or 0))
        
        table.add_row(
            str(item['line_number']),
            item['description'],
            f"{qty:.2f}",
            f"${price:.2f}",
            f"${amount:.2f}"
        )
    
    console.print(table)
    
    # Totals
    amount = Decimal(str(inv['amount'] or 0))
    paid = Decimal(str(inv['paid_amount'] or 0))
    balance = amount - paid
    
    console.print()
    console.print(f"[bold]Invoice Amount:[/bold] ${amount:,.2f}")
    if paid > 0:
        console.print(f"[bold green]Amount Paid:[/bold green] ${paid:,.2f}")
        console.print(f"[bold]Balance Due:[/bold] ${balance:,.2f}")
    console.print()

@invoice.command('update')
@click.argument('invoice_code')
@click.option('--status', help='Update status (pending/paid/cancelled)')
@click.option('--paid', type=float, help='Amount paid')
@click.option('--payment-date', help='Payment date (YYYY-MM-DD)')
@click.option('--payment-method', help='Payment method (check/wire/ach/credit)')
@click.option('--check-number', help='Check number')
def update_invoice(invoice_code, status, paid, payment_date, payment_method, check_number):
    """Update invoice status and payment information"""
    
    # Get current invoice
    invoice = execute_query("""
        SELECT * FROM bgs.invoice WHERE invoice_code = %s
    """, (invoice_code,))
    
    if not invoice:
        console.print(f"[red]Invoice '{invoice_code}' not found[/red]")
        return
    
    inv = invoice[0]
    
    console.print(f"\n[bold cyan]Updating Invoice {invoice_code}[/bold cyan]\n")
    console.print(f"Current Status: {inv['status']}")
    console.print(f"Current Amount: ${Decimal(str(inv['amount'])):,.2f}")
    console.print(f"Current Paid: ${Decimal(str(inv['paid_amount'] or 0)):,.2f}\n")
    
    # Build update
    updates = []
    params = []
    
    if status:
        updates.append("status = %s")
        params.append(status)
    
    if paid is not None:
        updates.append("paid_amount = %s")
        params.append(Decimal(str(paid)))
        
        # Auto-set status to paid if full amount
        if Decimal(str(paid)) >= Decimal(str(inv['amount'])):
            if 'status' not in [u.split('=')[0].strip() for u in updates]:
                updates.append("status = %s")
                params.append('paid')
    
    if payment_date:
        try:
            pd = datetime.strptime(payment_date, '%Y-%m-%d').date()
            updates.append("payment_date = %s")
            params.append(pd)
        except ValueError:
            console.print(f"[red]Invalid date format: {payment_date}[/red]")
            return
    
    if payment_method:
        updates.append("payment_method = %s")
        params.append(payment_method)
    
    if check_number:
        updates.append("check_number = %s")
        params.append(check_number)
    
    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        return
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(invoice_code)
    
    # Execute update
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = f"UPDATE bgs.invoice SET {', '.join(updates)} WHERE invoice_code = %s"
            cur.execute(sql, params)
            conn.commit()
            
            console.print("[bold green]✓ Invoice updated successfully![/bold green]\n")
            
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error updating invoice: {e}[/red]")
    finally:
        conn.close()


# Import and register export command
from copilot.commands.invoice_export_cmd import export_invoice
invoice.add_command(export_invoice)

# Import and register baseline export command
from copilot.commands.baseline_export_cmd import export_baseline
invoice.add_command(export_baseline)

# Import and register workbook commands
from copilot.commands.project_workbook_cmd import create_workbook, add_invoice_to_workbook
invoice.add_command(create_workbook)
invoice.add_command(add_invoice_to_workbook)
