"""
Baseline report export command - generates baseline cost report in PDF format
"""
import click
from rich.console import Console
from copilot.db import execute_query
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path

console = Console()

# Project base directory
PROJECT_BASE_DIR = "/mnt/sda1/01_bgm_projman/Active"
PROJECT_FALLBACK_DIR = os.path.expanduser("~/bgm_projects/Active")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

def get_base_dir():
    """Get base project directory"""
    if os.path.exists(PROJECT_BASE_DIR):
        return PROJECT_BASE_DIR
    else:
        return PROJECT_FALLBACK_DIR

def create_project_directories(client_code, project_code, project_name=None):
    """Create complete project directory structure"""
    from copilot.utils import get_project_directory_name
    base_dir = get_base_dir()
    dir_name = get_project_directory_name(project_code, project_name)
    project_root = os.path.join(base_dir, client_code, dir_name)
    
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

@click.command('baseline')
@click.argument('project_code')
@click.option('--output', '-o', help='Output directory (default: project 01_baseline folder)')
@click.option('--open', 'open_file', is_flag=True, help='Open file after creation')
def export_baseline(project_code, output, open_file):
    """Export baseline cost report for project"""
    
    if not PDF_AVAILABLE:
        console.print("[red]PDF export requires reportlab: pip install reportlab[/red]")
        return
    
    # Get baseline data
    baseline_data = get_baseline_data(project_code)
    if not baseline_data:
        console.print(f"[red]Project '{project_code}' not found or has no baseline[/red]")
        return
    
    proj = baseline_data['project']
    
    # Determine output directory
    if not output:
        # Create all project directories
        create_project_directories(proj['client_code'], proj['project_code'], proj['project_name'])
        base_dir = get_base_dir()
        from copilot.utils import get_project_directory_name
        dir_name = get_project_directory_name(proj['project_code'], proj['project_name'])
        output = os.path.join(base_dir, proj['client_code'], dir_name, '01_baseline')
    
    # Generate PDF
    pdf_file = export_baseline_pdf(baseline_data, output)
    
    if pdf_file:
        console.print(f"\n[bold green]✓ Baseline report created![/bold green]")
        console.print(f"[dim]Location: {pdf_file}[/dim]\n")
        
        if open_file:
            import subprocess
            subprocess.run(['xdg-open', pdf_file])

