"""
Invoice export command - generates invoices in multiple formats
"""
import click
from rich.console import Console
from copilot.db import execute_query
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path



def create_project_directories(client_code, project_code):
    """Create complete project directory structure"""
    PROJECT_BASE = "/mnt/sda1/01_bgm_projman/Active"
    PROJECT_FALLBACK = os.path.expanduser("~/bgm_projects/Active")
    
    base_dir = PROJECT_BASE if os.path.exists(PROJECT_BASE) else PROJECT_FALLBACK
    project_root = os.path.join(base_dir, client_code, project_code)
    
    subdirs = [
        '01_baseline',
        '02_invoices',
        '03_authorization',
        '04_subcontractors',
        '05_reports'
    ]
    
    for subdir in subdirs:
        dir_path = os.path.join(project_root, subdir)
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    return project_root

console = Console()

# Import format-specific libraries
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from jinja2 import Template
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False

@click.command('export')
@click.argument('invoice_code')
@click.option('--format', '-f', type=click.Choice(['xlsx', 'pdf', 'html', 'all']), 
              default='all', help='Export format')
@click.option('--output', '-o', help='Output directory (default: ~/bgs_invoices)')
@click.option('--open', 'open_file', is_flag=True, help='Open file after creation')
def export_invoice(invoice_code, format, output, open_file):
    """Export invoice to XLSX, PDF, or HTML format"""
    
    # Get invoice data
    invoice_data = get_invoice_data(invoice_code)
    if not invoice_data:
        console.print(f"[red]Invoice '{invoice_code}' not found[/red]")
        return
    
    # Set output directory
    if not output:
        output = os.path.expanduser("~/bgs_invoices")
    
    Path(output).mkdir(parents=True, exist_ok=True)
    
    # Generate requested format(s)
    files_created = []
    
    if format in ['xlsx', 'all']:
        if XLSX_AVAILABLE:
            xlsx_file = export_to_xlsx(invoice_data, output)
            if xlsx_file:
                files_created.append(xlsx_file)
                console.print(f"[green]✓ XLSX created:[/green] {xlsx_file}")
        else:
            console.print("[yellow]⚠ XLSX export requires openpyxl: pip install openpyxl[/yellow]")
    
    if format in ['pdf', 'all']:
        if PDF_AVAILABLE:
            pdf_file = export_to_pdf(invoice_data, output)
            if pdf_file:
                files_created.append(pdf_file)
                console.print(f"[green]✓ PDF created:[/green] {pdf_file}")
        else:
            console.print("[yellow]⚠ PDF export requires reportlab: pip install reportlab[/yellow]")
    
    if format in ['html', 'all']:
        if HTML_AVAILABLE:
            html_file = export_to_html(invoice_data, output)
            if html_file:
                files_created.append(html_file)
                console.print(f"[green]✓ HTML created:[/green] {html_file}")
        else:
            console.print("[yellow]⚠ HTML export requires jinja2: pip install jinja2[/yellow]")
    
    if not files_created:
        console.print("[red]No files were created[/red]")
        return
    
    console.print(f"\n[bold green]✓ Invoice exported successfully![/bold green]")
    console.print(f"[dim]Output directory: {output}[/dim]\n")
    
    # Open file if requested
    if open_file and files_created:
        import subprocess
        file_to_open = files_created[0]  # Open first file created
        console.print(f"Opening {file_to_open}...")
        subprocess.run(['xdg-open', file_to_open])

