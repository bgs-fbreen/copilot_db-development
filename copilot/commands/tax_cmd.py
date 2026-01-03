"""
Property tax tracking and foreclosure risk management

Comprehensive tax management system tracking:
- Tax bill tracking with assessment values
- Foreclosure risk analysis (3+ years delinquent)
- Payment priority recommendations
- Assessment and tax trend analysis
- Multi-format export (CSV, JSON, PDF)
"""

import click
import csv
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from copilot.db import execute_query
from datetime import datetime
from decimal import Decimal

console = Console()

# ============================================================================
# MAIN COMMAND GROUP
# ============================================================================

@click.group()
def tax():
    """Property tax tracking and foreclosure risk management"""
    pass

# ============================================================================
# FORECLOSURE RISK COMMAND
# ============================================================================

@tax.command('foreclosure')
@click.option('--property', '-p', 'property_code', help='Filter by property code')
def tax_foreclosure(property_code):
    """Show properties at risk of tax foreclosure (3+ years delinquent)"""
    
    # Build query
    query = """
        SELECT 
            property_code,
            tax_year,
            tax_season,
            balance_due,
            years_delinquent,
            risk_level
        FROM acc.v_property_tax_foreclosure_risk
    """
    
    params = None
    if property_code:
        query += " WHERE property_code = %s"
        params = (property_code,)
    
    query += " ORDER BY years_delinquent DESC, tax_year, property_code"
    
    results = execute_query(query, params)
    
    if not results:
        if property_code:
            console.print(f"[green]✓ No foreclosure risk for property {property_code}[/green]")
        else:
            console.print("[green]✓ No properties at foreclosure risk[/green]")
        return
    
    # Display header
    console.print()
    console.print(Panel.fit(
        "⚠️  TAX FORECLOSURE RISK REPORT",
        style="bold red"
    ))
    console.print()
    console.print("[yellow]Properties with taxes delinquent 3+ years are at risk of foreclosure![/yellow]")
    console.print()
    
    # Create table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Property", style="cyan")
    table.add_column("Year", style="white")
    table.add_column("Season", style="white")
    table.add_column("Balance", style="red", justify="right")
    table.add_column("Years Overdue", style="yellow", justify="center")
    table.add_column("Risk Level", style="white", justify="center")
    
    total_at_risk = Decimal('0.00')
    
    for row in results:
        # Format risk level with emoji
        risk_emoji = {
            'CRITICAL': '🔴',
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(row['risk_level'], '⚪')
        
        risk_display = f"{risk_emoji} {row['risk_level']}"
        
        table.add_row(
            row['property_code'],
            str(row['tax_year']),
            row['tax_season'],
            f"${row['balance_due']:>10,.2f}",
            f"{int(row['years_delinquent'])} years",
            risk_display
        )
        
        total_at_risk += row['balance_due']
    
    console.print(table)
    console.print()
    console.print(f"[bold red]TOTAL AT RISK: ${total_at_risk:,.2f}[/bold red]")
    console.print()
    console.print("[bold yellow]⚠️  ACTION REQUIRED: Pay these bills immediately to avoid property seizure![/bold yellow]")
    console.print()

# ============================================================================
# PAYMENT PRIORITY COMMAND
# ============================================================================

@tax.command('priority')
@click.option('--property', '-p', 'property_code', help='Filter by property code')
@click.option('--limit', '-n', default=20, help='Number of bills to show')
def tax_priority(property_code, limit):
    """Show recommended payment priority order"""
    
    # Build query
    query = """
        SELECT 
            property_code,
            tax_year,
            tax_season,
            total_due,
            total_paid,
            balance_due,
            years_delinquent,
            priority_rank,
            priority_reason
        FROM acc.v_property_tax_priority
    """
    
    params = None
    if property_code:
        query += " WHERE property_code = %s"
        params = (property_code,)
    
    query += f" ORDER BY priority_rank, tax_year, tax_season LIMIT {limit}"
    
    results = execute_query(query, params)
    
    if not results:
        if property_code:
            console.print(f"[green]✓ No outstanding taxes for property {property_code}[/green]")
        else:
            console.print("[green]✓ No outstanding taxes[/green]")
        return
    
    # Display header
    console.print()
    console.print(Panel.fit(
        "PAYMENT PRIORITY LIST",
        style="bold cyan"
    ))
    console.print()
    
    # Create table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Priority", style="white", justify="center", width=8)
    table.add_column("Property", style="cyan")
    table.add_column("Year", style="white")
    table.add_column("Season", style="white")
    table.add_column("Balance", style="yellow", justify="right")
    table.add_column("Risk", style="white")
    table.add_column("Reason", style="white")
    
    foreclosure_total = Decimal('0.00')
    total_outstanding = Decimal('0.00')
    foreclosure_count = 0
    
    for idx, row in enumerate(results, 1):
        # Determine risk emoji
        if 'CRITICAL' in row['priority_reason']:
            risk_emoji = '🔴'
            risk_text = 'CRITICAL'
        elif 'HIGH' in row['priority_reason']:
            risk_emoji = '🔴'
            risk_text = 'HIGH'
        elif 'MEDIUM' in row['priority_reason']:
            risk_emoji = '🟡'
            risk_text = 'MEDIUM'
        else:
            risk_emoji = '🟢'
            risk_text = 'LOW'
        
        # Extract reason
        reason_parts = row['priority_reason'].split(' - ')
        reason = reason_parts[1] if len(reason_parts) > 1 else row['priority_reason']
        
        priority_display = f"{risk_emoji} {idx}"
        
        table.add_row(
            priority_display,
            row['property_code'],
            str(row['tax_year']),
            row['tax_season'],
            f"${row['balance_due']:>10,.2f}",
            risk_text,
            reason
        )
        
        # Track foreclosure items (priority 1-2 = critical/high)
        if row['priority_rank'] <= 2:
            foreclosure_total += row['balance_due']
            foreclosure_count = idx
        
        total_outstanding += row['balance_due']
    
    console.print(table)
    console.print()
    
    if foreclosure_count > 0:
        console.print(f"[bold red]MINIMUM TO AVOID FORECLOSURE: ${foreclosure_total:,.2f} (items 1-{foreclosure_count})[/bold red]")
    console.print(f"[bold]TOTAL OUTSTANDING:            ${total_outstanding:,.2f}[/bold]")
    console.print()

# ============================================================================
# TRENDS ANALYSIS COMMAND
# ============================================================================

@tax.command('trends')
@click.argument('property_code')
@click.option('--years', '-y', default=10, help='Number of years to show')
def tax_trends(property_code, years):
    """Show assessment and tax trends over time"""
    
    # Get trend data
    query = """
        SELECT 
            property_code,
            tax_year,
            assessed_value,
            taxable_value,
            pre_pct,
            annual_tax,
            annual_paid,
            annual_balance,
            prev_assessed,
            prev_tax
        FROM acc.v_property_tax_trends
        WHERE property_code = %s
        ORDER BY tax_year DESC
        LIMIT %s
    """
    
    results = execute_query(query, (property_code, years))
    
    if not results:
        console.print(f"[red]No tax data found for property {property_code}[/red]")
        return
    
    # Reverse for chronological order
    results = list(reversed(results))
    
    # Calculate year range
    year_start = results[0]['tax_year']
    year_end = results[-1]['tax_year']
    
    # Display header
    console.print()
    console.print(Panel.fit(
        f"TAX TRENDS: {property_code} ({year_start}-{year_end})",
        style="bold cyan"
    ))
    console.print()
    
    # Draw assessed value chart
    console.print("[bold]ASSESSED VALUE TREND:[/bold]")
    _draw_ascii_chart(
        [r['assessed_value'] for r in results if r['assessed_value']],
        [r['tax_year'] for r in results if r['assessed_value']],
        prefix='$'
    )
    console.print()
    
    # Draw annual tax chart
    console.print("[bold]ANNUAL TAX TREND:[/bold]")
    _draw_ascii_chart(
        [r['annual_tax'] for r in results if r['annual_tax']],
        [r['tax_year'] for r in results if r['annual_tax']],
        prefix='$'
    )
    console.print()
    
    # Check for PRE exemption loss
    pre_lost_year = _find_pre_exemption_lost_year(results)
    
    if pre_lost_year:
        console.print(f"                         ↑")
        console.print(f"                   PRE Exemption Lost")
        console.print()
    
    # Year-over-year changes table
    console.print("[bold]Year-over-Year Changes:[/bold]")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Year", style="cyan")
    table.add_column("Assessed", style="white", justify="right")
    table.add_column("Change", style="white", justify="right")
    table.add_column("Annual Tax", style="yellow", justify="right")
    table.add_column("Change", style="white", justify="right")
    table.add_column("PRE%", style="white", justify="right")
    
    for row in results:
        # Calculate changes
        if row['prev_assessed'] and row['assessed_value']:
            assessed_change = ((row['assessed_value'] - row['prev_assessed']) / row['prev_assessed']) * 100
            assessed_change_str = f"+ {assessed_change:.1f}%" if assessed_change >= 0 else f"{assessed_change:.1f}%"
        else:
            assessed_change_str = "-"
        
        if row['prev_tax'] and row['annual_tax']:
            tax_change = ((row['annual_tax'] - row['prev_tax']) / row['prev_tax']) * 100
            tax_change_str = f"+ {tax_change:.1f}%" if tax_change >= 0 else f"{tax_change:.1f}%"
        else:
            tax_change_str = "-"
        
        # Highlight PRE exemption loss
        pre_str = f"{row['pre_pct']:.0f}%" if row['pre_pct'] else "0%"
        warning = ""
        if row['tax_year'] == pre_lost_year:
            warning = "  ⚠️"
            tax_change_str = f"[bold red]{tax_change_str}[/bold red]"
        
        table.add_row(
            str(row['tax_year']),
            f"${row['assessed_value']:>10,.0f}" if row['assessed_value'] else "N/A",
            assessed_change_str,
            f"${row['annual_tax']:>10,.2f}" if row['annual_tax'] else "N/A",
            tax_change_str,
            pre_str + warning
        )
    
    console.print(table)
    
    if pre_lost_year:
        console.print()
        console.print(f"[yellow]⚠️ Note: PRE exemption lost in {pre_lost_year} caused significant tax increase[/yellow]")
    
    console.print()

def _find_pre_exemption_lost_year(results):
    """Find the year when PRE exemption was lost"""
    for i, r in enumerate(results):
        if i > 0:
            prev_had_pre = results[i-1]['pre_pct'] and results[i-1]['pre_pct'] > 0
            curr_no_pre = not r['pre_pct'] or r['pre_pct'] == 0
            if prev_had_pre and curr_no_pre:
                return r['tax_year']
    return None

def _draw_ascii_chart(values, labels, prefix='', height=8, width=60):
    """Draw a simple ASCII bar chart with properly aligned x-axis labels"""
    
    # Filter out None values
    valid_data = [(v, l) for v, l in zip(values, labels) if v is not None]
    
    if not valid_data:
        console.print("[dim]No data available[/dim]")
        return
    
    values, labels = zip(*valid_data)
    
    max_val = max(values)
    min_val = min(values)
    val_range = max_val - min_val if max_val != min_val else max_val
    
    if val_range == 0:
        val_range = max_val if max_val > 0 else 1  # Prevent division by zero
    
    # Fixed column width: 4 chars for bar + 3 chars spacing = 7 chars per column
    col_width = 7
    bar_char = "████"
    
    # Y-axis label width (for alignment)
    y_label_width = 9  # "$ XX,XXX |"
    
    # Generate Y-axis labels
    y_labels = []
    for i in range(height):
        val = max_val - (i * val_range / (height - 1))
        y_labels.append(f"{prefix}{val:>7,.0f}")
    
    # Draw chart rows
    for i in range(height):
        threshold = max_val - (i * val_range / (height - 1))
        line = y_labels[i] + " |"
        
        for val in values:
            if val >= threshold:
                line += f" {bar_char}  "  # 1 space + 4 bar + 2 space = 7 chars
            else:
                line += " " * col_width
        
        console.print(line)
    
    # Draw X-axis line
    x_axis_line = "─" * (len(labels) * col_width + 1)
    console.print(f"{' ' * y_label_width}└{x_axis_line}")
    
    # Draw X-axis labels (aligned with each column)
    label_line = " "  # Initial space after └
    for label in labels:
        label_line += f" {str(label)}  "  # 1 space + 4 year + 2 space = 7 chars
    console.print(f"{' ' * y_label_width}{label_line}")

# ============================================================================
# EXPORT COMMAND
# ============================================================================

@tax.command('export')
@click.option('--property', '-p', 'property_code', help='Filter by property code')
@click.option('--year', '-y', type=int, help='Filter by tax year')
@click.option('--format', '-f', 'output_format', type=click.Choice(['csv', 'json', 'pdf']), default='csv')
@click.option('--output', '-o', 'output_file', help='Output file path')
@click.option('--report', '-r', type=click.Choice(['summary', 'detail', 'owed', 'history']), default='summary')
def tax_export(property_code, year, output_format, output_file, report):
    """Export tax data to CSV, JSON, or PDF"""
    
    # Build query based on report type
    if report == 'owed':
        query = """
            SELECT 
                property_code,
                tax_year,
                tax_season,
                total_due,
                total_paid,
                balance_due,
                payment_status,
                due_date
            FROM acc.property_tax_bill
            WHERE balance_due > 0
        """
    elif report == 'history':
        query = """
            SELECT 
                b.property_code,
                b.tax_year,
                b.tax_season,
                b.assessed_value,
                b.taxable_value,
                b.pre_pct,
                b.total_due,
                b.total_paid,
                b.balance_due,
                b.payment_status,
                b.due_date,
                b.paid_date
            FROM acc.property_tax_bill b
        """
    elif report == 'detail':
        query = """
            SELECT 
                b.property_code,
                b.tax_year,
                b.tax_season,
                b.assessed_value,
                b.taxable_value,
                b.pre_pct,
                b.millage_rate,
                b.total_due,
                b.total_paid,
                b.balance_due,
                b.payment_status,
                b.due_date,
                b.paid_date,
                b.late_fees,
                b.interest_charges,
                p.payment_date,
                p.amount as payment_amount,
                p.payment_method
            FROM acc.property_tax_bill b
            LEFT JOIN acc.property_tax_payment p ON p.tax_bill_id = b.id
        """
    else:  # summary
        query = """
            SELECT 
                property_code,
                tax_year,
                tax_season,
                total_due,
                total_paid,
                balance_due,
                payment_status
            FROM acc.property_tax_bill
        """
    
    # Add filters
    conditions = []
    params = []
    
    if property_code:
        conditions.append("property_code = %s")
        params.append(property_code)
    
    if year:
        conditions.append("tax_year = %s")
        params.append(year)
    
    if conditions:
        # Handle LEFT JOIN case for detail report
        if 'LEFT JOIN' in query:
            query += " WHERE b." + " AND b.".join(conditions)
        else:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY tax_year DESC, property_code, tax_season"
    
    results = execute_query(query, tuple(params) if params else None)
    
    if not results:
        console.print("[yellow]No data found matching criteria[/yellow]")
        return
    
    # Generate default filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = f"_{property_code}" if property_code else ""
        output_file = f"tax_export_{report}{suffix}_{timestamp}.{output_format}"
    
    # Export based on format
    if output_format == 'csv':
        _export_csv(results, output_file)
    elif output_format == 'json':
        _export_json(results, output_file)
    elif output_format == 'pdf':
        _export_pdf(results, output_file, report)
    
    console.print(f"[green]✓ Data exported to {output_file}[/green]")

def _export_csv(results, output_file):
    """Export results to CSV"""
    if not results:
        return
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        for row in results:
            # Convert Decimal to float for CSV
            row_dict = {}
            for key, val in row.items():
                if isinstance(val, Decimal):
                    row_dict[key] = float(val)
                elif isinstance(val, datetime):
                    row_dict[key] = val.strftime('%Y-%m-%d')
                else:
                    row_dict[key] = val
            writer.writerow(row_dict)

def _export_json(results, output_file):
    """Export results to JSON"""
    # Convert Decimal and datetime to JSON-serializable types
    json_results = []
    for row in results:
        json_row = {}
        for key, val in row.items():
            if isinstance(val, Decimal):
                json_row[key] = float(val)
            elif isinstance(val, datetime):
                json_row[key] = val.strftime('%Y-%m-%d')
            else:
                json_row[key] = val
        json_results.append(json_row)
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)

def _export_pdf(results, output_file, report_type):
    """Export results to PDF (requires reportlab - not yet implemented)"""
    raise NotImplementedError(
        "PDF export requires reportlab library. "
        "Install with: pip install reportlab, or use CSV/JSON format instead."
    )