def get_baseline_data(project_code):
    """Fetch baseline data from database"""
    
    # Get project info
    project = execute_query("""
        SELECT
            p.project_code,
            p.project_name,
            p.project_desc,
            p.client_po,
            p.start_date,
            c.code as client_code,
            c.name as client_name,
            c.contact_name,
            c.street_address,
            c.city,
            c.state,
            c.zip
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, (project_code,))
    
    if not project:
        return None
    
    proj = project[0]
    
    # Get baseline entries - USE res_id ONLY, no join to resource table
    baseline = execute_query("""
        SELECT
            b.task_no,
            b.sub_task_no,
            t.task_name,
            b.res_id,
            b.base_units,
            b.base_rate,
            b.base_miles,
            b.base_miles_rate,
            b.base_expense,
            (COALESCE(b.base_units, 0) * COALESCE(b.base_rate, 0) +
             COALESCE(b.base_miles, 0) * COALESCE(b.base_miles_rate, 0) +
             COALESCE(b.base_expense, 0)) as total
        FROM bgs.baseline b
        LEFT JOIN bgs.task t ON 
            t.project_code = b.project_code AND
            t.task_no = b.task_no AND
            t.sub_task_no = b.sub_task_no
        WHERE b.project_code = %s
        ORDER BY b.task_no, b.sub_task_no, b.res_id
    """, (project_code,))
    
    # Group by task
    tasks = {}
    grand_total = Decimal('0')
    
    for row in baseline:
        task_key = f"{row['task_no']}"
        task_name = row['task_name'] or "Consulting"
        
        if task_key not in tasks:
            tasks[task_key] = {
                'task_no': row['task_no'],
                'task_name': task_name,
                'resources': [],
                'subtotal': Decimal('0')
            }
        
        # Use res_id directly (e.g., "F.Breen")
        resource_display = row['res_id']
        expense = Decimal(str(row['base_expense'] or 0))
        total = Decimal(str(row['total'] or 0))
        
        tasks[task_key]['resources'].append({
            'resource': resource_display,
            'units': row['base_units'],
            'rate': row['base_rate'],
            'expense': expense,
            'total': total,
            'description': task_name
        })
        
        tasks[task_key]['subtotal'] += total
        grand_total += total
    
    return {
        'project': proj,
        'tasks': tasks,
        'grand_total': grand_total
    }

def export_baseline_pdf(data, output_dir):
    """Export baseline to PDF format - NO HTML CODES"""
    
    proj = data['project']
    tasks = data['tasks']
    grand_total = data['grand_total']
    
    filename = f"baseline_{proj['project_code']}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles - NO HTML
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
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
    elements.append(Paragraph("Baseline Costs", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Header table - plain text only
    project_location = f"{proj['city']}, {proj['state']}" if proj['city'] else "USA"
    
    header_data = [
        ["Breen GeoScience Management, Inc.", "Project"],
        ["", proj['project_name'] or proj['project_code']],
        ["Breen GeoScience Management, Inc.", project_location],
        ["PMB #354, 4234 I-75 Business Spur", "USA"],
        ["Sault Ste. Marie, Michigan USA 49783", ""],
    ]
    
    header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Client and project info - plain text
    today = datetime.now()
    client_address = proj['street_address'] if proj['street_address'] else ""
    client_location = f"{proj['city']}, {proj['state']} {proj['zip'] or ''}" if proj['city'] else ""
    contact_line = f"Attention: {proj['contact_name']}" if proj['contact_name'] else ""
    project_desc = f"Project Description: {proj['project_desc']}" if proj['project_desc'] else ""
    
    info_data = [
        ["", f"Date: {today.strftime('%m/%d/%y')}"],
        ["Client", f"BGM # {proj['project_code']}"],
        [proj['client_name'], "A/R 45 days"],
        [client_address, ""],
        [client_location, ""],
        ["USA", ""],
        [contact_line, ""],
        [project_desc, ""],
    ]
    
    info_table = Table(info_data, colWidths=[4*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Baseline items by task
    running_subtotal = Decimal('0')
    
    for task_key in sorted(tasks.keys()):
        task = tasks[task_key]
        
        # Task header - plain text
        task_header = Table([[f"{task['task_no']}: {task['task_name']}"]], colWidths=[7*inch])
        task_header.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
        ]))
        elements.append(task_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Resource table - plain text
        resource_data = [
            ['Resource\nName', 'Units', 'Unit\nRate', 'Expense', 'Total', 'Description']
        ]
        
        for res in task['resources']:
            units_str = f"{res['units']:.2f}" if res['units'] else ""
            rate_str = f"${res['rate']:.2f}" if res['rate'] else ""
            expense_str = f"${res['expense']:,.2f}" if res['expense'] > 0 else ""
            
            resource_data.append([
                res['resource'],  # This is now res_id like "F.Breen"
                units_str,
                rate_str,
                expense_str,
                f"${res['total']:,.2f}",
                res['description'][:40]
            ])
        
        resource_table = Table(resource_data, colWidths=[1.2*inch, 0.6*inch, 0.7*inch,
                                                         1.0*inch, 1.0*inch, 2.5*inch])
        resource_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(resource_table)
        elements.append(Spacer(1, 0.2*inch))
        
        running_subtotal += task['subtotal']
    
    # Subtotal - plain text
    subtotal_data = [
        ['', '', '', 'Labor / Material / Expense Sub Total :',
         f"${running_subtotal:,.2f}", '']
    ]
    
    subtotal_table = Table(subtotal_data, colWidths=[1.2*inch, 0.6*inch, 0.7*inch,
                                                      1.0*inch, 1.0*inch, 2.5*inch])
    subtotal_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (4, 0), 'RIGHT'),
        ('FONTNAME', (3, 0), (4, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(subtotal_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Grand total - plain text
    grand_data = [
        ['', '', '', 'Baseline Total :',
         f"${grand_total:,.2f}", '']
    ]
    
    grand_table = Table(grand_data, colWidths=[1.2*inch, 0.6*inch, 0.7*inch,
                                                1.0*inch, 1.0*inch, 2.5*inch])
    grand_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (4, 0), 'RIGHT'),
        ('FONTNAME', (3, 0), (4, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (3, 0), (4, 0), 12),
    ]))
    elements.append(grand_table)
    
    # Footer - plain text
    elements.append(Spacer(1, 0.5*inch))
    footer_data = [
        [f"{today.strftime('%m/%d/%Y')}", "", "Page 1 of 1"]
    ]
    footer_table = Table(footer_data, colWidths=[2*inch, 3*inch, 2*inch])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    
    return filepath

