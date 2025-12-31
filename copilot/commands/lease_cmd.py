"""
Lease tracking and management for rental properties (905brown, 711pine, 819helen)

Comprehensive lease management system tracking:
- Property and lease management
- Tenant and guarantor contact information
- Projected and actual income/expense tracking
- Vacancy tracking and rent adjustments
- P&L comparison and variance analysis
"""

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from copilot.db import execute_query, execute_insert, execute_command, get_connection
from datetime import datetime, timedelta, datetime as dt
from decimal import Decimal

console = Console()

# ============================================================================
# MAIN COMMAND GROUP
# ============================================================================

@click.group()
def lease():
    """Lease tracking and management for rental properties"""
    pass

# ============================================================================
# PROPERTY MANAGEMENT COMMANDS
# ============================================================================

@lease.command('property-list')
def property_list():
    """List all properties"""
    query = """
        SELECT property_code, address, city, state, 
               purchase_date, purchase_price, active
        FROM acc.properties
        ORDER BY property_code
    """
    properties = execute_query(query)
    
    if not properties:
        console.print("[yellow]No properties found[/yellow]")
        return
    
    table = Table(title="Rental Properties")
    table.add_column("Code", style="cyan")
    table.add_column("Address", style="white")
    table.add_column("City", style="white")
    table.add_column("Purchase Date", style="white")
    table.add_column("Purchase Price", style="green", justify="right")
    table.add_column("Status", style="white")
    
    for prop in properties:
        table.add_row(
            prop['property_code'],
            prop['address'],
            f"{prop['city']}, {prop['state']}",
            prop['purchase_date'].strftime('%Y-%m-%d') if prop['purchase_date'] else 'N/A',
            f"${prop['purchase_price']:,.2f}" if prop['purchase_price'] else 'N/A',
            '✓ Active' if prop['active'] else 'Inactive'
        )
    
    console.print(table)

@lease.command('property-show')
@click.argument('property_code')
def property_show(property_code):
    """Show detailed property information"""
    query = """
        SELECT * FROM acc.properties 
        WHERE property_code = %s
    """
    properties = execute_query(query, (property_code,))
    
    if not properties:
        console.print(f"[red]Property '{property_code}' not found[/red]")
        return
    
    prop = properties[0]
    
    console.print(f"\n[bold cyan]Property: {prop['property_code']}[/bold cyan]")
    console.print(f"Address: {prop['address']}")
    console.print(f"City: {prop['city']}, {prop['state']} {prop['zip_code'] or ''}")
    console.print(f"Purchase Date: {prop['purchase_date'].strftime('%Y-%m-%d') if prop['purchase_date'] else 'N/A'}")
    console.print(f"Purchase Price: ${prop['purchase_price']:,.2f}" if prop['purchase_price'] else 'N/A')
    
    if prop['mortgage_amount']:
        console.print(f"\n[bold]Mortgage Information:[/bold]")
        console.print(f"Amount: ${prop['mortgage_amount']:,.2f}")
        console.print(f"Rate: {prop['mortgage_rate']*100:.2f}%" if prop['mortgage_rate'] else 'N/A')
        console.print(f"Start Date: {prop['mortgage_start_date'].strftime('%Y-%m-%d')}" if prop['mortgage_start_date'] else 'N/A')
        console.print(f"Term: {prop['mortgage_term_months']} months" if prop['mortgage_term_months'] else 'N/A')
    
    if prop['notes']:
        console.print(f"\n[bold]Notes:[/bold] {prop['notes']}")

@lease.command('property-update')
@click.argument('property_code')
@click.option('--address', help='Property address')
@click.option('--purchase-date', help='Purchase date (YYYY-MM-DD)')
@click.option('--purchase-price', type=float, help='Purchase price')
@click.option('--mortgage-amount', type=float, help='Mortgage amount')
@click.option('--mortgage-rate', type=float, help='Mortgage rate (e.g., 6.5 for 6.5%)')
@click.option('--active/--inactive', default=None, help='Property active status')
def property_update(property_code, address, purchase_date, purchase_price, 
                   mortgage_amount, mortgage_rate, active):
    """Update property information"""
    updates = []
    params = []
    
    if address:
        updates.append("address = %s")
        params.append(address)
    if purchase_date:
        updates.append("purchase_date = %s")
        params.append(purchase_date)
    if purchase_price is not None:
        updates.append("purchase_price = %s")
        params.append(purchase_price)
    if mortgage_amount is not None:
        updates.append("mortgage_amount = %s")
        params.append(mortgage_amount)
    if mortgage_rate is not None:
        updates.append("mortgage_rate = %s")
        params.append(mortgage_rate / 100.0)  # Convert percentage to decimal
    if active is not None:
        updates.append("active = %s")
        params.append(active)
    
    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        return
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(property_code)
    
    # Build query safely with predefined column names
    update_clause = ', '.join(updates)
    query = f"""
        UPDATE acc.properties 
        SET {update_clause}
        WHERE property_code = %s
    """
    
    execute_command(query, params)
    console.print(f"[green]✓ Property '{property_code}' updated[/green]")

