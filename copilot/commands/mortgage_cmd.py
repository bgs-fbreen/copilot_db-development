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
from decimal import Decimal
import csv

console = Console()

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

[bold]Analysis:[/bold]
  copilot mortgage whatif <property>            Scenario analysis
    --extra-monthly 100                         Extra monthly payment impact
    --extra-annual 5000                         Annual lump sum impact
    --rate-change 7.5                           Rate change impact
    --cashout 15000                             Refinance cash-out analysis

[bold]Reporting:[/bold]
  copilot mortgage tax-report --year 2024       Interest paid summary for taxes

[bold]Examples:[/bold]
  copilot mortgage show 711pine
  copilot mortgage list --entity mhb
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
    except:
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
    
    amount_abs = abs(float(amount))
    month = trans_date.month
    
    # Large amounts in July ($3000-5000): property_tax (summer tax)
    if month == 7 and 3000 <= amount_abs <= 5000:
        return 'property_tax'
    
    # Large amounts in December ($1000-2000): property_tax (winter tax)
    if month == 12 and 1000 <= amount_abs <= 2000:
        return 'property_tax'
    
    # Amounts $700-1500 not in Jul/Dec: insurance
    if 700 <= amount_abs <= 1500 and month not in [7, 12]:
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
    
    if not mortgage:
        console.print(f"[red]Error: No active mortgage found for property '{property}'[/red]")
        return
    
    mortgage_id = mortgage['id']
    
    # Parse CSV file
    try:
        with open(file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except Exception as e:
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
    
    existing_payment_set = {(p['payment_date'], float(p['amount'])) for p in existing_payments}
    existing_escrow_set = {(e['disbursement_date'], float(e['amount'])) for e in existing_escrow}
    
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
            if (effective_date, float(amount)) in existing_payment_set:
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
            # Escrow transaction
            # CSV amounts are positive, convert to negative for disbursements
            escrow_amount = -abs(amount)
            
            if (effective_date, float(escrow_amount)) in existing_escrow_set:
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
                Decimal('0.00'),  # escrow portion in payment
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
                abs(esc['amount']),  # Store as positive amount in database
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
        
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error during import: {e}[/red]")
    finally:
        cur.close()
        conn.close()

# ============================================================================
# MORTGAGE PROJECT COMMAND (Placeholder)
# ============================================================================

@mortgage.command('project')
@click.argument('property_code')
def mortgage_project(property_code):
    """Generate amortization schedule projection"""
    console.print("[yellow]This command is not yet implemented[/yellow]")
    console.print(f"Would generate projection for: {property_code}")
    console.print("\nThis will create full amortization schedule showing:")
    console.print("- Payment number, date, amount")
    console.print("- Principal and interest breakdown")
    console.print("- Remaining balance after each payment")
    console.print("- Cumulative interest paid")

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
