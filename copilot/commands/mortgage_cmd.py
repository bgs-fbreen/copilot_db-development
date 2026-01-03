"""
Mortgage tracking and management for MHB and personal properties

Comprehensive mortgage management system tracking:
- Payment history with principal/interest split
- Amortization projections and comparisons
- Escrow tracking
- Tax reporting
- Scenario analysis (what-if calculations)
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, execute_insert, execute_command, get_connection
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import csv
import psycopg2
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

console = Console()

# ============================================================================
# CONSTANTS
# ============================================================================

# Escrow type detection thresholds (for type 710 transactions)
ESCROW_PROPERTY_TAX_JULY_MIN = 3000  # Summer tax minimum
ESCROW_PROPERTY_TAX_JULY_MAX = 5000  # Summer tax maximum
ESCROW_PROPERTY_TAX_DEC_MIN = 1000   # Winter tax minimum
ESCROW_PROPERTY_TAX_DEC_MAX = 2000   # Winter tax maximum
ESCROW_INSURANCE_MIN = 700           # Insurance minimum
ESCROW_INSURANCE_MAX = 1500          # Insurance maximum

# Allowed entity schemas for SQL injection prevention
ALLOWED_ENTITIES = {'mhb', 'per'}

# Amortization calculation constants
BALANCE_THRESHOLD = 0.01  # Minimum balance to continue amortization (cents)

# ============================================================================
# MAIN COMMAND GROUP
# ============================================================================

@click.group()
def mortgage():
    """Mortgage tracking and payment analysis"""
    pass

# ============================================================================
# MORTGAGE LIST COMMAND
# ============================================================================

@mortgage.command('list')
@click.option('--entity', type=click.Choice(['mhb', 'per', 'all']), default='all', help='Filter by entity')
def mortgage_list(entity):
    """List all mortgages across entities"""
    
    queries = []
    
    # MHB mortgages
    if entity in ['mhb', 'all']:
        queries.append("""
            SELECT 
                'mhb' as entity,
                m.id,
                m.property_code,
                p.address,
                m.lender,
                m.issued_on,
                m.original_balance,
                m.current_balance,
                m.interest_rate,
                m.monthly_payment,
                m.matures_on,
                m.status
            FROM mhb.mortgage m
            JOIN mhb.property p ON p.code = m.property_code
            WHERE m.status = 'active'
        """)
    
    # Personal mortgages
    if entity in ['per', 'all']:
        queries.append("""
            SELECT 
                'per' as entity,
                m.id,
                m.property_code,
                r.address,
                m.lender,
                m.issued_on,
                m.original_balance,
                m.current_balance,
                m.interest_rate,
                m.monthly_payment,
                m.matures_on,
                m.status
            FROM per.mortgage m
            JOIN per.residence r ON r.property_code = m.property_code
            WHERE m.status = 'active'
        """)
    
    query = " UNION ALL ".join(queries) + " ORDER BY entity, property_code"
    
    mortgages = execute_query(query)
    
    if not mortgages:
        console.print("[yellow]No mortgages found[/yellow]")
        return
    
    table = Table(title="Active Mortgages")
    table.add_column("Entity", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Address", style="white")
    table.add_column("Lender", style="white")
    table.add_column("Rate", style="yellow", justify="right")
    table.add_column("Current Balance", style="red", justify="right")
    table.add_column("Maturity", style="white")
    
    for mtg in mortgages:
        table.add_row(
            mtg['entity'].upper(),
            mtg['property_code'],
            mtg['address'],
            mtg['lender'],
            f"{mtg['interest_rate']:.3f}%",
            f"${mtg['current_balance']:,.2f}",
            mtg['matures_on'].strftime('%Y-%m-%d')
        )
    
    console.print(table)
    
    # Summary statistics
    total_balance = sum(m['current_balance'] for m in mortgages)
    avg_rate = sum(m['interest_rate'] for m in mortgages) / len(mortgages)
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"Total Mortgages: {len(mortgages)}")
    console.print(f"Total Balance: ${total_balance:,.2f}")
    console.print(f"Average Rate: {avg_rate:.3f}%")

# ============================================================================
# MORTGAGE SHOW COMMAND
# ============================================================================

@mortgage.command('show')
@click.argument('property_code')
def mortgage_show(property_code):
    """Show detailed mortgage information and payment history"""
    
    # Try MHB first
    query_mhb = """
        SELECT 
            'mhb' as entity,
            m.*,
            p.address,
            p.city,
            p.state
        FROM mhb.mortgage m
        JOIN mhb.property p ON p.code = m.property_code
        WHERE m.property_code = %s
    """
    
    query_per = """
        SELECT 
            'per' as entity,
            m.*,
            r.address,
            r.city,
            r.state
        FROM per.mortgage m
        JOIN per.residence r ON r.property_code = m.property_code
        WHERE m.property_code = %s
    """
    
    mortgage = execute_query(query_mhb, (property_code,))
    if not mortgage:
        mortgage = execute_query(query_per, (property_code,))
    
    if not mortgage:
        console.print(f"[red]Mortgage for property '{property_code}' not found[/red]")
        return
    
    mtg = mortgage[0]
    entity = mtg['entity']
    
    # Display mortgage details
    console.print(f"\n[bold cyan]Mortgage: {mtg['property_code']}[/bold cyan]")
    console.print(f"Entity: {entity.upper()}")
    console.print(f"Property: {mtg['address']}, {mtg['city']}, {mtg['state']}")
    console.print(f"Lender: {mtg['lender']}")
    console.print(f"Loan Number: {mtg['loan_number'] or 'N/A'}")
    console.print(f"\n[bold]Loan Terms:[/bold]")
    console.print(f"Issue Date: {mtg['issued_on'].strftime('%Y-%m-%d')}")
    console.print(f"Maturity Date: {mtg['matures_on'].strftime('%Y-%m-%d')}")
    console.print(f"Original Balance: ${mtg['original_balance']:,.2f}")
    console.print(f"Current Balance: ${mtg['current_balance']:,.2f}")
    console.print(f"Interest Rate: {mtg['interest_rate']:.3f}%")
    if mtg['monthly_payment']:
        console.print(f"Monthly Payment: ${mtg['monthly_payment']:,.2f}")
    
    # Calculate paid off amount and percentage
    paid_off = mtg['original_balance'] - mtg['current_balance']
    percent_paid = (paid_off / mtg['original_balance']) * 100 if mtg['original_balance'] > 0 else 0
    
    console.print(f"\n[bold]Progress:[/bold]")
    console.print(f"Principal Paid: ${paid_off:,.2f} ({percent_paid:.1f}%)")
    console.print(f"Remaining: ${mtg['current_balance']:,.2f} ({100-percent_paid:.1f}%)")
    
    # Get payment history
    payment_table = f"{entity}.mortgage_payment"
    payment_query = f"""
        SELECT 
            payment_date,
            amount,
            principal,
            interest,
            escrow,
            balance_after
        FROM {payment_table}
        WHERE mortgage_id = %s
        ORDER BY payment_date DESC
        LIMIT 12
    """
    
    payments = execute_query(payment_query, (mtg['id'],))
    
    if payments:
        console.print(f"\n[bold]Recent Payments (last 12):[/bold]")
        table = Table()
        table.add_column("Date", style="cyan")
        table.add_column("Amount", style="white", justify="right")
        table.add_column("Principal", style="green", justify="right")
        table.add_column("Interest", style="yellow", justify="right")
        table.add_column("Escrow", style="blue", justify="right")
        table.add_column("Balance After", style="red", justify="right")
        
        for pmt in payments:
            table.add_row(
                pmt['payment_date'].strftime('%Y-%m-%d'),
                f"${pmt['amount']:,.2f}",
                f"${pmt['principal']:,.2f}",
                f"${pmt['interest']:,.2f}",
                f"${pmt['escrow']:,.2f}" if pmt['escrow'] else "-",
                f"${pmt['balance_after']:,.2f}"
            )
        
        console.print(table)
        
        # Payment statistics
        total_principal = sum(p['principal'] for p in payments)
        total_interest = sum(p['interest'] for p in payments)
        
        console.print(f"\n[bold]Last 12 Payments Summary:[/bold]")
        console.print(f"Total Principal: ${total_principal:,.2f}")
        console.print(f"Total Interest: ${total_interest:,.2f}")
        console.print(f"Interest/Principal Ratio: {(total_interest/total_principal*100) if total_principal > 0 else 0:.1f}%")
    else:
        console.print(f"\n[yellow]No payment history found[/yellow]")

# ============================================================================
# MORTGAGE HELP COMMAND
# ============================================================================

@mortgage.command('help')
def mortgage_help():
    """Show mortgage command cheat sheet"""
    
    help_text = """