# ============================================================================
# LEASE MANAGEMENT COMMANDS
# ============================================================================

@lease.command('list')
@click.option('--property', help='Filter by property code')
@click.option('--status', type=click.Choice(['active', 'expired', 'terminated', 'pending']), 
              help='Filter by status')
def lease_list(property, status):
    """List all leases"""
    query = """
        SELECT l.id, p.property_code, l.start_date, l.end_date, 
               l.monthly_rent, l.status, l.lease_type,
               COUNT(DISTINCT lt.id) as tenant_count
        FROM acc.leases l
        JOIN acc.properties p ON p.id = l.property_id
        LEFT JOIN acc.lease_tenants lt ON lt.lease_id = l.id
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND p.property_code = %s"
        params.append(property)
    if status:
        query += " AND l.status = %s"
        params.append(status)
    
    query += """
        GROUP BY l.id, p.property_code, l.start_date, l.end_date, 
                 l.monthly_rent, l.status, l.lease_type
        ORDER BY p.property_code, l.start_date DESC
    """
    
    leases = execute_query(query, params or None)
    
    if not leases:
        console.print("[yellow]No leases found[/yellow]")
        return
    
    table = Table(title="Leases")
    table.add_column("ID", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Start Date", style="white")
    table.add_column("End Date", style="white")
    table.add_column("Monthly Rent", style="green", justify="right")
    table.add_column("Tenants", style="white", justify="center")
    table.add_column("Type", style="white")
    table.add_column("Status", style="white")
    
    for lease_item in leases:
        table.add_row(
            str(lease_item['id']),
            lease_item['property_code'],
            lease_item['start_date'].strftime('%Y-%m-%d'),
            lease_item['end_date'].strftime('%Y-%m-%d'),
            f"${lease_item['monthly_rent']:,.2f}",
            str(lease_item['tenant_count']),
            lease_item['lease_type'],
            lease_item['status']
        )
    
    console.print(table)

@lease.command('add')
@click.option('--property', required=True, help='Property code')
@click.option('--start', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='End date (YYYY-MM-DD)')
@click.option('--rent', type=float, required=True, help='Monthly rent amount')
@click.option('--deposit', type=float, default=0, help='Deposit amount')
@click.option('--deposit-last-month', is_flag=True, help='Deposit applies to last month')
@click.option('--lease-type', type=click.Choice(['fixed', 'month-to-month', 'academic']), 
              default='fixed', help='Lease type')
def lease_add(property, start, end, rent, deposit, deposit_last_month, lease_type):
    """Add a new lease"""
    # Get property ID
    prop_query = "SELECT id FROM acc.properties WHERE property_code = %s"
    props = execute_query(prop_query, (property,))
    
    if not props:
        console.print(f"[red]Property '{property}' not found[/red]")
        return
    
    property_id = props[0]['id']
    
    query = """
        INSERT INTO acc.leases 
        (property_id, start_date, end_date, monthly_rent, deposit_amount, 
         deposit_applies_to_last_month, lease_type, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (property_id, start, end, rent, deposit, 
                               deposit_last_month, lease_type))
            lease_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Lease {lease_id} created for {property}[/green]")
            console.print(f"[dim]Use 'copilot lease tenant add {lease_id}' to add tenants[/dim]")
    finally:
        conn.close()

