"""
Property tax tracking and management for personal and MHB properties.

Comprehensive property tax management system tracking:
- Tax bills with assessment information
- Millage breakdown by taxing authority
- Payment history with interest/penalty tracking
- Outstanding balance tracking and reporting
"""

import click
import csv
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, get_connection
from copilot.commands.help_utils import print_header, print_section, print_examples
from datetime import datetime
from decimal import Decimal

console = Console()

# ============================================================================
# MAIN COMMAND GROUP
# ============================================================================

@click.group()
def tax():
    """Property tax tracking and management"""
    pass

# ============================================================================
# IMPORT COMMANDS
# ============================================================================

@tax.command('import')
@click.option('-f', '--file', required=True, help='CSV file to import')
@click.option('-p', '--property', required=True, help='Property code')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb', 
              help='Database schema (per or mhb)')
def tax_import(file, property, schema):
    """Import tax bills from CSV file
    
    Expected CSV columns:
    - tax_year: Year (e.g., 2024)
    - tax_season: summer or winter
    - school_district: School district code
    - property_class: Property class (e.g., 401 for residential)
    - pre_pct: Principal Residence Exemption % as whole number (e.g., 18.00 for 18%)
    - assessed_value: SEV
    - taxable_value: Taxable value
    - total_millage: Total millage rate
    - base_tax: Base tax amount
    - admin_fee: Admin fee (optional)
    - total_due: Total amount due
    - due_date: Due date (YYYY-MM-DD)
    - bill_number: Bill number (optional)
    
    Optional millage detail columns (prefix with 'millage_'):
    - millage_<authority>: Amount for each taxing authority
    - rate_<authority>: Millage rate for each authority
    
    NOTE: pre_pct should be provided as a whole number (e.g., 18.00 for 18%). 
    The import process will automatically convert it to decimal format (0.18).
    """
    try:
        with open(file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            if not rows:
                console.print("[yellow]No data found in CSV file[/yellow]")
                return
            
            console.print(f"[cyan]Importing {len(rows)} tax bill(s) for property {property}...[/cyan]")
            
            conn = get_connection()
            imported = 0
            errors = 0
            
            # Note: Each tax bill (including its millage details) is committed as a single 
            # transaction unit. This allows partial imports - if one bill fails, others 
            # will still be imported successfully.
            try:
                for row in rows:
                    try:
                        # Parse basic bill data
                        tax_year = int(row['tax_year'])
                        tax_season = row['tax_season'].lower()
                        
                        # Convert PRE percentage (handle both whole number and decimal formats)
                        pre_pct = None
                        if row.get('pre_pct'):
                            pre_val = float(row['pre_pct'])
                            # If value is > 1, assume it's a whole number (e.g., 18.00 for 18%)
                            # If value is <= 1, assume it's already in decimal format (e.g., 0.18)
                            pre_pct = pre_val / 100.0 if pre_val > 1 else pre_val
                            # Validate range
                            if pre_pct < 0 or pre_pct > 1:
                                raise ValueError(f"PRE percentage out of range: {row['pre_pct']}")
                        
                        # Insert or update tax bill
                        bill_query = f"""
                            INSERT INTO {schema}.property_tax_bill 
                            (property_code, tax_year, tax_season, school_district, property_class,
                             pre_pct, assessed_value, taxable_value, total_millage, base_tax, 
                             admin_fee, total_due, due_date, bill_number, balance_due)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (property_code, tax_year, tax_season) 
                            DO UPDATE SET
                                school_district = EXCLUDED.school_district,
                                property_class = EXCLUDED.property_class,
                                pre_pct = EXCLUDED.pre_pct,
                                assessed_value = EXCLUDED.assessed_value,
                                taxable_value = EXCLUDED.taxable_value,
                                total_millage = EXCLUDED.total_millage,
                                base_tax = EXCLUDED.base_tax,
                                admin_fee = EXCLUDED.admin_fee,
                                total_due = EXCLUDED.total_due,
                                due_date = EXCLUDED.due_date,
                                bill_number = EXCLUDED.bill_number,
                                balance_due = EXCLUDED.balance_due,
                                updated_at = NOW()
                            RETURNING id
                        """
                        
                        with conn.cursor() as cur:
                            cur.execute(bill_query, (
                                property,
                                tax_year,
                                tax_season,
                                row.get('school_district'),
                                row.get('property_class'),
                                pre_pct,
                                float(row['assessed_value']) if row.get('assessed_value') else None,
                                float(row['taxable_value']) if row.get('taxable_value') else None,
                                float(row['total_millage']) if row.get('total_millage') else None,
                                float(row['base_tax']),
                                float(row.get('admin_fee', 0)),
                                float(row['total_due']),
                                row.get('due_date'),
                                row.get('bill_number'),
                                float(row['total_due'])  # Initial balance_due = total_due
                            ))
                            bill_id = cur.fetchone()[0]
                            
                            # Import millage details if present
                            millage_imported = 0
                            for key in row.keys():
                                if key.startswith('millage_'):
                                    authority = key.replace('millage_', '').replace('_', ' ').upper()
                                    amount = float(row[key])
                                    rate_key = f"rate_{key.replace('millage_', '')}"
                                    rate = float(row.get(rate_key, 0))
                                    
                                    if amount > 0:
                                        detail_query = f"""
                                            INSERT INTO {schema}.property_tax_detail
                                            (tax_bill_id, taxing_authority, millage_rate, amount)
                                            VALUES (%s, %s, %s, %s)
                                            ON CONFLICT (tax_bill_id, taxing_authority)
                                            DO UPDATE SET
                                                millage_rate = EXCLUDED.millage_rate,
                                                amount = EXCLUDED.amount
                                        """
                                        cur.execute(detail_query, (bill_id, authority, rate, amount))
                                        millage_imported += 1
                            
                            conn.commit()
                            imported += 1
                            
                            if millage_imported > 0:
                                console.print(f"  [green]✓[/green] {tax_year} {tax_season} - ${float(row['total_due']):,.2f} ({millage_imported} millage details)")
                            else:
                                console.print(f"  [green]✓[/green] {tax_year} {tax_season} - ${float(row['total_due']):,.2f}")
                    
                    except Exception as e:
                        errors += 1
                        console.print(f"  [red]✗[/red] Error importing row: {str(e)}")
                        conn.rollback()
            
            finally:
                conn.close()
            
            console.print(f"\n[green]Imported {imported} bill(s)[/green]")
            if errors > 0:
                console.print(f"[red]{errors} error(s)[/red]")
    
    except FileNotFoundError:
        console.print(f"[red]File not found: {file}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

# ============================================================================
# BILL MANAGEMENT COMMANDS
# ============================================================================

@tax.command('list')
@click.option('-p', '--property', help='Filter by property code')
@click.option('-y', '--year', type=int, help='Filter by tax year')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
@click.option('--status', type=click.Choice(['unpaid', 'partial', 'paid', 'delinquent']),
              help='Filter by payment status')
def list_bills(property, year, schema, status):
    """List all tax bills"""
    query = f"""
        SELECT id, property_code, tax_year, tax_season, 
               assessed_value, taxable_value, total_due, 
               total_paid, balance_due, status, due_date
        FROM {schema}.property_tax_bill
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND property_code = %s"
        params.append(property)
    if year:
        query += " AND tax_year = %s"
        params.append(year)
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY property_code, tax_year DESC, tax_season"
    
    bills = execute_query(query, params or None)
    
    if not bills:
        console.print("[yellow]No tax bills found[/yellow]")
        return
    
    table = Table(title=f"Property Tax Bills ({schema.upper()})")
    table.add_column("ID", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Year", style="white")
    table.add_column("Season", style="white")
    table.add_column("Assessed", style="white", justify="right")
    table.add_column("Taxable", style="white", justify="right")
    table.add_column("Total Due", style="green", justify="right")
    table.add_column("Paid", style="green", justify="right")
    table.add_column("Balance", style="yellow", justify="right")
    table.add_column("Status", style="white")
    table.add_column("Due Date", style="white")
    
    for bill in bills:
        status_color = {
            'paid': 'green',
            'partial': 'yellow',
            'unpaid': 'white',
            'delinquent': 'red'
        }.get(bill['status'], 'white')
        
        table.add_row(
            str(bill['id']),
            bill['property_code'],
            str(bill['tax_year']),
            bill['tax_season'].capitalize(),
            f"${bill['assessed_value']:,.2f}" if bill['assessed_value'] else 'N/A',
            f"${bill['taxable_value']:,.2f}" if bill['taxable_value'] else 'N/A',
            f"${bill['total_due']:,.2f}",
            f"${bill['total_paid']:,.2f}",
            f"${bill['balance_due']:,.2f}" if bill['balance_due'] else '$0.00',
            f"[{status_color}]{bill['status'].upper()}[/{status_color}]",
            bill['due_date'].strftime('%Y-%m-%d') if bill['due_date'] else 'N/A'
        )
    
    console.print(table)

@tax.command('show')
@click.argument('bill_id', type=int)
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def show_bill(bill_id, schema):
    """Show detailed bill information including millage breakdown"""
    # Get bill details
    bill_query = f"""
        SELECT * FROM {schema}.property_tax_bill
        WHERE id = %s
    """
    bills = execute_query(bill_query, (bill_id,))
    
    if not bills:
        console.print(f"[red]Bill {bill_id} not found[/red]")
        return
    
    bill = bills[0]
    
    console.print(f"\n[bold cyan]Tax Bill #{bill['id']}[/bold cyan]")
    console.print(f"Property: {bill['property_code']}")
    console.print(f"Tax Year: {bill['tax_year']} - {bill['tax_season'].capitalize()} Season")
    
    if bill['bill_number']:
        console.print(f"Bill Number: {bill['bill_number']}")
    
    console.print(f"\n[bold]Assessment Information:[/bold]")
    console.print(f"  School District: {bill['school_district'] or 'N/A'}")
    console.print(f"  Property Class: {bill['property_class'] or 'N/A'}")
    if bill['pre_pct']:
        console.print(f"  PRE Exemption: {bill['pre_pct']*100:.2f}%")
    console.print(f"  Assessed Value (SEV): ${bill['assessed_value']:,.2f}" if bill['assessed_value'] else "  Assessed Value: N/A")
    console.print(f"  Taxable Value: ${bill['taxable_value']:,.2f}" if bill['taxable_value'] else "  Taxable Value: N/A")
    
    console.print(f"\n[bold]Bill Amounts:[/bold]")
    if bill['total_millage']:
        console.print(f"  Total Millage Rate: {bill['total_millage']:.6f}")
    console.print(f"  Base Tax: ${bill['base_tax']:,.2f}")
    if bill['admin_fee'] and bill['admin_fee'] > 0:
        console.print(f"  Admin Fee: ${bill['admin_fee']:,.2f}")
    console.print(f"  [bold]Total Due: ${bill['total_due']:,.2f}[/bold]")
    
    console.print(f"\n[bold]Payment Information:[/bold]")
    console.print(f"  Total Paid: ${bill['total_paid']:,.2f}")
    if bill['interest_paid'] and bill['interest_paid'] > 0:
        console.print(f"  Interest Paid: ${bill['interest_paid']:,.2f}")
    console.print(f"  [bold]Balance Due: ${bill['balance_due']:,.2f}[/bold]" if bill['balance_due'] else "  [bold]Balance Due: $0.00[/bold]")
    
    status_color = {
        'paid': 'green',
        'partial': 'yellow',
        'unpaid': 'white',
        'delinquent': 'red'
    }.get(bill['status'], 'white')
    console.print(f"  Status: [{status_color}]{bill['status'].upper()}[/{status_color}]")
    
    if bill['due_date']:
        console.print(f"  Due Date: {bill['due_date'].strftime('%Y-%m-%d')}")
        if bill['balance_due'] and bill['balance_due'] > 0 and bill['due_date'] < datetime.now().date():
            days_overdue = (datetime.now().date() - bill['due_date']).days
            console.print(f"  [red]OVERDUE by {days_overdue} days[/red]")
    
    # Get millage breakdown
    detail_query = f"""
        SELECT taxing_authority, millage_rate, amount, amount_paid
        FROM {schema}.property_tax_detail
        WHERE tax_bill_id = %s
        ORDER BY amount DESC
    """
    details = execute_query(detail_query, (bill_id,))
    
    if details:
        console.print(f"\n[bold]Millage Breakdown:[/bold]")
        table = Table(show_header=True)
        table.add_column("Taxing Authority", style="white")
        table.add_column("Millage Rate", style="white", justify="right")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Paid", style="green", justify="right")
        
        for detail in details:
            table.add_row(
                detail['taxing_authority'],
                f"{detail['millage_rate']:.6f}",
                f"${detail['amount']:,.2f}",
                f"${detail['amount_paid']:,.2f}"
            )
        
        console.print(table)
    
    # Get payment history
    payment_query = f"""
        SELECT payment_date, amount, interest_amount, penalty_amount,
               total_payment, receipt_number, payment_method, paid_from
        FROM {schema}.property_tax_payment
        WHERE tax_bill_id = %s
        ORDER BY payment_date DESC
    """
    payments = execute_query(payment_query, (bill_id,))
    
    if payments:
        console.print(f"\n[bold]Payment History:[/bold]")
        table = Table(show_header=True)
        table.add_column("Date", style="white")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Interest", style="yellow", justify="right")
        table.add_column("Penalty", style="red", justify="right")
        table.add_column("Total", style="green", justify="right")
        table.add_column("Method", style="white")
        table.add_column("Receipt", style="dim")
        
        for payment in payments:
            table.add_row(
                payment['payment_date'].strftime('%Y-%m-%d'),
                f"${payment['amount']:,.2f}",
                f"${payment['interest_amount']:,.2f}" if payment['interest_amount'] else "-",
                f"${payment['penalty_amount']:,.2f}" if payment['penalty_amount'] else "-",
                f"${payment['total_payment']:,.2f}",
                payment['payment_method'] or 'N/A',
                payment['receipt_number'] or '-'
            )
        
        console.print(table)

# ============================================================================
# PAYMENT COMMANDS
# ============================================================================

@tax.command('add-payment')
@click.argument('bill_id', type=int)
@click.option('--date', required=True, help='Payment date (YYYY-MM-DD)')
@click.option('--amount', type=float, required=True, help='Payment amount')
@click.option('--interest', type=float, default=0, help='Interest amount')
@click.option('--penalty', type=float, default=0, help='Penalty amount')
@click.option('--method', default='check', help='Payment method (check, online, escrow)')
@click.option('--receipt', help='Receipt number')
@click.option('--paid-from', help='Payment source (escrow, direct, account code)')
@click.option('--notes', help='Payment notes')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def add_payment(bill_id, date, amount, interest, penalty, method, receipt, paid_from, notes, schema):
    """Record a tax payment"""
    total = amount + interest + penalty
    
    query = f"""
        INSERT INTO {schema}.property_tax_payment
        (tax_bill_id, payment_date, amount, interest_amount, penalty_amount,
         total_payment, receipt_number, payment_method, paid_from, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (
                bill_id, date, amount, interest, penalty, total,
                receipt, method, paid_from, notes
            ))
            payment_id = cur.fetchone()[0]
            conn.commit()
            
            console.print(f"[green]✓ Payment of ${total:,.2f} recorded (ID: {payment_id})[/green]")
            console.print(f"[dim]Principal: ${amount:,.2f}, Interest: ${interest:,.2f}, Penalty: ${penalty:,.2f}[/dim]")
    finally:
        conn.close()

@tax.command('payment-history')
@click.option('-p', '--property', help='Filter by property code')
@click.option('-y', '--year', type=int, help='Filter by tax year')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def payment_history(property, year, schema):
    """Show payment history"""
    query = f"""
        SELECT p.id, b.property_code, b.tax_year, b.tax_season,
               p.payment_date, p.amount, p.interest_amount, p.penalty_amount,
               p.total_payment, p.payment_method, p.receipt_number
        FROM {schema}.property_tax_payment p
        JOIN {schema}.property_tax_bill b ON b.id = p.tax_bill_id
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND b.property_code = %s"
        params.append(property)
    if year:
        query += " AND b.tax_year = %s"
        params.append(year)
    
    query += " ORDER BY p.payment_date DESC"
    
    payments = execute_query(query, params or None)
    
    if not payments:
        console.print("[yellow]No payments found[/yellow]")
        return
    
    table = Table(title=f"Payment History ({schema.upper()})")
    table.add_column("ID", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Year", style="white")
    table.add_column("Season", style="white")
    table.add_column("Date", style="white")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Interest", style="yellow", justify="right")
    table.add_column("Penalty", style="red", justify="right")
    table.add_column("Total", style="green", justify="right")
    table.add_column("Method", style="white")
    table.add_column("Receipt", style="dim")
    
    for payment in payments:
        table.add_row(
            str(payment['id']),
            payment['property_code'],
            str(payment['tax_year']),
            payment['tax_season'].capitalize(),
            payment['payment_date'].strftime('%Y-%m-%d'),
            f"${payment['amount']:,.2f}",
            f"${payment['interest_amount']:,.2f}" if payment['interest_amount'] else "-",
            f"${payment['penalty_amount']:,.2f}" if payment['penalty_amount'] else "-",
            f"${payment['total_payment']:,.2f}",
            payment['payment_method'] or 'N/A',
            payment['receipt_number'] or '-'
        )
    
    console.print(table)

# ============================================================================
# REPORTING COMMANDS
# ============================================================================

@tax.command('outstanding')
@click.option('-p', '--property', help='Filter by property code')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def outstanding(property, schema):
    """Show outstanding tax balances"""
    query = f"""
        SELECT * FROM {schema}.v_property_tax_outstanding
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND property_code = %s"
        params.append(property)
    
    balances = execute_query(query, params or None)
    
    if not balances:
        console.print("[green]No outstanding balances![/green]")
        return
    
    table = Table(title=f"Outstanding Tax Balances ({schema.upper()})")
    table.add_column("Property", style="cyan")
    table.add_column("Year", style="white")
    table.add_column("Season", style="white")
    table.add_column("Total Due", style="white", justify="right")
    table.add_column("Paid", style="green", justify="right")
    table.add_column("Balance", style="yellow", justify="right")
    table.add_column("Due Date", style="white")
    table.add_column("Status", style="white")
    table.add_column("Days Overdue", style="white", justify="right")
    
    total_balance = 0
    
    for balance in balances:
        status_color = {
            'OVERDUE': 'red',
            'DUE': 'yellow',
            'PAID': 'green'
        }.get(balance['payment_status'], 'white')
        
        total_balance += float(balance['balance_due'] or 0)
        
        table.add_row(
            balance['property_code'],
            str(balance['tax_year']),
            balance['tax_season'].capitalize(),
            f"${balance['total_due']:,.2f}",
            f"${balance['total_paid']:,.2f}",
            f"${balance['balance_due']:,.2f}" if balance['balance_due'] else '$0.00',
            balance['due_date'].strftime('%Y-%m-%d') if balance['due_date'] else 'N/A',
            f"[{status_color}]{balance['payment_status']}[/{status_color}]",
            str(balance['days_overdue']) if balance['days_overdue'] > 0 else '-'
        )
    
    console.print(table)
    console.print(f"\n[bold]Total Outstanding Balance: ${total_balance:,.2f}[/bold]")

@tax.command('history')
@click.option('-p', '--property', help='Filter by property code')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def tax_history(property, schema):
    """Show annual tax history summary"""
    query = f"""
        SELECT * FROM {schema}.v_property_tax_history
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND property_code = %s"
        params.append(property)
    
    history = execute_query(query, params or None)
    
    if not history:
        console.print("[yellow]No tax history found[/yellow]")
        return
    
    table = Table(title=f"Tax History Summary ({schema.upper()})")
    table.add_column("Property", style="cyan")
    table.add_column("Year", style="white")
    table.add_column("Summer Tax", style="white", justify="right")
    table.add_column("Winter Tax", style="white", justify="right")
    table.add_column("Annual Tax", style="green", justify="right")
    table.add_column("Paid", style="green", justify="right")
    table.add_column("Balance", style="yellow", justify="right")
    table.add_column("Assessed Value", style="white", justify="right")
    table.add_column("Taxable Value", style="white", justify="right")
    
    for row in history:
        table.add_row(
            row['property_code'],
            str(row['tax_year']),
            f"${row['summer_tax']:,.2f}",
            f"${row['winter_tax']:,.2f}",
            f"${row['annual_tax']:,.2f}",
            f"${row['annual_paid']:,.2f}",
            f"${row['annual_balance']:,.2f}" if row['annual_balance'] else '$0.00',
            f"${row['assessed_value']:,.2f}" if row['assessed_value'] else 'N/A',
            f"${row['taxable_value']:,.2f}" if row['taxable_value'] else 'N/A'
        )
    
    console.print(table)

@tax.command('summary')
@click.option('-y', '--year', type=int, help='Filter by tax year')
@click.option('-s', '--schema', type=click.Choice(['per', 'mhb']), default='mhb',
              help='Database schema (per or mhb)')
def tax_summary(year, schema):
    """Show tax summary by property and year"""
    query = f"""
        SELECT 
            property_code,
            tax_year,
            COUNT(*) as bill_count,
            SUM(total_due) as total_due,
            SUM(total_paid) as total_paid,
            SUM(balance_due) as balance_due,
            SUM(interest_paid) as interest_paid
        FROM {schema}.property_tax_bill
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND tax_year = %s"
        params.append(year)
    
    query += " GROUP BY property_code, tax_year ORDER BY property_code, tax_year DESC"
    
    summary = execute_query(query, params or None)
    
    if not summary:
        console.print("[yellow]No tax data found[/yellow]")
        return
    
    table = Table(title=f"Tax Summary ({schema.upper()})")
    table.add_column("Property", style="cyan")
    table.add_column("Year", style="white")
    table.add_column("Bills", style="white", justify="center")
    table.add_column("Total Due", style="white", justify="right")
    table.add_column("Paid", style="green", justify="right")
    table.add_column("Balance", style="yellow", justify="right")
    table.add_column("Interest", style="red", justify="right")
    
    for row in summary:
        table.add_row(
            row['property_code'],
            str(row['tax_year']),
            str(row['bill_count']),
            f"${row['total_due']:,.2f}",
            f"${row['total_paid']:,.2f}",
            f"${row['balance_due']:,.2f}" if row['balance_due'] else '$0.00',
            f"${row['interest_paid']:,.2f}" if row['interest_paid'] else '-'
        )
    
    console.print(table)

# ============================================================================
# HELP COMMAND
# ============================================================================

@tax.command('help')
def help_command():
    """Display comprehensive tax management help"""
    print_header("PROPERTY TAX MANAGEMENT")
    
    # Import/Export
    import_commands = [
        ("import -f <file> -p <property> [-s schema]", "Import tax bills from CSV"),
    ]
    print_section("IMPORT", import_commands)
    
    # Bill Management
    bill_commands = [
        ("list [-p property] [-y year] [-s schema] [--status]", "List all tax bills"),
        ("show <bill_id> [-s schema]", "Show detailed bill with millage breakdown"),
    ]
    print_section("BILL MANAGEMENT", bill_commands)
    
    # Payments
    payment_commands = [
        ("add-payment <bill_id> --date --amount [opts]", "Record a tax payment"),
        ("payment-history [-p property] [-y year] [-s schema]", "Show payment history"),
    ]
    print_section("PAYMENTS", payment_commands)
    
    # Reports
    report_commands = [
        ("outstanding [-p property] [-s schema]", "Show outstanding balances"),
        ("history [-p property] [-s schema]", "Show annual tax history"),
        ("summary [-y year] [-s schema]", "Show tax summary by property"),
    ]
    print_section("REPORTS", report_commands)
    
    # Examples
    examples = [
        ("Import tax bills from CSV",
         "copilot tax import -f taxes_2024.csv -p 711pine -s mhb"),
        
        ("List all unpaid bills",
         "copilot tax list --status unpaid"),
        
        ("Show detailed bill information",
         "copilot tax show 1 -s mhb"),
        
        ("Record a payment",
         "copilot tax add-payment 1 --date 2024-07-15 --amount 1250.00 --method escrow"),
        
        ("Show outstanding balances",
         "copilot tax outstanding -s mhb"),
    ]
    print_examples("EXAMPLES", examples)


if __name__ == '__main__':
    tax()