[bold cyan]Mortgage Management Commands[/bold cyan]

[bold]List & View:[/bold]
  copilot mortgage list                         List all mortgages
  copilot mortgage list --entity mhb            List only MHB mortgages
  copilot mortgage list --entity per            List only personal mortgages
  copilot mortgage show <property>              Show mortgage details + payment history

[bold]Payment Processing:[/bold]
  copilot mortgage import --file <csv>          Import bank CSV & split P&I
  copilot mortgage project <property>           Generate amortization schedule
  copilot mortgage compare <property>           Compare projected vs actual

[bold]Analysis & Reporting:[/bold]
  copilot mortgage report <property>            Generate charts & analysis report
  copilot mortgage whatif <property>            Scenario analysis
    --extra-monthly 100                         Extra monthly payment impact
    --extra-annual 5000                         Annual lump sum impact
    --rate-change 7.5                           Rate change impact
    --cashout 15000                             Refinance cash-out analysis

[bold]Tax Reporting:[/bold]
  copilot mortgage tax-report --year 2024       Interest paid summary for taxes

[bold]Examples:[/bold]
  copilot mortgage show 711pine
  copilot mortgage list --entity mhb
  copilot mortgage report parnell
  copilot mortgage report 819helen
  copilot mortgage whatif parnell --extra-monthly 200
  copilot mortgage tax-report --year 2024