@lease.command('show')
@click.argument('lease_id', type=int)
def lease_show(lease_id):
    """Show detailed lease information"""
    query = """
        SELECT l.*, p.property_code, p.address
        FROM acc.leases l
        JOIN acc.properties p ON p.id = l.property_id
        WHERE l.id = %s
    """
    leases = execute_query(query, (lease_id,))
    
    if not leases:
        console.print(f"[red]Lease {lease_id} not found[/red]")
        return
    
    lease_item = leases[0]
    
    console.print(f"\n[bold cyan]Lease #{lease_item['id']}[/bold cyan]")
    console.print(f"Property: {lease_item['property_code']} - {lease_item['address']}")
    console.print(f"Period: {lease_item['start_date'].strftime('%Y-%m-%d')} to {lease_item['end_date'].strftime('%Y-%m-%d')}")
    console.print(f"Monthly Rent: ${lease_item['monthly_rent']:,.2f}")
    console.print(f"Deposit: ${lease_item['deposit_amount']:,.2f}")
    
    if lease_item['deposit_applies_to_last_month']:
        console.print("[yellow]→ Deposit applies to last month's rent[/yellow]")
    
    console.print(f"Type: {lease_item['lease_type']}")
    console.print(f"Status: {lease_item['status']}")
    
    if lease_item['notes']:
        console.print(f"\n[bold]Notes:[/bold] {lease_item['notes']}")
    
    # Show tenants
    tenant_query = "SELECT * FROM acc.lease_tenants WHERE lease_id = %s ORDER BY is_primary DESC, tenant_name"
    tenants = execute_query(tenant_query, (lease_id,))
    
    if tenants:
        console.print(f"\n[bold]Tenants ({len(tenants)}):[/bold]")
        for tenant in tenants:
            primary = " [PRIMARY]" if tenant['is_primary'] else ""
            student = " (Student)" if tenant['is_student'] else ""
            console.print(f"  • {tenant['tenant_name']}{primary}{student}")
            if tenant['email']:
                console.print(f"    Email: {tenant['email']}")
            if tenant['phone']:
                console.print(f"    Phone: {tenant['phone']}")
    
    # Show guarantors
    guarantor_query = "SELECT * FROM acc.lease_guarantors WHERE lease_id = %s"
    guarantors = execute_query(guarantor_query, (lease_id,))
    
    if guarantors:
        console.print(f"\n[bold]Guarantors ({len(guarantors)}):[/bold]")
        for guarantor in guarantors:
            rel = f" ({guarantor['relationship']})" if guarantor['relationship'] else ""
            console.print(f"  • {guarantor['guarantor_name']}{rel}")
            if guarantor['email']:
                console.print(f"    Email: {guarantor['email']}")
            if guarantor['phone']:
                console.print(f"    Phone: {guarantor['phone']}")

@lease.command('update')
@click.argument('lease_id', type=int)
@click.option('--status', type=click.Choice(['active', 'expired', 'terminated', 'pending']))
@click.option('--rent', type=float, help='Monthly rent amount')
@click.option('--notes', help='Lease notes')
def lease_update(lease_id, status, rent, notes):
    """Update lease information"""
    updates = []
    params = []
    
    if status:
        updates.append("status = %s")
        params.append(status)
    if rent is not None:
        updates.append("monthly_rent = %s")
        params.append(rent)
    if notes:
        updates.append("notes = %s")
        params.append(notes)
    
    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        return
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(lease_id)
    
    # Build query safely with predefined column names
    update_clause = ', '.join(updates)
    query = f"""
        UPDATE acc.leases 
        SET {update_clause}
        WHERE id = %s
    """
    
    execute_command(query, params)
    console.print(f"[green]✓ Lease {lease_id} updated[/green]")