def get_invoice_data(invoice_code):
    """Fetch complete invoice data from database"""
    
    # Get invoice header
    invoice = execute_query("""
        SELECT
            i.*,
            p.project_name,
            p.project_desc,
            p.client_po,
            c.code as client_code,
            c.name as client_name,
            c.contact_name,
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
        return None
    
    inv = invoice[0]
    
    # Get timesheet line items (detail)
    timesheets = execute_query("""
        SELECT 
            t.ts_date,
            t.res_id,
            r.res_name,
            t.ts_units,
            t.task_no,
            t.sub_task_no,
            t.ts_desc,
            t.ts_mileage,
            t.ts_expense,
            b.base_rate,
            b.base_miles_rate
        FROM bgs.timesheet t
        -- Resource name not needed, using res_id
        LEFT JOIN bgs.baseline b ON 
            b.project_code = t.project_code AND
            b.task_no = t.task_no AND
            b.sub_task_no = t.sub_task_no AND
            b.res_id = t.res_id
        WHERE t.invoice_code = %s
        ORDER BY t.ts_date, t.task_no, t.sub_task_no
    """, (invoice_code,))
    
    # Calculate line totals
    labor_items = []
    total_hours = Decimal('0')
    total_labor = Decimal('0')
    total_mileage = Decimal('0')
    total_expenses = Decimal('0')
    
    for ts in timesheets:
        hours = Decimal(str(ts['ts_units']))
        rate = Decimal(str(ts['base_rate'] or 0))
        miles = Decimal(str(ts['ts_mileage'] or 0))
        mile_rate = Decimal(str(ts['base_miles_rate'] or 0))
        expense = Decimal(str(ts['ts_expense'] or 0))
        
        labor_amt = hours * rate
        mile_amt = miles * mile_rate
        
        total_hours += hours
        total_labor += labor_amt
        total_mileage += mile_amt
        total_expenses += expense
        
        labor_items.append({
            'date': ts['ts_date'],
            'resource': ts['res_name'] or ts['res_id'],
            'hours': hours,
            'rate': rate,
            'task': ts['task_no'],
            'total': labor_amt,
            'description': ts['ts_desc'],
            'miles': miles,
            'mile_rate': mile_rate,
            'mile_amt': mile_amt,
            'expense': expense
        })
    
    grand_total = total_labor + total_mileage + total_expenses
    
    return {
        'invoice': inv,
        'labor_items': labor_items,
        'totals': {
            'hours': total_hours,
            'labor': total_labor,
            'mileage': total_mileage,
            'expenses': total_expenses,
            'grand_total': grand_total
        }
    }

def export_to_xlsx(data, output_dir):
    """Export invoice to Excel/LibreOffice Calc format"""
    
    inv = data['invoice']
    items = data['labor_items']
    totals = data['totals']
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = f"Invoice {inv['invoice_number']:04d}"
    
    # Set column widths
    ws.column_dimensions['A'].width = 12  # Date
    ws.column_dimensions['B'].width = 20  # Resource
    ws.column_dimensions['C'].width = 8   # Units
    ws.column_dimensions['D'].width = 12  # Rate
    ws.column_dimensions['E'].width = 8   # Task
    ws.column_dimensions['F'].width = 12  # Total
    ws.column_dimensions['G'].width = 40  # Description
    
    # Define styles
    header_font = Font(bold=True, size=12)
    title_font = Font(bold=True, size=14)
    border_thin = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Header section
    row = 1
    ws[f'A{row}'] = "Invoice Report"
    ws[f'A{row}'].font = Font(bold=True, size=16)
    row += 1
    
    ws[f'A{row}'] = "Breen GeoScience Management, Inc."
    ws[f'A{row}'].font = header_font
    ws[f'F{row}'] = "Project"
    ws[f'F{row}'].font = header_font
    row += 1
    
    ws[f'A{row}'] = "Payment to:"
    ws[f'F{row}'] = inv['project_name']
    row += 1
    
    ws[f'A{row}'] = "Breen GeoScience Management, Inc."
    ws[f'F{row}'] = f"{inv['city']}, {inv['state']}" if inv['city'] else ""
    row += 1
    
    ws[f'A{row}'] = "PMB #354, 4234 I-75 Business Spur"
    ws[f'F{row}'] = "USA"
    row += 1
    
    ws[f'A{row}'] = "Sault Ste. Marie, Michigan USA 49783"
    row += 2
    
    ws[f'F{row}'] = f"Date: {inv['invoice_date'].strftime('%B %d, %Y')}"
    ws[f'F{row}'].font = header_font
    row += 1
    
    # Client section
    ws[f'A{row}'] = "Client"
    ws[f'A{row}'].font = header_font
    ws[f'F{row}'] = f"Desc. {inv['project_code']}"
    row += 1
    
    ws[f'A{row}'] = inv['client_name']
    ws[f'F{row}'] = f"PO#: {inv['client_po'] or 'NA'}"
    row += 1
    
    ws[f'A{row}'] = f"{inv['city']}, {inv['state']}" if inv['city'] else ""
    ws[f'F{row}'] = "A/R Net 30"
    row += 1
    
    ws[f'F{row}'] = f"Baseline: {inv['project_code']}"
    row += 1
    
    ws[f'A{row}'] = f"Attention: {inv['contact_name']}" if inv['contact_name'] else ""
    ws[f'F{row}'] = f"Invoice No. {inv['invoice_code']}"
    ws[f'F{row}'].font = header_font
    row += 1
    
    ws[f'A{row}'] = f"Project Description: {inv['project_desc']}" if inv['project_desc'] else ""
    row += 2
    
    # Labor section header
    ws[f'A{row}'] = "Labor"
    ws[f'A{row}'].font = Font(bold=True, size=12, underline='single')
    row += 2
    
    # Column headers
    headers = ['Date', 'Resource Name', 'Units', 'Unit Rate', 'Task', 'Total', 'Description']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.border = border_thin
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    row += 1
    
    # Labor line items
    for item in items:
        ws[f'A{row}'] = item['date'].strftime('%Y-%m-%d')
        ws[f'B{row}'] = item['resource']
        ws[f'C{row}'] = f"{item['hours']:.2f}"
        ws[f'D{row}'] = f"${item['rate']:.2f}"
        ws[f'E{row}'] = item['task']
        ws[f'F{row}'] = f"${item['total']:.2f}"
        ws[f'G{row}'] = item['description']
        
        # Apply borders
        for col in range(1, 8):
            ws.cell(row=row, column=col).border = border_thin
        
        row += 1
    
    row += 1
    
    # Totals
    ws[f'A{row}'] = "Total Hrs."
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'C{row}'] = f"{totals['hours']:.2f}"
    ws[f'E{row}'] = "Total Labor"
    ws[f'E{row}'].font = Font(bold=True)
    ws[f'F{row}'] = f"${totals['labor']:.2f}"
    ws[f'F{row}'].font = Font(bold=True)
    row += 2
    
    # Grand total
    ws[f'F{row}'] = f"${totals['grand_total']:.2f}"
    ws[f'F{row}'].font = Font(bold=True, size=14)
    
    # Save file
    filename = f"{inv['invoice_code']}.xlsx"
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    
    return filepath

def export_to_pdf(data, output_dir):
    """Export invoice to PDF format"""
    
    inv = data['invoice']
    items = data['labor_items']
    totals = data['totals']
    
    filename = f"{inv['invoice_code']}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#000000'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Title
    elements.append(Paragraph("Invoice Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Header table (2 columns)
    header_data = [
        [Paragraph("<b>Breen GeoScience Management, Inc.</b>", header_style),
         Paragraph("<b>Project</b>", header_style)],
        [Paragraph("Payment to:", header_style),
         Paragraph(inv['project_name'], header_style)],
        [Paragraph("Breen GeoScience Management, Inc.", header_style),
         Paragraph(f"{inv['city']}, {inv['state']}" if inv['city'] else "", header_style)],
        [Paragraph("PMB #354, 4234 I-75 Business Spur", header_style),
         Paragraph("USA", header_style)],
        [Paragraph("Sault Ste. Marie, Michigan USA 49783", header_style),
         Paragraph("", header_style)],
    ]
    
    header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Date and invoice info
    info_data = [
        ["", f"Date: {inv['invoice_date'].strftime('%B %d, %Y')}"],
        [f"Client", f"Desc. {inv['project_code']}"],
        [inv['client_name'], f"PO#: {inv['client_po'] or 'NA'}"],
        [f"{inv['city']}, {inv['state']}" if inv['city'] else "", "A/R Net 30"],
        ["", f"Baseline: {inv['project_code']}"],
        [f"Attention: {inv['contact_name']}" if inv['contact_name'] else "", 
         f"<b>Invoice No. {inv['invoice_code']}</b>"],
        [f"Project Description: {inv['project_desc']}" if inv['project_desc'] else "", ""],
    ]
    
    info_table = Table(info_data, colWidths=[4*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (1, 5), (1, 5), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Labor section
    elements.append(Paragraph("<b><u>Labor</u></b>", bold_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Labor table
    labor_data = [
        ['Date', 'Resource Name', 'Units', 'Unit Rate', 'Task', 'Total', 'Description']
    ]
    
    for item in items:
        labor_data.append([
            item['date'].strftime('%Y-%m-%d'),
            item['resource'],
            f"{item['hours']:.2f}",
            f"${item['rate']:.2f}",
            item['task'],
            f"${item['total']:.2f}",
            item['description'][:30]  # Truncate long descriptions
        ])
    
    labor_table = Table(labor_data, colWidths=[0.8*inch, 1.2*inch, 0.6*inch, 
                                               0.8*inch, 0.5*inch, 0.8*inch, 2.3*inch])
    labor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Units
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Rate
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),  # Total
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(labor_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Totals
    totals_data = [
        ['', '', '<b>Total Hrs.</b>', f"{totals['hours']:.2f}", 
         '<b>Total Labor</b>', f"<b>${totals['labor']:.2f}</b>", '']
    ]
    
    totals_table = Table(totals_data, colWidths=[0.8*inch, 1.2*inch, 0.6*inch, 
                                                  0.8*inch, 0.5*inch, 0.8*inch, 2.3*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
        ('ALIGN', (5, 0), (5, 0), 'RIGHT'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTNAME', (4, 0), (5, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Grand total
    grand_data = [['', '', '', '', '', f"<b>${totals['grand_total']:.2f}</b>", '']]
    grand_table = Table(grand_data, colWidths=[0.8*inch, 1.2*inch, 0.6*inch, 
                                                0.8*inch, 0.5*inch, 0.8*inch, 2.3*inch])
    grand_table.setStyle(TableStyle([
        ('ALIGN', (5, 0), (5, 0), 'RIGHT'),
        ('FONTNAME', (5, 0), (5, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (5, 0), (5, 0), 12),
    ]))
    elements.append(grand_table)
    
    # Build PDF
    doc.build(elements)
    
    return filepath

def export_to_html(data, output_dir):
    """Export invoice to HTML format"""
    
    inv = data['invoice']
    items = data['labor_items']
    totals = data['totals']
    
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice {{ invoice.invoice_code }}</title>
    <style>
        @page {
            size: letter;
            margin: 0.5in;
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            max-width: 8in;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .header-left, .header-right {
            width: 48%;
        }
        .title {
            text-align: center;
            font-size: 16pt;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .section-title {
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .company-name {
            font-weight: bold;
            font-size: 11pt;
        }
        .client-section {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .client-left, .client-right {
            width: 48%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #cccccc;
            border: 1px solid #666;
            padding: 8px;
            text-align: left;
            font-weight: bold;
        }
        td {
            border: 1px solid #666;
            padding: 6px;
        }
        .right-align {
            text-align: right;
        }
        .totals {
            margin-top: 15px;
            display: flex;
            justify-content: space-between;
            font-weight: bold;
        }
        .grand-total {
            text-align: right;
            font-size: 14pt;
            font-weight: bold;
            margin-top: 10px;
        }
        .bold {
            font-weight: bold;
        }
        .underline {
            text-decoration: underline;
        }
        @media print {
            body {
                margin: 0;
            }
        }
    </style>
</head>
<body>
    <div class="title">Invoice Report</div>
    
    <div class="header">
        <div class="header-left">
            <div class="company-name">Breen GeoScience Management, Inc.</div>
            <div>Payment to:</div>
            <div>Breen GeoScience Management, Inc.</div>
            <div>PMB #354, 4234 I-75 Business Spur</div>
            <div>Sault Ste. Marie, Michigan USA 49783</div>
        </div>
        <div class="header-right" style="text-align: right;">
            <div class="bold">Project</div>
            <div>{{ invoice.project_name }}</div>
            <div>{{ invoice.city }}, {{ invoice.state }}</div>
            <div>USA</div>
        </div>
    </div>
    
    <div class="client-section">
        <div class="client-left">
            <div class="bold">Client</div>
            <div>{{ invoice.client_name }}</div>
            <div>{{ invoice.city }}, {{ invoice.state }}</div>
            <div style="margin-top: 10px;">
                {% if invoice.contact_name %}
                Attention: {{ invoice.contact_name }}
                {% endif %}
            </div>
            <div>
                {% if invoice.project_desc %}
                Project Description: {{ invoice.project_desc }}
                {% endif %}
            </div>
        </div>
        <div class="client-right" style="text-align: right;">
            <div>Date: {{ invoice.invoice_date.strftime('%B %d, %Y') }}</div>
            <div>Desc. {{ invoice.project_code }}</div>
            <div>PO#: {{ invoice.client_po or 'NA' }}</div>
            <div>A/R Net 30</div>
            <div>Baseline: {{ invoice.project_code }}</div>
            <div class="bold">Invoice No. {{ invoice.invoice_code }}</div>
        </div>
    </div>
    
    <div class="section-title underline">Labor</div>
    
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Resource Name</th>
                <th class="right-align">Units</th>
                <th class="right-align">Unit Rate</th>
                <th>Task</th>
                <th class="right-align">Total</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.date.strftime('%Y-%m-%d') }}</td>
                <td>{{ item.resource }}</td>
                <td class="right-align">{{ "%.2f"|format(item.hours) }}</td>
                <td class="right-align">${{ "%.2f"|format(item.rate) }}</td>
                <td>{{ item.task }}</td>
                <td class="right-align">${{ "%.2f"|format(item.total) }}</td>
                <td>{{ item.description }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="totals">
        <div>
            <span class="bold">Total Hrs.</span> {{ "%.2f"|format(totals.hours) }}
        </div>
        <div>
            <span class="bold">Total Labor</span> ${{ "%.2f"|format(totals.labor) }}
        </div>
    </div>
    
    <div class="grand-total">
        ${{ "%.2f"|format(totals.grand_total) }}
    </div>
</body>
</html>
    """
    
    # Render template
    template = Template(html_template)
    html_content = template.render(
        invoice=inv,
        items=items,
        totals=totals
    )
    
    # Save file
    filename = f"{inv['invoice_code']}.html"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(html_content)
    
    return filepath