"""
    
    console.print(Panel(help_text, title="Mortgage Commands", border_style="cyan"))

# ============================================================================
# MORTGAGE IMPORT COMMAND
# ============================================================================

def parse_csv_date(date_str):
    """Parse date from CSV 'Effective / Posted' column - extract first date"""
    if not date_str:
        return None
    
    # Handle "12/30/2025 12/24/2025" format - take first date
    parts = date_str.strip().split()
    first_date = parts[0] if parts else date_str
    
    date_formats = [
        '%m/%d/%Y',      # 12/30/2025
        '%m/%d/%y',      # 12/30/25
        '%Y-%m-%d',      # 2025-12-30
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(first_date.strip(), fmt).date()
        except ValueError:
            continue
    
    console.print(f"[yellow]Warning: Could not parse date '{date_str}'[/yellow]")
    return None

def parse_csv_amount(amount_str):
    """Parse amount from CSV, handling negative values and currency symbols"""
    if not amount_str:
        return Decimal('0.00')
    
    # Remove currency symbols, spaces, and commas
    amount_str = amount_str.replace('$', '').replace(',', '').strip()
    
    # Handle parentheses for negative amounts
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    try:
        return Decimal(amount_str)
    except (ValueError, InvalidOperation):
        return Decimal('0.00')

def detect_escrow_type(type_code, amount, trans_date, description):
    """
    Detect escrow type for type 710 transactions
    Based on amount and date patterns
    """
    if type_code == '716':
        return 'auto_disbursement'
    
    if type_code != '710':
        return 'other'
    
    # Use Decimal directly, no float conversion to maintain precision
    amount_abs = abs(amount)
    month = trans_date.month
    
    # Large amounts in July: property_tax (summer tax)
    if month == 7 and ESCROW_PROPERTY_TAX_JULY_MIN <= amount_abs <= ESCROW_PROPERTY_TAX_JULY_MAX:
        return 'property_tax'
    
    # Large amounts in December: property_tax (winter tax)
    if month == 12 and ESCROW_PROPERTY_TAX_DEC_MIN <= amount_abs <= ESCROW_PROPERTY_TAX_DEC_MAX:
        return 'property_tax'
    
    # Amounts in insurance range not in Jul/Dec: insurance
    if ESCROW_INSURANCE_MIN <= amount_abs <= ESCROW_INSURANCE_MAX and month not in [7, 12]:
        return 'insurance'
    
    # Default to other
    return 'other'

def get_entity_and_mortgage(property_code):
    """
    Get entity schema and mortgage record for property_code
    Returns: (entity, mortgage_record) or (None, None) if not found
    """
    # parnell -> per schema, all others -> mhb schema
    entity = 'per' if property_code == 'parnell' else 'mhb'
    
    # Validate entity against whitelist to prevent SQL injection
    if entity not in ALLOWED_ENTITIES:
        console.print(f"[red]Error: Invalid entity '{entity}'[/red]")
        return None, None
    
    query = f"""
        SELECT id, current_balance, interest_rate
        FROM {entity}.mortgage
        WHERE property_code = %s AND status = 'active'
    """
    
    result = execute_query(query, (property_code,))
    if result:
        return entity, result[0]
    return None, None

@mortgage.command('import')
@click.option('--file', '-f', type=click.Path(exists=True), required=True, help='CSV file to import')
@click.option('--property', '-p', required=True, help='Property code (711pine, 819helen, 905brown, parnell)')
@click.option('--dry-run', is_flag=True, help='Preview without inserting')
def mortgage_import(file, property, dry_run):
    """Import mortgage payment history from Central Savings Bank CSV"""
    
    # Get entity and mortgage record
    entity, mortgage = get_entity_and_mortgage(property)
    
    if not mortgage or not entity:
        console.print(f"[red]Error: No active mortgage found for property '{property}'[/red]")
        return
    
    # Additional validation: entity must be in allowed list (defense in depth)
    if entity not in ALLOWED_ENTITIES:
        console.print(f"[red]Error: Invalid entity schema '{entity}'[/red]")
        return
    
    mortgage_id = mortgage['id']
    
    # Parse CSV file
    try:
        with open(file, 'r', encoding='utf-8-sig', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except (FileNotFoundError, csv.Error, UnicodeDecodeError) as e:
        console.print(f"[red]Error reading CSV file: {e}[/red]")
        return
    
    if not rows:
        console.print("[yellow]No data found in CSV file[/yellow]")
        return
    
    # Process rows and categorize
    payments_to_import = []
    escrow_to_import = []
    duplicates = 0
    
    # Get existing payments and escrow to detect duplicates
    existing_payments = execute_query(f"""
        SELECT payment_date, amount 
        FROM {entity}.mortgage_payment 
        WHERE mortgage_id = %s
    """, (mortgage_id,))
    
    existing_escrow = execute_query(f"""
        SELECT disbursement_date, amount 
        FROM {entity}.mortgage_escrow 
        WHERE mortgage_id = %s
    """, (mortgage_id,))
    
    existing_payment_set = {(p['payment_date'], Decimal(str(p['amount']))) for p in existing_payments}
    existing_escrow_set = {(e['disbursement_date'], Decimal(str(e['amount']))) for e in existing_escrow}
    
    for row in rows:
        # Parse date
        effective_date = parse_csv_date(row.get('Effective / Posted', ''))
        if not effective_date:
            continue
        
        # Parse type code
        type_field = row.get('Type', '')
        type_code = type_field.split(' - ')[0].strip() if ' - ' in type_field else ''
        
        # Parse amounts
        amount = parse_csv_amount(row.get('Amount', ''))
        principal = parse_csv_amount(row.get('Principal', ''))
        interest = parse_csv_amount(row.get('Interest', ''))
        balance = parse_csv_amount(row.get('Balance', ''))
        
        # Route based on type code
        if type_code in ('620', '612'):
            # Payment transaction
            if (effective_date, amount) in existing_payment_set:
                duplicates += 1
                continue
            
            payments_to_import.append({
                'date': effective_date,
                'amount': amount,
                'principal': principal,
                'interest': interest,
                'balance': balance,
                'type': type_field
            })
        
        elif type_code in ('710', '716'):
            # Escrow transaction - disbursements from escrow account
            # CSV amounts are positive, store as positive in disbursement table
            escrow_amount = abs(amount)
            
            if (effective_date, escrow_amount) in existing_escrow_set:
                duplicates += 1
                continue
            
            escrow_type = detect_escrow_type(type_code, amount, effective_date, type_field)
            
            escrow_to_import.append({
                'date': effective_date,
                'amount': escrow_amount,
                'escrow_type': escrow_type,
                'description': type_field
            })
    
    # Calculate summary by escrow type
    escrow_summary = {}
    for esc in escrow_to_import:
        esc_type = esc['escrow_type']
        escrow_summary[esc_type] = escrow_summary.get(esc_type, 0) + 1
    
    # Get the most recent balance
    new_balance = None
    if payments_to_import:
        # Sort by date to get the most recent
        sorted_payments = sorted(payments_to_import, key=lambda x: x['date'], reverse=True)
        new_balance = sorted_payments[0]['balance']
    
    # Display summary
    if dry_run:
        console.print(f"\n[bold cyan]Dry Run - Preview of import for {property}[/bold cyan]")
        console.print("─" * 50)
        console.print(f"File: {file}")
        console.print(f"Records: {len(rows)}")
        console.print(f"\nPayments to import: {len(payments_to_import)}")
        console.print(f"Escrow transactions: {len(escrow_to_import)}")
        
        if escrow_summary:
            for esc_type, count in sorted(escrow_summary.items()):
                console.print(f"  - {esc_type.replace('_', ' ').title()}: {count}")
        
        console.print(f"\nDuplicates to skip: {duplicates}")
        
        if new_balance is not None:
            console.print(f"\nNew balance will be: ${new_balance:,.2f}")
        
        console.print("\n[yellow]Run without --dry-run to import.[/yellow]")
        return
    
    # Perform actual import
    console.print(f"\n[bold cyan]Importing mortgage history for {property}...[/bold cyan]")
    console.print("─" * 50)
    
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Insert payments
        payment_count = 0
        for pmt in payments_to_import:
            cur.execute(f"""
                INSERT INTO {entity}.mortgage_payment 
                (mortgage_id, payment_date, amount, principal, interest, escrow, balance_after, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                mortgage_id,
                pmt['date'],
                pmt['amount'],
                pmt['principal'],
                pmt['interest'],
                Decimal('0.00'),  # escrow portion of payment (0 since escrow tracked separately)
                pmt['balance'],
                f"Imported from CSV - {pmt['type']}"
            ))
            payment_count += 1
        
        # Insert escrow transactions
        escrow_count = 0
        for esc in escrow_to_import:
            cur.execute(f"""
                INSERT INTO {entity}.mortgage_escrow 
                (mortgage_id, disbursement_date, expense_type, payee, amount, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                mortgage_id,
                esc['date'],
                esc['escrow_type'],
                'Central Savings Bank',
                esc['amount'],  # Already positive from processing above
                esc['description']
            ))
            escrow_count += 1
        
        # Update current balance if we have a new one
        if new_balance is not None:
            cur.execute(f"""
                UPDATE {entity}.mortgage 
                SET current_balance = %s 
                WHERE id = %s
            """, (new_balance, mortgage_id))
        
        conn.commit()
        
        console.print(f"[green]✓[/green] Imported {payment_count} payments")
        console.print(f"[green]✓[/green] Imported {escrow_count} escrow transactions")
        if new_balance is not None:
            console.print(f"[green]✓[/green] Updated current balance: ${new_balance:,.2f}")
        
        if duplicates > 0:
            console.print(f"\nSkipped {duplicates} duplicates")
        
        console.print(f"\n[bold green]Import completed successfully![/bold green]")
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        console.print(f"[red]Database error during import: {e}[/red]")
    except Exception as e:
        if conn:
            conn.rollback()
        console.print(f"[red]Unexpected error during import: {e}[/red]")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ============================================================================
# MORTGAGE PROJECT COMMAND
# ============================================================================

def calculate_monthly_payment(principal, annual_rate, months):
    """
    Calculate monthly payment using standard amortization formula
    M = P * [r(1+r)^n] / [(1+r)^n - 1]
    """
    if annual_rate == 0:
        return principal / months if months > 0 else 0
    
    monthly_rate = annual_rate / 12 / 100
    denominator = ((1 + monthly_rate) ** months) - 1
    
    if denominator == 0:
        return principal / months if months > 0 else 0
    
    monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / denominator
    return monthly_payment

def add_months_to_date(start_date, months):
    """Add months to a date, handling month/year rollovers and day-of-month edge cases"""
    import calendar
    
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    
    # Get the last day of the target month
    last_day = calendar.monthrange(year, month)[1]
    day = min(start_date.day, last_day)
    
    return start_date.replace(year=year, month=month, day=day)

@mortgage.command('project')
@click.argument('property_code')
def mortgage_project(property_code):
    """Generate amortization schedule projection"""
    
    # Get entity and mortgage record
    entity, mortgage = get_entity_and_mortgage(property_code)
    
    if not mortgage or not entity:
        console.print(f"[red]Error: No active mortgage found for property '{property_code}'[/red]")
        return
    
    # Get full mortgage details
    query = f"""
        SELECT id, property_code, original_balance, current_balance, interest_rate, monthly_payment, 
               issued_on, matures_on
        FROM {entity}.mortgage 
        WHERE property_code = %s AND status = 'active'
    """
    
    result = execute_query(query, (property_code,))
    if not result:
        console.print(f"[red]Error: Mortgage not found[/red]")
        return
    
    mtg = result[0]
    
    # Edge case: Zero balance
    if mtg['original_balance'] <= 0:
        console.print(f"[yellow]⚠ Mortgage {property_code} has zero balance. No projection needed.[/yellow]")
        return
    
    # Edge case: Maturity date in the past
    today = datetime.now().date()
    if mtg['matures_on'] < today:
        console.print(f"[yellow]⚠ Mortgage {property_code} maturity date ({mtg['matures_on']}) is in the past.[/yellow]")
        return
    
    # Calculate monthly payment if not set
    monthly_payment = mtg['monthly_payment']
    if not monthly_payment or monthly_payment <= 0:
        # Calculate months until maturity from issued_on date
        issued_on = mtg['issued_on']
        months_until_maturity = (mtg['matures_on'].year - issued_on.year) * 12 + (mtg['matures_on'].month - issued_on.month)
        if months_until_maturity <= 0:
            months_until_maturity = 1
        
        monthly_payment = calculate_monthly_payment(
            float(mtg['original_balance']),
            float(mtg['interest_rate']),
            months_until_maturity
        )
        monthly_payment = Decimal(str(round(monthly_payment, 2)))
    
    # Display header
    console.print(f"\n[bold cyan]Generating amortization schedule for {property_code}...[/bold cyan]")
    console.print("━" * 50)
    console.print()
    
    # Display mortgage details
    console.print("[bold]Mortgage Details:[/bold]")
    console.print(f"  Original Balance: ${mtg['original_balance']:,.2f}")
    console.print(f"  Interest Rate: {mtg['interest_rate']:.3f}%")
    console.print(f"  Monthly Payment: ${monthly_payment:,.2f}")
    console.print(f"  Issued: {mtg['issued_on']}")
    console.print(f"  Maturity Date: {mtg['matures_on']}")
    console.print()
    
    # Delete existing projections
    execute_command(f"DELETE FROM {entity}.mortgage_projection WHERE mortgage_id = %s", (mtg['id'],))
    
    # Generate amortization schedule
    monthly_rate = float(mtg['interest_rate']) / 12 / 100
    remaining_balance = float(mtg['original_balance'])
    cumulative_interest = 0.0
    payment_number = 1
    
    # Start from first payment date (month after issued_on)
    issued_on = mtg['issued_on']
    payment_date = add_months_to_date(issued_on, 1)
    
    projections = []
    
    while remaining_balance > BALANCE_THRESHOLD and payment_date <= mtg['matures_on']:
        # Calculate interest for this period
        interest = remaining_balance * monthly_rate
        
        # Calculate principal - ensure we don't go negative
        principal_payment = float(monthly_payment) - interest
        
        # Handle case where interest exceeds payment (negative amortization)
        if principal_payment <= 0:
            console.print(f"[red]Error: Monthly payment ${monthly_payment:,.2f} is too small for interest rate {mtg['interest_rate']:.3f}%[/red]")
            console.print(f"[red]At current balance ${remaining_balance:,.2f}, monthly interest is ${interest:,.2f}[/red]")
            return
        
        principal = min(principal_payment, remaining_balance)
        
        # Adjust for final payment
        if principal >= remaining_balance:
            principal = remaining_balance
            total_payment = principal + interest
        else:
            total_payment = float(monthly_payment)
        
        # Update running totals
        remaining_balance -= principal
        cumulative_interest += interest
        
        # Store projection record
        projections.append({
            'mortgage_id': mtg['id'],
            'projection_date': datetime.now(),
            'payment_number': payment_number,
            'payment_date': payment_date,
            'payment_amount': Decimal(str(round(total_payment, 2))),
            'principal': Decimal(str(round(principal, 2))),
            'interest': Decimal(str(round(interest, 2))),
            'balance_after': Decimal(str(round(remaining_balance, 2))),
            'cumulative_interest': Decimal(str(round(cumulative_interest, 2)))
        })
        
        payment_number += 1
        payment_date = add_months_to_date(payment_date, 1)
    
    # Insert all projections
    conn = get_connection()
    try:
        cur = conn.cursor()
        for proj in projections:
            cur.execute(f"""
                INSERT INTO {entity}.mortgage_projection 
                (mortgage_id, projection_date, payment_number, payment_date, 
                 payment_amount, principal, interest, balance_after, cumulative_interest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proj['mortgage_id'],
                proj['projection_date'],
                proj['payment_number'],
                proj['payment_date'],
                proj['payment_amount'],
                proj['principal'],
                proj['interest'],
                proj['balance_after'],
                proj['cumulative_interest']
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error inserting projections: {e}[/red]")
        return
    finally:
        cur.close()
        conn.close()
    
    # Calculate totals
    total_payments = len(projections)
    first_payment = projections[0]['payment_date'] if projections else None
    last_payment = projections[-1]['payment_date'] if projections else None
    total_interest = projections[-1]['cumulative_interest'] if projections else Decimal('0.00')
    total_amount = sum(p['payment_amount'] for p in projections)
    
    # Display summary
    console.print("[bold]Projection Generated:[/bold]")
    console.print(f"  Total Payments: {total_payments}")
    console.print(f"  First Payment: {first_payment}")
    console.print(f"  Last Payment: {last_payment}")
    console.print(f"  Total Interest: ${total_interest:,.2f}")
    console.print(f"  Total Amount: ${total_amount:,.2f}")
    console.print()
    console.print(f"[green]✓ Projection saved to database[/green]")
    console.print(f"Run 'copilot mortgage report {property_code}' to view charts")

# ============================================================================
# MORTGAGE COMPARE COMMAND (Placeholder)
# ============================================================================

@mortgage.command('compare')
@click.argument('property_code')
def mortgage_compare(property_code):
    """Compare projected vs actual mortgage payments"""
    console.print("[yellow]This command is not yet implemented[/yellow]")
    console.print(f"Would compare projected vs actual for: {property_code}")
    console.print("\nThis will show:")
    console.print("- Projected schedule vs actual payments")
    console.print("- Ahead/behind schedule")
    console.print("- Extra principal payments impact")
    console.print("- Interest savings from early payments")

# ============================================================================
# MORTGAGE WHATIF COMMAND (Placeholder)
# ============================================================================

@mortgage.command('whatif')
@click.argument('property_code')
@click.option('--extra-monthly', type=float, help='Extra monthly payment amount')
@click.option('--extra-annual', type=float, help='Annual lump sum payment')
@click.option('--rate-change', type=float, help='New interest rate for comparison')
@click.option('--cashout', type=float, help='Cash-out refinance amount')
def mortgage_whatif(property_code, extra_monthly, extra_annual, rate_change, cashout):
    """Run what-if scenario analysis"""
    console.print("[yellow]This command is not yet implemented[/yellow]")
    console.print(f"Would run scenario for: {property_code}")
    console.print("\nScenario parameters:")
    if extra_monthly:
        console.print(f"- Extra monthly: ${extra_monthly:,.2f}")
    if extra_annual:
        console.print(f"- Extra annual: ${extra_annual:,.2f}")
    if rate_change:
        console.print(f"- Rate change to: {rate_change}%")
    if cashout:
        console.print(f"- Cash-out amount: ${cashout:,.2f}")

# ============================================================================
# MORTGAGE TAX REPORT COMMAND (Placeholder)
# ============================================================================

@mortgage.command('tax-report')
@click.option('--year', type=int, required=True, help='Tax year')
def mortgage_tax_report(year):
    """Generate interest paid summary for tax reporting"""
    console.print("[yellow]This command is not yet implemented[/yellow]")
    console.print(f"Would generate tax report for year: {year}")
    console.print("\nThis will show:")
    console.print("- Total interest paid by property")
    console.print("- Month-by-month breakdown")
    console.print("- Deductible interest amounts")
    console.print("- Format suitable for Schedule E")

# ============================================================================
# MORTGAGE REPORT COMMAND - Charts and Analysis
# ============================================================================

def get_mortgage_details(entity, property_code):
    """Get mortgage details with property information"""
    if entity not in ALLOWED_ENTITIES:
        return None
    
    if entity == 'per':
        query = f"""
            SELECT 
                m.id,
                m.property_code,
                r.address,
                r.city,
                r.state,
                m.lender,
                m.loan_number,
                m.issued_on,
                m.original_balance,
                m.current_balance,
                m.interest_rate,
                m.monthly_payment,
                m.matures_on
            FROM {entity}.mortgage m
            JOIN {entity}.residence r ON r.property_code = m.property_code
            WHERE m.property_code = %s AND m.status = 'active'
        """
    else:
        query = f"""
            SELECT 
                m.id,
                m.property_code,
                p.address,
                p.city,
                p.state,
                m.lender,
                m.loan_number,
                m.issued_on,
                m.original_balance,
                m.current_balance,
                m.interest_rate,
                m.monthly_payment,
                m.matures_on
            FROM {entity}.mortgage m
            JOIN {entity}.property p ON p.code = m.property_code
            WHERE m.property_code = %s AND m.status = 'active'
        """
    
    result = execute_query(query, (property_code,))
    return result[0] if result else None

def get_projection_data(entity, mortgage_id):
    """Get projection data from mortgage_projection table"""
    if entity not in ALLOWED_ENTITIES:
        return []
    
    query = f"""
        SELECT 
            payment_number, 
            payment_date, 
            principal, 
            interest, 
            balance_after, 
            cumulative_interest
        FROM {entity}.mortgage_projection
        WHERE mortgage_id = %s
        ORDER BY payment_number
    """
    
    return execute_query(query, (mortgage_id,))

def get_actual_payment_data(entity, mortgage_id):
    """Get actual payment data from mortgage_payment table"""
    if entity not in ALLOWED_ENTITIES:
        return []
    
    query = f"""
        SELECT 
            payment_date, 
            principal, 
            interest, 
            balance_after
        FROM {entity}.mortgage_payment
        WHERE mortgage_id = %s
          AND (principal != 0 OR interest != 0)
        ORDER BY payment_date
    """
    
    return execute_query(query, (mortgage_id,))

def calculate_variance_stats(projected, actual):
    """Calculate projected vs actual variance statistics"""
    if not projected or not actual:
        return None
    
    # Match by payment number (assume chronological order)
    num_actual = len(actual)
    if num_actual > len(projected):
        num_actual = len(projected)
    
    proj_principal = sum(p['principal'] for p in projected[:num_actual])
    act_principal = sum(a['principal'] for a in actual[:num_actual])
    
    proj_interest = sum(p['interest'] for p in projected[:num_actual])
    act_interest = sum(a['interest'] for a in actual[:num_actual])
    
    proj_balance = projected[num_actual - 1]['balance_after'] if num_actual > 0 else 0
    act_balance = actual[-1]['balance_after'] if actual else 0
    
    return {
        'payments_made': num_actual,
        'total_projected_payments': len(projected),
        'proj_principal': proj_principal,
        'act_principal': act_principal,
        'principal_variance': act_principal - proj_principal,
        'proj_interest': proj_interest,
        'act_interest': act_interest,
        'interest_variance': act_interest - proj_interest,
        'proj_balance': proj_balance,
        'act_balance': act_balance,
        'balance_variance': act_balance - proj_balance,
    }

def print_summary_report(mortgage, projected, actual, stats):
    """Print terminal summary report using Rich"""
    property_code = mortgage['property_code']
    full_address = f"{mortgage['address']}, {mortgage['city']}, {mortgage['state']}"
    
    # Header
    console.print(Panel(
        f"[bold cyan]Mortgage Report: {property_code}[/bold cyan]",
        expand=False
    ))
    console.print()
    
    # Mortgage details
    console.print(f"[bold]Property:[/bold] {full_address}")
    console.print(f"[bold]Lender:[/bold] {mortgage['lender']}")
    console.print(f"[bold]Interest Rate:[/bold] {mortgage['interest_rate']:.3f}%")
    console.print(f"[bold]Original Balance:[/bold] ${mortgage['original_balance']:,.2f}")
    console.print(f"[bold]Current Balance:[/bold] ${mortgage['current_balance']:,.2f}")
    console.print()
    
    # Loan progress
    if stats:
        principal_paid = mortgage['original_balance'] - mortgage['current_balance']
        percent_paid = (principal_paid / mortgage['original_balance'] * 100) if mortgage['original_balance'] > 0 else 0
        
        console.print("[bold]Loan Progress:[/bold]")
        console.print(f"  Payments Made: {stats['payments_made']} of {stats['total_projected_payments']}")
        console.print(f"  Principal Paid: ${principal_paid:,.2f} ({percent_paid:.1f}%)")
        console.print(f"  Interest Paid: ${stats['act_interest']:,.2f}")
        console.print(f"  Remaining: ${mortgage['current_balance']:,.2f} ({100-percent_paid:.1f}%)")
        console.print()
        
        # Projected vs Actual Analysis
        console.print("[bold]Projected vs Actual Analysis:[/bold]")
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Projected", style="white", justify="right")
        table.add_column("Actual", style="white", justify="right")
        table.add_column("Variance", style="yellow", justify="right")
        
        # Principal variance
        principal_var_str = f"[green]+${stats['principal_variance']:,.2f}[/green]" if stats['principal_variance'] > 0 else f"${stats['principal_variance']:,.2f}"
        table.add_row(
            "Principal Paid",
            f"${stats['proj_principal']:,.2f}",
            f"${stats['act_principal']:,.2f}",
            principal_var_str
        )
        
        # Interest variance
        interest_var_str = f"[green]-${abs(stats['interest_variance']):,.2f}[/green]" if stats['interest_variance'] < 0 else f"+${stats['interest_variance']:,.2f}"
        table.add_row(
            "Interest Paid",
            f"${stats['proj_interest']:,.2f}",
            f"${stats['act_interest']:,.2f}",
            interest_var_str
        )
        
        # Balance variance
        balance_var_str = f"[green]-${abs(stats['balance_variance']):,.2f}[/green]" if stats['balance_variance'] < 0 else f"+${stats['balance_variance']:,.2f}"
        table.add_row(
            "Current Balance",
            f"${stats['proj_balance']:,.2f}",
            f"${stats['act_balance']:,.2f}",
            balance_var_str
        )
        
        console.print(table)
        console.print()
        
        # Status message
        if stats['principal_variance'] > 0:
            # Calculate payment difference (avoiding division by zero)
            avg_payment_principal = stats['proj_principal'] / stats['payments_made'] if stats['payments_made'] > 0 else 0
            payment_diff = stats['principal_variance'] / avg_payment_principal if avg_payment_principal > 0 else 0
            console.print(f"[bold green]Status: ✓ Ahead of schedule by approximately {int(payment_diff)} payments[/bold green]")
        elif stats['principal_variance'] < 0:
            console.print(f"[bold yellow]Status: ⚠ Behind schedule[/bold yellow]")
        else:
            console.print(f"[bold]Status: ✓ On schedule[/bold]")
        
        if stats['interest_variance'] < 0:
            console.print(f"[bold green]Interest Savings: ${abs(stats['interest_variance']):,.2f}[/bold green]")
    else:
        console.print("[yellow]No payment history imported yet[/yellow]")
    
    console.print()

def insert_gaps_for_missing_data(dates, values, max_gap_days=45):
    """Insert NaN values where there are gaps > max_gap_days to break the line."""
    if len(dates) < 2:
        return dates, values
    
    new_dates = []
    new_values = []
    
    for i in range(len(dates)):
        new_dates.append(dates[i])
        new_values.append(values[i])
        
        # Check if there's a gap to next point
        if i < len(dates) - 1:
            gap = (dates[i+1] - dates[i]).days
            if gap > max_gap_days:
                # Insert NaN to break the line
                new_dates.append(dates[i] + timedelta(days=1))
                new_values.append(np.nan)
    
    return new_dates, new_values

def display_charts(mortgage, projected, actual):
    """Generate and display matplotlib charts"""
    if not projected:
        console.print("[yellow]⚠ No projection data available for charts[/yellow]")
        return
    
    # Create figure with 3 subplots (stacked vertically) - 15% narrower, 10% shorter from original 14x10
    fig, axes = plt.subplots(3, 1, figsize=(10.7, 8.1))
    
    property_code = mortgage['property_code']
    full_address = f"{mortgage['address']}, {mortgage['city']}, {mortgage['state']}"
    fig.suptitle(f"Mortgage Report: {property_code} - {full_address}", fontsize=16, fontweight='bold')
    
    # Extract projected data - use dates for X-axis
    proj_dates = [p['payment_date'] for p in projected]
    proj_principal = [float(p['principal']) for p in projected]
    proj_interest = [float(p['interest']) for p in projected]
    proj_balance = [float(p['balance_after']) for p in projected]
    
    # Extract actual data - use dates for X-axis
    act_dates = [a['payment_date'] for a in actual]
    act_principal = [float(a['principal']) for a in actual]
    act_interest = [float(a['interest']) for a in actual]
    act_balance = [float(a['balance_after']) for a in actual]
    
    # Insert gaps for missing data (> 45 days between payments)
    if act_dates:
        act_dates, act_principal = insert_gaps_for_missing_data(act_dates, act_principal)
        act_dates, act_interest = insert_gaps_for_missing_data(act_dates, act_interest)
        act_dates, act_balance = insert_gaps_for_missing_data(act_dates, act_balance)
    
    # Panel 1: Principal per Payment
    axes[0].plot(proj_dates, proj_principal, 'b--', label='Projected Principal', linewidth=2)
    if actual:
        axes[0].plot(act_dates, act_principal, 'b-', label='Actual Principal', linewidth=2)
    axes[0].set_xlabel('Date')
    axes[0].set_ylabel('Principal ($)')
    axes[0].set_title('Principal per Payment')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    # Format X-axis as dates
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    axes[0].xaxis.set_major_locator(mdates.YearLocator(2))  # Every 2 years
    
    # Panel 2: Interest per Payment
    axes[1].plot(proj_dates, proj_interest, 'r--', label='Projected Interest', linewidth=2)
    if actual:
        axes[1].plot(act_dates, act_interest, 'r-', label='Actual Interest', linewidth=2)
    axes[1].set_xlabel('Date')
    axes[1].set_ylabel('Interest ($)')
    axes[1].set_title('Interest per Payment')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    # Format X-axis as dates
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))  # Every 2 years
    
    # Panel 3: Remaining Balance
    axes[2].plot(proj_dates, proj_balance, 'g--', label='Projected Balance', linewidth=2)
    if actual:
        axes[2].plot(act_dates, act_balance, 'g-', label='Actual Balance', linewidth=2)
    axes[2].set_xlabel('Date')
    axes[2].set_ylabel('Balance ($)')
    axes[2].set_title('Remaining Balance')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    # Format X-axis as dates
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    axes[2].xaxis.set_major_locator(mdates.YearLocator(2))  # Every 2 years
    
    plt.tight_layout()
    
    # Try to maximize window (cross-platform)
    manager = plt.get_current_fig_manager()
    try:
        # For TkAgg backend (most common)
        manager.window.state('zoomed')
    except:
        try:
            # For Qt backend
            manager.window.showMaximized()
        except:
            try:
                # For other backends
                manager.full_screen_toggle()
            except:
                # If all else fails, just show normally
                pass
    
    plt.show()