@lease.command('delete')
@click.argument('lease_id', type=int)
@click.option('--force', is_flag=True, help='Skip confirmation')
def lease_delete(lease_id, force):
    """Delete a lease"""
    if not force:
        if not Confirm.ask(f"Delete lease {lease_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    query = "DELETE FROM acc.leases WHERE id = %s"
    execute_command(query, (lease_id,))
    console.print(f"[green]✓ Lease {lease_id} deleted[/green]")

# ============================================================================
# TENANT MANAGEMENT COMMANDS
# ============================================================================

@lease.command('tenant-add')
@click.argument('lease_id', type=int)
@click.option('--name', required=True, help='Tenant name')
@click.option('--email', help='Email address')
@click.option('--phone', help='Phone number')
@click.option('--primary', is_flag=True, help='Primary contact')
@click.option('--student', is_flag=True, help='Is a student')
@click.option('--school', help='School name')
@click.option('--graduation', help='Graduation date (YYYY-MM-DD)')
def tenant_add(lease_id, name, email, phone, primary, student, school, graduation):
    """Add a tenant to a lease"""
    query = """
        INSERT INTO acc.lease_tenants 
        (lease_id, tenant_name, email, phone, is_primary, is_student, 
         school_name, graduation_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (lease_id, name, email, phone, primary, 
                               student, school, graduation))
            tenant_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Tenant '{name}' added to lease {lease_id}[/green]")
    finally:
        conn.close()

@lease.command('tenant-list')
@click.argument('lease_id', type=int)
def tenant_list(lease_id):
    """List tenants for a lease"""
    query = """
        SELECT * FROM acc.lease_tenants 
        WHERE lease_id = %s 
        ORDER BY is_primary DESC, tenant_name
    """
    tenants = execute_query(query, (lease_id,))
    
    if not tenants:
        console.print(f"[yellow]No tenants found for lease {lease_id}[/yellow]")
        return
    
    table = Table(title=f"Tenants for Lease {lease_id}")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Email", style="white")
    table.add_column("Phone", style="white")
    table.add_column("Primary", style="white")
    table.add_column("Student", style="white")
    table.add_column("School", style="white")
    
    for tenant in tenants:
        table.add_row(
            str(tenant['id']),
            tenant['tenant_name'],
            tenant['email'] or '',
            tenant['phone'] or '',
            '✓' if tenant['is_primary'] else '',
            '✓' if tenant['is_student'] else '',
            tenant['school_name'] or ''
        )
    
    console.print(table)

@lease.command('tenant-remove')
@click.argument('tenant_id', type=int)
@click.option('--force', is_flag=True, help='Skip confirmation')
def tenant_remove(tenant_id, force):
    """Remove a tenant from a lease"""
    if not force:
        if not Confirm.ask(f"Remove tenant {tenant_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    query = "DELETE FROM acc.lease_tenants WHERE id = %s"
    execute_command(query, (tenant_id,))
    console.print(f"[green]✓ Tenant {tenant_id} removed[/green]")

# ============================================================================
# GUARANTOR MANAGEMENT COMMANDS
# ============================================================================

@lease.command('guarantor-add')
@click.argument('lease_id', type=int)
@click.option('--name', required=True, help='Guarantor name')
@click.option('--relationship', help='Relationship to tenant')
@click.option('--email', help='Email address')
@click.option('--phone', help='Phone number')
@click.option('--address', help='Street address')
@click.option('--city', help='City')
@click.option('--state', help='State')
@click.option('--zip', help='ZIP code')
def guarantor_add(lease_id, name, relationship, email, phone, address, city, state, zip):
    """Add a guarantor to a lease"""
    query = """
        INSERT INTO acc.lease_guarantors 
        (lease_id, guarantor_name, relationship, email, phone, 
         address_line1, city, state, zip_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (lease_id, name, relationship, email, phone, 
                               address, city, state, zip))
            guarantor_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Guarantor '{name}' added to lease {lease_id}[/green]")
    finally:
        conn.close()

@lease.command('guarantor-list')
@click.argument('lease_id', type=int)
def guarantor_list(lease_id):
    """List guarantors for a lease"""
    query = """
        SELECT * FROM acc.lease_guarantors 
        WHERE lease_id = %s 
        ORDER BY guarantor_name
    """
    guarantors = execute_query(query, (lease_id,))
    
    if not guarantors:
        console.print(f"[yellow]No guarantors found for lease {lease_id}[/yellow]")
        return
    
    table = Table(title=f"Guarantors for Lease {lease_id}")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Relationship", style="white")
    table.add_column("Email", style="white")
    table.add_column("Phone", style="white")
    table.add_column("Address", style="white")
    
    for guarantor in guarantors:
        address_parts = [guarantor['address_line1'], guarantor['city'], guarantor['state'], guarantor['zip_code']]
        address = ', '.join(filter(None, address_parts))
        
        table.add_row(
            str(guarantor['id']),
            guarantor['guarantor_name'],
            guarantor['relationship'] or '',
            guarantor['email'] or '',
            guarantor['phone'] or '',
            address
        )
    
    console.print(table)

# ============================================================================
# EXPENSE MANAGEMENT COMMANDS
# ============================================================================

@lease.command('expense-add')
@click.argument('property_code')
@click.option('--type', 'expense_type', required=True, 
              type=click.Choice(['summer_tax', 'winter_tax', 'insurance', 'hoa', 'maintenance', 'utilities', 'other']))
@click.option('--name', required=True, help='Expense name')
@click.option('--amount', type=float, required=True, help='Amount')
@click.option('--frequency', type=click.Choice(['monthly', 'quarterly', 'annual', 'one-time']), 
              default='annual', help='Frequency')
@click.option('--due-month', type=int, help='Due month (1-12) for annual/quarterly expenses')
def expense_add(property_code, expense_type, name, amount, frequency, due_month):
    """Add a projected expense for a property"""
    # Get property ID
    prop_query = "SELECT id FROM acc.properties WHERE property_code = %s"
    props = execute_query(prop_query, (property_code,))
    
    if not props:
        console.print(f"[red]Property '{property_code}' not found[/red]")
        return
    
    property_id = props[0]['id']
    
    query = """
        INSERT INTO acc.property_expenses 
        (property_id, expense_type, expense_name, amount, frequency, due_month)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (property_id, expense_type, name, amount, frequency, due_month))
            expense_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Expense '{name}' added to {property_code}[/green]")
    finally:
        conn.close()

@lease.command('expense-list')
@click.argument('property_code')
def expense_list(property_code):
    """List projected expenses for a property"""
    query = """
        SELECT pe.id, pe.expense_type, pe.expense_name, pe.amount, 
               pe.frequency, pe.due_month, pe.active
        FROM acc.property_expenses pe
        JOIN acc.properties p ON p.id = pe.property_id
        WHERE p.property_code = %s
        ORDER BY pe.expense_type, pe.expense_name
    """
    expenses = execute_query(query, (property_code,))
    
    if not expenses:
        console.print(f"[yellow]No expenses found for {property_code}[/yellow]")
        return
    
    table = Table(title=f"Projected Expenses for {property_code}")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Name", style="white")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Frequency", style="white")
    table.add_column("Due Month", style="white")
    table.add_column("Status", style="white")
    
    for expense in expenses:
        table.add_row(
            str(expense['id']),
            expense['expense_type'],
            expense['expense_name'],
            f"${expense['amount']:,.2f}",
            expense['frequency'],
            str(expense['due_month']) if expense['due_month'] else 'N/A',
            '✓ Active' if expense['active'] else 'Inactive'
        )
    
    console.print(table)

@lease.command('expense-remove')
@click.argument('expense_id', type=int)
@click.option('--force', is_flag=True, help='Skip confirmation')
def expense_remove(expense_id, force):
    """Remove a projected expense"""
    if not force:
        if not Confirm.ask(f"Remove expense {expense_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    query = "DELETE FROM acc.property_expenses WHERE id = %s"
    execute_command(query, (expense_id,))
    console.print(f"[green]✓ Expense {expense_id} removed[/green]")

# ============================================================================
# PAYMENT TRACKING COMMANDS
# ============================================================================

@lease.command('payment-add')
@click.option('--property', required=True, help='Property code')
@click.option('--lease', 'lease_id', type=int, help='Lease ID (optional, will auto-detect)')
@click.option('--amount', type=float, required=True, help='Payment amount')
@click.option('--date', required=True, help='Payment date (YYYY-MM-DD)')
@click.option('--for-month', required=True, help='Month this payment is for (YYYY-MM-DD)')
@click.option('--method', default='check', help='Payment method')
@click.option('--check-number', help='Check number')
@click.option('--status', type=click.Choice(['received', 'bounced', 'partial', 'waived', 'pending']), 
              default='received')
def payment_add(property, lease_id, amount, date, for_month, method, check_number, status):
    """Record a rent payment"""
    # Get property ID
    prop_query = "SELECT id FROM acc.properties WHERE property_code = %s"
    props = execute_query(prop_query, (property,))
    
    if not props:
        console.print(f"[red]Property '{property}' not found[/red]")
        return
    
    property_id = props[0]['id']
    
    # Auto-detect lease if not provided
    if not lease_id:
        lease_query = """
            SELECT id FROM acc.leases 
            WHERE property_id = %s 
            AND %s BETWEEN start_date AND end_date
            AND status = 'active'
            ORDER BY start_date DESC
            LIMIT 1
        """
        leases = execute_query(lease_query, (property_id, for_month))
        
        if leases:
            lease_id = leases[0]['id']
        else:
            console.print(f"[red]No active lease found for {property} covering {for_month}[/red]")
            return
    
    query = """
        INSERT INTO acc.rent_payments 
        (lease_id, property_id, payment_date, amount, for_month, 
         payment_method, payment_status, check_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (lease_id, property_id, date, amount, for_month, 
                               method, status, check_number))
            payment_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Payment of ${amount:,.2f} recorded for {property}[/green]")
    finally:
        conn.close()

@lease.command('payment-list')
@click.option('--property', help='Filter by property code')
@click.option('--lease', 'lease_id', type=int, help='Filter by lease ID')
@click.option('--year', type=int, help='Filter by year')
@click.option('--month', type=int, help='Filter by month')
def payment_list(property, lease_id, year, month):
    """List rent payments"""
    query = """
        SELECT rp.id, p.property_code, rp.lease_id, rp.payment_date, 
               rp.amount, rp.for_month, rp.payment_method, 
               rp.payment_status, rp.check_number
        FROM acc.rent_payments rp
        JOIN acc.properties p ON p.id = rp.property_id
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND p.property_code = %s"
        params.append(property)
    if lease_id:
        query += " AND rp.lease_id = %s"
        params.append(lease_id)
    if year:
        query += " AND EXTRACT(YEAR FROM rp.for_month) = %s"
        params.append(year)
    if month:
        query += " AND EXTRACT(MONTH FROM rp.for_month) = %s"
        params.append(month)
    
    query += " ORDER BY rp.payment_date DESC"
    
    payments = execute_query(query, params or None)
    
    if not payments:
        console.print("[yellow]No payments found[/yellow]")
        return
    
    table = Table(title="Rent Payments")
    table.add_column("ID", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Lease", style="white")
    table.add_column("Payment Date", style="white")
    table.add_column("For Month", style="white")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Method", style="white")
    table.add_column("Status", style="white")
    
    for payment in payments:
        status_color = "green" if payment['payment_status'] == 'received' else "yellow"
        
        table.add_row(
            str(payment['id']),
            payment['property_code'],
            str(payment['lease_id']),
            payment['payment_date'].strftime('%Y-%m-%d'),
            payment['for_month'].strftime('%Y-%m'),
            f"${payment['amount']:,.2f}",
            payment['payment_method'],
            f"[{status_color}]{payment['payment_status']}[/{status_color}]"
        )
    
    console.print(table)

# ============================================================================
# ACTUAL EXPENSE COMMANDS
# ============================================================================

@lease.command('actual-expense-add')
@click.argument('property_code')
@click.option('--date', required=True, help='Expense date (YYYY-MM-DD)')
@click.option('--type', 'expense_type', required=True,
              type=click.Choice(['summer_tax', 'winter_tax', 'insurance', 'hoa', 'repair', 
                               'maintenance', 'utilities', 'mortgage', 'other']))
@click.option('--description', required=True, help='Expense description')
@click.option('--amount', type=float, required=True, help='Amount')
@click.option('--vendor', help='Vendor name')
@click.option('--check-number', help='Check number')
def actual_expense_add(property_code, date, expense_type, description, amount, vendor, check_number):
    """Record an actual property expense"""
    # Get property ID
    prop_query = "SELECT id FROM acc.properties WHERE property_code = %s"
    props = execute_query(prop_query, (property_code,))
    
    if not props:
        console.print(f"[red]Property '{property_code}' not found[/red]")
        return
    
    property_id = props[0]['id']
    
    query = """
        INSERT INTO acc.property_actual_expenses 
        (property_id, expense_date, expense_type, description, amount, 
         vendor, check_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (property_id, date, expense_type, description, 
                               amount, vendor, check_number))
            expense_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Expense of ${amount:,.2f} recorded for {property_code}[/green]")
    finally:
        conn.close()

# ============================================================================
# VACANCY TRACKING COMMANDS
# ============================================================================

@lease.command('vacancy-add')
@click.argument('property_code')
@click.option('--start', required=True, help='Vacancy start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='Vacancy end date (YYYY-MM-DD)')
@click.option('--rent', type=float, required=True, help='Expected monthly rent')
@click.option('--reason', help='Reason for vacancy')
def vacancy_add(property_code, start, end, rent, reason):
    """Record a vacancy period"""
    # Get property ID
    prop_query = "SELECT id FROM acc.properties WHERE property_code = %s"
    props = execute_query(prop_query, (property_code,))
    
    if not props:
        console.print(f"[red]Property '{property_code}' not found[/red]")
        return
    
    property_id = props[0]['id']
    
    query = """
        INSERT INTO acc.property_vacancy 
        (property_id, start_date, end_date, expected_monthly_rent, reason)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (property_id, start, end, rent, reason))
            vacancy_id = cur.fetchone()[0]
            conn.commit()
            
            # Calculate lost rent using actual dates
            start_dt = dt.strptime(start, '%Y-%m-%d')
            end_dt = dt.strptime(end, '%Y-%m-%d')
            days = (end_dt - start_dt).days + 1
            # Note: This is an estimate. Actual calculation should use daily rate
            # For more accurate calculation, see the vacancy_monthly view
            lost_rent = (days / 30.0) * rent
            
            console.print(f"[green]✓ Vacancy period recorded for {property_code}[/green]")
            console.print(f"[dim]Duration: {days} days, Estimated lost rent: ${lost_rent:,.2f}[/dim]")
    finally:
        conn.close()

@lease.command('vacancy-list')
@click.option('--property', help='Filter by property code')
def vacancy_list(property):
    """List vacancy periods"""
    query = """
        SELECT v.id, p.property_code, v.start_date, v.end_date, 
               v.expected_monthly_rent, v.reason
        FROM acc.property_vacancy v
        JOIN acc.properties p ON p.id = v.property_id
        WHERE 1=1
    """
    params = []
    
    if property:
        query += " AND p.property_code = %s"
        params.append(property)
    
    query += " ORDER BY v.start_date DESC"
    
    vacancies = execute_query(query, params or None)
    
    if not vacancies:
        console.print("[yellow]No vacancy periods found[/yellow]")
        return
    
    table = Table(title="Vacancy Periods")
    table.add_column("ID", style="cyan")
    table.add_column("Property", style="white")
    table.add_column("Start Date", style="white")
    table.add_column("End Date", style="white")
    table.add_column("Days", style="white", justify="right")
    table.add_column("Expected Rent", style="green", justify="right")
    table.add_column("Lost Rent", style="red", justify="right")
    table.add_column("Reason", style="white")
    
    for vacancy in vacancies:
        days = (vacancy['end_date'] - vacancy['start_date']).days + 1
        lost_rent = (days / 30.0) * float(vacancy['expected_monthly_rent'])
        
        table.add_row(
            str(vacancy['id']),
            vacancy['property_code'],
            vacancy['start_date'].strftime('%Y-%m-%d'),
            vacancy['end_date'].strftime('%Y-%m-%d'),
            str(days),
            f"${vacancy['expected_monthly_rent']:,.2f}",
            f"${lost_rent:,.2f}",
            vacancy['reason'] or ''
        )
    
    console.print(table)

# ============================================================================
# ADJUSTMENT COMMANDS
# ============================================================================

@lease.command('adjustment-add')
@click.argument('lease_id', type=int)
@click.option('--date', required=True, help='Adjustment date (YYYY-MM-DD)')
@click.option('--type', 'adjustment_type', required=True,
              type=click.Choice(['late_fee', 'credit', 'concession', 'damage', 'other']))
@click.option('--amount', type=float, required=True, help='Amount (positive for charges, negative for credits)')
@click.option('--description', required=True, help='Description')
@click.option('--for-month', help='Month this applies to (YYYY-MM-DD)')
def adjustment_add(lease_id, date, adjustment_type, amount, description, for_month):
    """Add a rent adjustment (late fee, credit, etc.)"""
    # Get property ID from lease
    lease_query = "SELECT property_id FROM acc.leases WHERE id = %s"
    leases = execute_query(lease_query, (lease_id,))
    
    if not leases:
        console.print(f"[red]Lease {lease_id} not found[/red]")
        return
    
    property_id = leases[0]['property_id']
    
    query = """
        INSERT INTO acc.rent_adjustments 
        (lease_id, property_id, adjustment_date, adjustment_type, 
         amount, description, for_month)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (lease_id, property_id, date, adjustment_type, 
                               amount, description, for_month))
            adjustment_id = cur.fetchone()[0]
            conn.commit()
            console.print(f"[green]✓ Adjustment of ${amount:,.2f} recorded for lease {lease_id}[/green]")
    finally:
        conn.close()

# ============================================================================
# REPORT COMMANDS
# ============================================================================

@lease.command('contacts')
def contacts():
    """Show contact directory for active leases"""
    query = "SELECT * FROM acc.v_lease_contact_directory ORDER BY property_code, lease_id, contact_type"
    contacts_data = execute_query(query)
    
    if not contacts_data:
        console.print("[yellow]No active lease contacts found[/yellow]")
        return
    
    table = Table(title="Lease Contact Directory")
    table.add_column("Property", style="cyan")
    table.add_column("Lease", style="white")
    table.add_column("Type", style="white")
    table.add_column("Name", style="white")
    table.add_column("Email", style="white")
    table.add_column("Phone", style="white")
    table.add_column("Notes", style="dim")
    
    for contact in contacts_data:
        notes = []
        if contact['is_primary']:
            notes.append("PRIMARY")
        if contact['is_student']:
            notes.append(f"Student@{contact['school_name']}")
        if contact['relationship']:
            notes.append(contact['relationship'])
        
        table.add_row(
            contact['property_code'],
            str(contact['lease_id']),
            contact['contact_type'],
            contact['contact_name'],
            contact['email'] or '',
            contact['phone'] or '',
            ', '.join(notes)
        )
    
    console.print(table)

@lease.command('status')
def status():
    """Show current lease status summary"""
    query = "SELECT * FROM acc.v_lease_details WHERE lease_status = 'active' ORDER BY property_code"
    leases = execute_query(query)
    
    if not leases:
        console.print("[yellow]No active leases found[/yellow]")
        return
    
    table = Table(title="Active Lease Status")
    table.add_column("Property", style="cyan")
    table.add_column("Primary Tenant", style="white")
    table.add_column("Start Date", style="white")
    table.add_column("End Date", style="white")
    table.add_column("Rent", style="green", justify="right")
    table.add_column("Tenants", style="white", justify="center")
    table.add_column("Contact", style="white")
    
    for lease_item in leases:
        table.add_row(
            lease_item['property_code'],
            lease_item['primary_tenant'] or lease_item['tenant_names'] or 'N/A',
            lease_item['start_date'].strftime('%Y-%m-%d'),
            lease_item['end_date'].strftime('%Y-%m-%d'),
            f"${lease_item['monthly_rent']:,.2f}",
            str(lease_item['tenant_count']),
            lease_item['primary_email'] or lease_item['primary_phone'] or 'N/A'
        )
    
    console.print(table)

@lease.command('report')
@click.option('--year', type=int, required=True, help='Year for report')
@click.option('--type', 'report_type', type=click.Choice(['calendar', 'academic']), 
              default='calendar', help='Report type')
def report(year, report_type):
    """Generate income report (calendar or academic year)"""
    if report_type == 'academic':
        # Academic year: June to May
        start_month = 6
        year_label = f"Academic Year {year}-{year+1}"
    else:
        # Calendar year
        start_month = 1
        year_label = f"Calendar Year {year}"
    
    query = """
        SELECT property_code, month, 
               SUM(projected_rent) as projected,
               SUM(actual_rent) as actual
        FROM acc.v_property_monthly_comparison
        WHERE year = %s
        GROUP BY property_code, month
        ORDER BY property_code, month
    """
    
    data = execute_query(query, (year,))
    
    if not data:
        console.print(f"[yellow]No data found for {year}[/yellow]")
        return
    
    console.print(f"\n[bold cyan]{year_label} Income Report[/bold cyan]\n")
    
    # Group by property
    properties = {}
    for row in data:
        prop = row['property_code']
        if prop not in properties:
            properties[prop] = []
        properties[prop].append(row)
    
    # Display each property
    for prop, months in properties.items():
        console.print(f"\n[bold]{prop}[/bold]")
        
        table = Table()
        table.add_column("Month", style="white")
        table.add_column("Projected", style="green", justify="right")
        table.add_column("Actual", style="green", justify="right")
        table.add_column("Variance", style="white", justify="right")
        
        total_proj = 0
        total_actual = 0
        
        for month in months:
            projected = float(month['projected'] or 0)
            actual = float(month['actual'] or 0)
            variance = actual - projected
            
            total_proj += projected
            total_actual += actual
            
            variance_color = "green" if variance >= 0 else "red"
            
            table.add_row(
                f"{year}-{month['month']:02d}",
                f"${projected:,.2f}",
                f"${actual:,.2f}",
                f"[{variance_color}]${variance:,.2f}[/{variance_color}]"
            )
        
        # Add totals row
        total_variance = total_actual - total_proj
        variance_color = "green" if total_variance >= 0 else "red"
        
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]${total_proj:,.2f}[/bold]",
            f"[bold]${total_actual:,.2f}[/bold]",
            f"[bold {variance_color}]${total_variance:,.2f}[/bold {variance_color}]"
        )
        
        console.print(table)

@lease.command('compare')
@click.option('--year', type=int, required=True, help='Year for comparison')
@click.option('--property', help='Filter by property code')
def compare(year, property):
    """Compare projected vs actual P&L with variance analysis"""
    query = """
        SELECT * FROM acc.v_property_pnl_comparison
        WHERE year = %s
    """
    params = [year]
    
    if property:
        query += " AND property_code = %s"
        params.append(property)
    
    query += " ORDER BY property_code"
    
    data = execute_query(query, params)
    
    if not data:
        console.print(f"[yellow]No data found for {year}[/yellow]")
        return
    
    console.print(f"\n[bold cyan]P&L Comparison for {year}[/bold cyan]\n")
    
    for row in data:
        console.print(f"\n[bold]{row['property_code']}[/bold]")
        
        # Income section
        console.print("\n[bold]INCOME[/bold]")
        console.print(f"  Projected Rent:        ${float(row['total_projected_rent']):>12,.2f}")
        console.print(f"  Actual Rent Received:  ${float(row['total_actual_rent']):>12,.2f}")
        console.print(f"  Adjustments:           ${float(row['total_adjustments']):>12,.2f}")
        console.print(f"  [bold]Total Actual Income:   ${float(row['total_actual_income']):>12,.2f}[/bold]")
        
        income_var = float(row['total_income_variance'])
        var_color = "red" if income_var > 0 else "green"
        console.print(f"  [{var_color}]Income Variance:       ${income_var:>12,.2f}[/{var_color}]")
        
        if float(row['total_vacancy_loss']) > 0:
            console.print(f"  [yellow]Vacancy Loss:          ${float(row['total_vacancy_loss']):>12,.2f}[/yellow]")
        if float(row['total_bounced']) > 0:
            console.print(f"  [red]Bounced Checks:        ${float(row['total_bounced']):>12,.2f}[/red]")
        if float(row['total_waived']) > 0:
            console.print(f"  [yellow]Waived Rent:           ${float(row['total_waived']):>12,.2f}[/yellow]")
        
        # Expense section
        console.print("\n[bold]EXPENSES[/bold]")
        console.print(f"  Projected Expenses:    ${float(row['total_projected_expenses']):>12,.2f}")
        console.print(f"  Actual Expenses:       ${float(row['total_actual_expenses']):>12,.2f}")
        
        expense_var = float(row['expense_variance'])
        exp_var_color = "green" if expense_var > 0 else "red"
        console.print(f"  [{exp_var_color}]Expense Variance:      ${expense_var:>12,.2f}[/{exp_var_color}]")
        
        # Net income section
        console.print("\n[bold]NET INCOME[/bold]")
        console.print(f"  Projected Net Income:  ${float(row['projected_net_income']):>12,.2f}")
        console.print(f"  Actual Net Income:     ${float(row['actual_net_income']):>12,.2f}")
        
        net_var = float(row['net_income_variance'])
        net_var_color = "green" if net_var > 0 else "red"
        console.print(f"  [{net_var_color}]Net Income Variance:   ${net_var:>12,.2f}[/{net_var_color}]")

if __name__ == '__main__':
    lease()