@mortgage.command('report')
@click.argument('property_code')
def mortgage_report(property_code):
    """Generate projected vs actual mortgage report with charts"""
    
    # 1. Determine entity (per or mhb)
    entity = 'per' if property_code == 'parnell' else 'mhb'
    
    # 2. Get mortgage details
    mortgage = get_mortgage_details(entity, property_code)
    
    if not mortgage:
        console.print(f"[red]Error: No active mortgage found for property '{property_code}'[/red]")
        console.print(f"[yellow]Hint: Check property code spelling or use 'copilot mortgage list' to see available mortgages[/yellow]")
        return
    
    # 3. Get projected data from mortgage_projection table
    projected = get_projection_data(entity, mortgage['id'])
    
    # 4. Get actual data from mortgage_payment table
    actual = get_actual_payment_data(entity, mortgage['id'])
    
    # Handle missing projection data
    if not projected:
        console.print(f"[yellow]⚠ No projection data found for {property_code}.[/yellow]")
        console.print(f"[yellow]Run 'copilot mortgage project {property_code}' first to generate amortization schedule.[/yellow]")
        return
    
    # 5. Calculate statistics
    stats = calculate_variance_stats(projected, actual) if actual else None
    
    # 6. Print terminal summary report
    print_summary_report(mortgage, projected, actual, stats)
    
    # 7. Generate and display matplotlib charts
    display_charts(mortgage, projected, actual)
