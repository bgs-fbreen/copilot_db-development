"""
Project management commands for BGM Copilot
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from copilot.db import execute_query, get_connection
from datetime import datetime, date, timedelta
import os
from pathlib import Path
import xlsxwriter
import re

console = Console()

PROJECT_BASE_DIR = "/mnt/sda1/01_bgm_projman/Active"
PROJECT_FALLBACK_DIR = os.path.expanduser("~/bgm_projects/Active")

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def get_base_dir():
    if os.path.exists(PROJECT_BASE_DIR):
        return PROJECT_BASE_DIR
    else:
        console.print(f"[yellow]⚠ Mount not available: {PROJECT_BASE_DIR}[/yellow]")
        console.print(f"[yellow]  Using fallback: {PROJECT_FALLBACK_DIR}[/yellow]")
        return PROJECT_FALLBACK_DIR

def create_project_directories(client_code, project_code):
    base_dir = get_base_dir()
    project_root = os.path.join(base_dir, client_code, project_code)
    subdirs = [
        '01_baseline', '02_invoices', '03_authorization', '04_subcontractors', '05_reports'
    ]
    for subdir in subdirs:
        dir_path = os.path.join(project_root, subdir)
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    return project_root

@click.group()
def project():
    """Project management commands"""

@project.command('create-dirs')
@click.argument('project_code')
def create_dirs(project_code):
    """Create directory structure for existing project"""
    proj = execute_query("""
        SELECT p.project_code, p.project_name, p.client_code, c.name as client_name
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, (project_code,))
    if not proj:
        console.print(f"[red]Project '{project_code}' not found[/red]")
        return
    p = proj[0]
    console.print(f"\n[bold cyan]Create Directory Structure[/bold cyan]\n")
    console.print(f"[bold]Project:[/bold] {p['project_name']}")
    console.print(f"[bold]Client:[/bold] {p['client_name']}")
    console.print(f"[bold]Project Code:[/bold] {p['project_code']}\n")
    if not Confirm.ask("Create directories?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return
    try:
        project_root = create_project_directories(p['client_code'], p['project_code'])
        console.print(f"\n[bold green]✓ Directories created![/bold green]")
        console.print(f"[dim]Location: {project_root}[/dim]\n")
        console.print("Structure:")
        console.print(f"  {p['client_code']}/")
        console.print(f"    └── {p['project_code']}/")
        console.print(f"        ├── 01_baseline/")
        console.print(f"        ├── 02_invoices/")
        console.print(f"        ├── 03_authorization/")
        console.print(f"        ├── 04_subcontractors/")
        console.print(f"        └── 05_reports/\n")
    except Exception as e:
        console.print(f"[red]Error creating directories: {e}[/red]")

@project.command('list')
@click.option('--client', '-c', help='Filter by client code')
@click.option('--status', '-s', help='Filter by status', default='active')
def list_projects(client, status):
    """List projects"""
    where_clauses = []
    params = []
    if client:
        where_clauses.append("p.client_code = %s")
        params.append(client)
    if status:
        where_clauses.append("p.status = %s")
        params.append(status)
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    projects = execute_query(f"""
        SELECT 
            p.project_code, p.project_name, p.client_code, c.name as client_name,
            p.start_date, p.status
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        {where_sql}
        ORDER BY p.project_code DESC
    """, params if params else None)
    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Projects[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project Code", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Project Name", style="white")
    table.add_column("Start Date", style="yellow")
    table.add_column("Status")
    for p in projects:
        start = p['start_date'].strftime('%Y-%m-%d') if p['start_date'] else ""
        table.add_row(
            p['project_code'],
            p['client_code'],
            (p['project_name'] or '')[:50],
            start,
            p['status']
        )
    console.print(table)
    console.print()

# ---- create-baseline subcommand (copied in-module for ease, modularize if desired) ----

@project.command("create-baseline")
@click.argument("project_code", required=False)
def create_baseline(project_code):
    """
    Generate/re-generate the Baseline XLSX for the given project code.
    If no code specified, shows a list and prompts for entry.
    """
    COMPANY_NAME = "Breen GeoScience Management, Inc."
    COMPANY_ADDR1 = "PMB #354, 4234 I-75 Business Spur"
    COMPANY_ADDR2 = "Sault Ste. Marie, Michigan USA 49783"

    def sanitize(name):
        return re.sub(r'[^a-zA-Z0-9_]', '_', name.strip().replace(' ', '_'))[:32]
    def wrap(text, width):
        lines, line = [], []
        for word in text.split():
            if sum(len(w) for w in line) + len(word) + len(line) > width:
                lines.append(" ".join(line))
                line = []
            line.append(word)
        if line: lines.append(" ".join(line))
        return lines
    def make_description(sub_task_no, task_name, task_notes):
        desc = ""
        if sub_task_no and str(sub_task_no).strip().lower() != "na":
            desc = f"{sub_task_no}: {task_name or ''}".strip()
            if task_notes:
                desc = f"{desc} {task_notes}"
        else:
            if task_notes:
                desc = task_notes
        return desc.strip()

    conn = get_connection()
    cur = conn.cursor()
    if not project_code:
        cur.execute("SELECT project_code, project_name FROM bgs.project WHERE status = 'active' ORDER BY project_code")
        projects = cur.fetchall()
        print("\nExisting Projects:")
        for idx, (pcode, pname) in enumerate(projects, 1):
            print("  %2d) %s  %s" % (idx, pcode, pname))
        print()
        try:
            inp = input("Enter project code from the above list (or empty to abort): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
        if not inp:
            print("Aborted.")
            return
        project_code = inp
    cur.execute("""
        SELECT
            p.project_code, p.project_name, p.project_desc, p.client_po, p.status,
            p.project_city, p.project_state, p.project_country, c.code as client_code,
            c.name as client_name, c.address as client_addr, c.city as client_city,
            c.state as client_state, c.zip as client_zip, c.contact_name,
            p.project_year, p.project_number
        FROM bgs.project p
        JOIN bgs.client c ON p.client_code = c.code
        WHERE p.project_code = %s
    """, (project_code,))
    rec = cur.fetchone()
    if not rec:
        print(f"Project '{project_code}' not found. Please run again and select a valid code.")
        return
    (
        project_code, project_name, project_desc, project_po, proj_status,
        project_city, project_state, project_country, client_code,
        client_name, client_addr, client_city, client_state, client_zip, contact_name,
        project_year, project_number
    ) = rec
    abbr = sanitize(project_name if project_name else project_code)
    proj_dir = os.path.join(PROJECT_BASE_DIR, client_code, f"{project_code}_{abbr}")
    os.makedirs(proj_dir, exist_ok=True)
    for sub in ['01_baseline', '02_invoices', '03_authorization', '04_subcontractors', '05_reports']:
        os.makedirs(os.path.join(proj_dir, sub), exist_ok=True)
    cur2 = conn.cursor()
    cur2.execute("""
        SELECT
            b.task_no, t.task_name, b.res_id, b.base_units, b.base_rate,
            b.base_expense, b.is_lump_sum,
            COALESCE(NULLIF(b.base_units * b.base_rate, 0), NULLIF(b.base_expense, 0), 0) as real_total,
            b.base_expense, b.base_miles, b.base_miles_rate, b.sub_task_no, t.task_notes
        FROM bgs.baseline b
        LEFT JOIN bgs.task t ON t.project_code = b.project_code AND t.task_no = b.task_no AND t.sub_task_no = b.sub_task_no
        WHERE b.project_code = %s
        ORDER BY b.task_no, b.sub_task_no, b.res_id
    """, (project_code,))
    baseline_rows = cur2.fetchall()
    tasks = dict()
    for row in baseline_rows:
        (
            task_no, task_name, res_id, base_units, base_rate, base_expense, is_lump_sum, real_total,
            base_expense2, base_miles, base_miles_rate, sub_task_no, task_notes
        ) = row
        key = (task_no, task_name)
        desc = make_description(sub_task_no, task_name, task_notes)
        if key not in tasks:
            tasks[key] = []
        tasks[key].append({
            "resource": res_id,
            "base_units": base_units,
            "base_rate": base_rate,
            "base_expense": base_expense,
            "is_lump_sum": is_lump_sum,
            "total": real_total,
            "desc": desc
        })
    cur2.close()
    today_str = datetime.now().strftime("%m/%d/%y")
    baseline_xlsx = os.path.join(proj_dir, "01_baseline", f"{project_code}_baseline.xlsx")
    wb = xlsxwriter.Workbook(baseline_xlsx)
    ws = wb.add_worksheet("Baseline")
    bold = wb.add_format({'bold': True})
    titlebold = wb.add_format({'bold': True, 'font_size': 14})
    bigbold = wb.add_format({'bold': True, 'font_size': 12})
    money = wb.add_format({'num_format': '$#,##0.00'})
    headbg = wb.add_format({'bg_color': '#DDDDDD', 'align': 'center', 'bold': True, 'font_size': 11})
    headleft = wb.add_format({'bg_color': '#DDDDDD', 'align': 'left', 'bold': True, 'font_size': 11})
    left = wb.add_format({'align': 'left'})
    right_bold = wb.add_format({'align': 'right', 'bold': True})
    center = wb.add_format({'align': 'center', 'font_size': 9})
    total_label_fmt = wb.add_format({'bold': True, 'align': 'right'})
    total_val_fmt = wb.add_format({'bold': True, 'num_format': '$#,##0.00', 'align': 'right', 'top': 1})
    pagegray = wb.add_format({'font_color':'#888888'})
    desc_fmt = wb.add_format({'font_size': 9, 'text_wrap': True, 'align': 'left'})
    cell = wb.add_format({'font_size': 9})
    ws.set_column('A:A', 18)
    ws.set_column('B:B', 11)
    ws.set_column('C:C', 11)
    ws.set_column('D:D', 12)
    ws.set_column('E:E', 15)
    ws.set_column('F:F', 45)
    row = 0
    ws.merge_range(row, 0, row, 5, "Baseline Costs", titlebold)
    row += 2
    ws.write(row, 0, COMPANY_NAME, bigbold)
    ws.write(row, 4, project_name or "", left)
    row += 1
    ws.write(row, 0, COMPANY_NAME)
    ws.write(row, 4, project_city or "", left)
    row += 1
    ws.write(row, 0, COMPANY_ADDR1)
    ws.write(row, 4, project_state or "", left)
    row += 1
    ws.write(row, 0, COMPANY_ADDR2)
    ws.write(row, 4, project_country or "", left)
    row += 2
    ws.write(row, 4, "Date: " + today_str, left)
    row += 1
    ws.write(row, 0, "Client", bold)
    ws.write(row, 4, f"BGM # {project_code}", left)
    row += 1
    ws.write(row, 0, client_name or "")
    ws.write(row, 4, "A/R 45 days", left)
    row += 1
    addr_lines = wrap(client_addr or "", 35)
    city_line = f"{client_city or ''}, {client_state or ''} {client_zip or ''}".strip(", ")
    addr_lines.append(city_line)
    addr_lines.append("USA")
    for aline in addr_lines:
        ws.write(row, 0, aline)
        row += 1
    ws.write(row, 0, f"Attention: {contact_name or ''}")
    row += 1
    ws.write(row, 0, f"Project Description: {project_desc or ''}")
    row += 2
    all_line_row_ranges = []
    for (task_no, task_name), lines in tasks.items():
        task_header = f"{task_no}: {task_name or ''}"
        ws.write(row, 0, task_header, bigbold)
        row += 2
        ws.write(row, 0, "Resource Name", headbg)
        ws.write(row, 1, "Unit Rate", headbg)
        ws.write(row, 2, "Units", headbg)
        ws.write(row, 3, "Expense", headbg)
        ws.write(row, 4, "Total", headbg)
        ws.write(row, 5, "Description", headleft)
        row += 1
        section_first = row
        section_last = row + len(lines) - 1
        for entry in lines:
            ws.write(row, 0, entry["resource"], cell)
            if entry["is_lump_sum"]:
                ws.write(row, 1, "", cell)
                ws.write(row, 2, "", center)
                ws.write(row, 3, "", cell)
                ws.write(row, 4, entry["total"], money if entry["total"] else cell)
            else:
                ws.write(row, 1, entry["base_rate"] if entry["base_rate"] else "", money if entry["base_rate"] else cell)
                ws.write(row, 2, entry["base_units"] if entry["base_units"] else "", center)
                ws.write(row, 3, entry["base_expense"] if entry["base_expense"] else "", money if entry["base_expense"] else cell)
                ws.write(row, 4, entry["total"] if entry["total"] else "", money if entry["total"] else cell)
            ws.write(row, 5, entry["desc"] or "", desc_fmt)
            row += 1
        if section_last >= section_first:
            all_line_row_ranges.append((section_first+1, section_last+1))
            subtotal_formula = f"=SUM(E{section_first+1}:E{section_last+1})"
            ws.write(row, 3, "Task Subtotal :", right_bold)
            ws.write_formula(row, 4, subtotal_formula, total_val_fmt)
            row += 2
    if all_line_row_ranges:
        sum_formula = '=SUM(' + ','.join(
            f'E{start}:E{end}' if start != end else f'E{start}' for start, end in all_line_row_ranges
        ) + ')'
        ws.write(row, 3, "Baseline Total :", total_label_fmt)
        ws.write_formula(row, 4, sum_formula, total_val_fmt)
        row += 2
    else:
        ws.write(row, 3, "Baseline Total :", total_label_fmt)
        ws.write(row, 4, 0, total_val_fmt)
        row += 2
    ws.write(row, 0, today_str, pagegray)
    ws.write(row, 5, "Page 1 of 1", pagegray)
    wb.close()
    print(f"Generated: {baseline_xlsx}")
    cur.close()
    conn.close()


@project.command('delete')
@click.argument('project_code', required=False)
@click.option('--yes', is_flag=True, help='Confirm deletion without prompting')
def delete_project(project_code, yes):
    """
    Delete a project and all related data from the database (tasks, baseline, timesheet, etc).
    This will NOT delete anything from the resources table.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        # If no project_code, list active ones and prompt for selection
        if not project_code:
            cur.execute("SELECT project_code, project_name FROM bgs.project WHERE status = 'active' ORDER BY project_code")
            projects = cur.fetchall()
            print("\nActive Projects:")
            for idx, (pcode, pname) in enumerate(projects, 1):
                print("  %2d) %s  %s" % (idx, pcode, pname))
            print()
            try:
                inp = input("Enter project code from the above list (or empty to abort): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\\nAborted.")
            if not inp:
                print("Aborted.")
                return
            project_code = inp

        if not yes:
            ans = input(f"Are you sure you want to delete project '{project_code}' and ALL related data? This CANNOT be undone! Type 'YES' to confirm: ")
            if ans.strip() != "YES":
                print("Aborted.")
                return

        delete_sql = [
            "DELETE FROM bgs.timesheet WHERE project_code = %s",
            "DELETE FROM bgs.baseline WHERE project_code = %s",
            "DELETE FROM bgs.task WHERE project_code = %s",
            "DELETE FROM bgs.project WHERE project_code = %s"
        ]
        for sql in delete_sql:
            cur.execute(sql, (project_code,))
        conn.commit()
        print(f"Project {project_code} and all related records deleted successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error deleting project: {e}")


def show_project_list_for_actual():
    """Display list of active projects and return selected project code"""
    projects = execute_query("""
        SELECT 
            p.project_code,
            p.client_code,
            p.project_name
        FROM bgs.project p
        WHERE p.status = 'active'
        ORDER BY p.project_code
    """)
    
    if not projects:
        console.print("[yellow]No active projects found[/yellow]")
        return None
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Client", style="cyan")
    table.add_column("Project Name", style="white")
    table.add_column("Project Code", style="yellow")
    
    for proj in projects:
        table.add_row(
            proj['client_code'],
            (proj['project_name'] or '')[:28],
            proj['project_code']
        )
    
    console.print(table)
    console.print()
    
    project_code = Prompt.ask("[yellow]Project Code[/yellow]")
    return project_code if project_code else None


def show_project_actual(project_code):
    """Display baseline vs actual for a specific project"""
    
    # Get project info
    project_info = execute_query("""
        SELECT 
            p.project_code, 
            p.project_name, 
            p.client_code,
            c.name as client_name,
            p.client_po,
            p.project_desc
        FROM bgs.project p
        JOIN bgs.client c ON c.code = p.client_code
        WHERE p.project_code = %s
    """, [project_code])
    
    if not project_info:
        console.print(f"[red]Project '{project_code}' not found[/red]")
        return
    
    proj = project_info[0]
    
    # Display header
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Project Actual Report[/bold cyan]")
    console.print(f"[bold cyan]   {project_code}[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"[bold]Project:[/bold]     {proj['project_name']}")
    console.print(f"[bold]Client:[/bold]      {proj['client_name']} ({proj['client_code']})")
    if proj['client_po']:
        console.print(f"[bold]Job No.:[/bold]     {proj['client_po']}")
    if proj['project_desc']:
        console.print(f"[bold]Description:[/bold] {proj['project_desc'][:60]}")
    
    # Get baseline vs actual by task
    actual_data = execute_query("""
        WITH baseline_totals AS (
            SELECT 
                b.task_no,
                b.sub_task_no,
                SUM(COALESCE(b.base_units, 0) * COALESCE(b.base_rate, 0) 
                  + COALESCE(b.base_miles, 0) * COALESCE(b.base_miles_rate, 0) 
                  + COALESCE(b.base_expense, 0)) as baseline
            FROM bgs.baseline b
            WHERE b.project_code = %s
            GROUP BY b.task_no, b.sub_task_no
        ),
        actual_totals AS (
            SELECT 
                ts.task_no,
                ts.sub_task_no,
                SUM(COALESCE(ts.ts_units, 0) * COALESCE(bl.base_rate, 0) 
                  + COALESCE(ts.ts_mileage, 0) * COALESCE(bl.base_miles_rate, 0) 
                  + COALESCE(ts.ts_expense, 0)) as actual
            FROM bgs.timesheet ts
            LEFT JOIN bgs.baseline bl ON bl.project_code = ts.project_code 
                AND bl.task_no = ts.task_no 
                AND bl.sub_task_no = ts.sub_task_no 
                AND bl.res_id = ts.res_id
            WHERE ts.project_code = %s
            GROUP BY ts.task_no, ts.sub_task_no
        )
        SELECT 
            COALESCE(b.task_no, a.task_no) as task_no,
            COALESCE(b.sub_task_no, a.sub_task_no) as sub_task_no,
            COALESCE(t.task_name, '') as task_name,
            COALESCE(b.baseline, 0) as baseline,
            COALESCE(a.actual, 0) as actual,
            COALESCE(b.baseline, 0) - COALESCE(a.actual, 0) as remaining
        FROM baseline_totals b
        FULL OUTER JOIN actual_totals a ON b.task_no = a.task_no AND b.sub_task_no = a.sub_task_no
        LEFT JOIN bgs.task t ON t.project_code = %s 
            AND t.task_no = COALESCE(b.task_no, a.task_no) 
            AND t.sub_task_no = COALESCE(b.sub_task_no, a.sub_task_no)
        ORDER BY COALESCE(b.task_no, a.task_no), COALESCE(b.sub_task_no, a.sub_task_no)
    """, [project_code, project_code, project_code])
    
    if not actual_data:
        console.print(f"\n[yellow]No data found for project '{project_code}'[/yellow]")
        return
    
    # Display table header
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Baseline vs Actual by Task[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    # Build table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task", style="cyan")
    table.add_column("Sub", style="cyan")
    table.add_column("Task Name", style="white")
    table.add_column("Baseline", justify="right", style="white")
    table.add_column("Actual", justify="right", style="yellow")
    table.add_column("Remaining", justify="right")
    
    total_baseline = 0
    total_actual = 0
    
    for row in actual_data:
        baseline = float(row['baseline'] or 0)
        actual = float(row['actual'] or 0)
        remaining = float(row['remaining'] or 0)
        
        total_baseline += baseline
        total_actual += actual
        
        remaining_color = "green" if remaining >= 0 else "red"
        
        table.add_row(
            row['task_no'],
            row['sub_task_no'],
            (row['task_name'] or '')[:24],
            f"${baseline:,.0f}",
            f"${actual:,.0f}",
            f"[{remaining_color}]${remaining:,.0f}[/{remaining_color}]"
        )
    
    console.print(table)
    
    # Display totals
    total_remaining = total_baseline - total_actual
    budget_used_pct = (total_actual / total_baseline * 100) if total_baseline > 0 else 0
    
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]   Project Totals[/bold cyan]")
    console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print(f"   Total Baseline:     ${total_baseline:>12,.2f}")
    console.print(f"   Total Actual:       ${total_actual:>12,.2f}")
    
    remaining_color = "green" if total_remaining >= 0 else "red"
    console.print(f"   [{remaining_color}]Remaining:          ${total_remaining:>12,.2f}[/{remaining_color}]")
    
    pct_color = "green" if budget_used_pct <= 100 else "red"
    console.print(f"   [{pct_color}]Budget Used:         {budget_used_pct:>12.1f}%[/{pct_color}]")
    
    console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    # Get invoices for this project
    invoices = execute_query("""
        SELECT 
            i.invoice_code,
            i.invoice_number,
            i.invoice_date,
            i.due_date,
            i.amount,
            i.paid_amount,
            i.status,
            i.payment_date
        FROM bgs.invoice i
        WHERE i.project_code = %s
        ORDER BY i.invoice_number
    """, [project_code])
    
    if invoices:
        today = date.today()
        
        console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        console.print(f"[bold cyan]   Invoice Status[/bold cyan]")
        console.print(f"[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
        
        inv_table = Table(show_header=True, header_style="bold magenta")
        inv_table.add_column("Inv#", style="cyan")
        inv_table.add_column("Invoice Date", style="white")
        inv_table.add_column("Due Date", style="white")
        inv_table.add_column("Amount", justify="right")
        inv_table.add_column("Paid", justify="right", style="green")
        inv_table.add_column("Balance", justify="right")
        inv_table.add_column("Status", justify="center")
        inv_table.add_column("Days", justify="right")
        
        total_invoiced = 0
        total_paid = 0
        
        for inv in invoices:
            invoice_date = inv['invoice_date']
            # Skip invoice if it has no invoice_date
            if not invoice_date:
                continue
            
            amount = float(inv['amount'] or 0)
            paid = float(inv['paid_amount'] or 0)
            balance = amount - paid
            total_invoiced += amount
            total_paid += paid
                
            due_date = inv['due_date'] or (invoice_date + timedelta(days=30))
            
            # Determine status and color
            status = inv['status'] or 'draft'
            
            # Safely convert invoice_number to int
            try:
                invoice_number = int(inv['invoice_number']) if inv['invoice_number'] else 0
            except (ValueError, TypeError):
                invoice_number = 0
            
            if status == 'paid':
                status_color = "green"
                days_str = "-"
            else:
                days_outstanding = (today - invoice_date).days
                days_str = str(days_outstanding)
                
                # Check if overdue
                if today > due_date and status != 'paid':
                    status = "overdue"
                    status_color = "red"
                elif status == 'pending':
                    status_color = "yellow"
                else:
                    status_color = "dim"
                
                # Color code days
                if days_outstanding > 90:
                    days_str = f"[red]{days_outstanding}[/red]"
                elif days_outstanding > 60:
                    days_str = f"[bright_yellow]{days_outstanding}[/bright_yellow]"
                elif days_outstanding > 30:
                    days_str = f"[yellow]{days_outstanding}[/yellow]"
            
            # Balance color
            balance_color = "white" if balance == 0 else "yellow"
            
            inv_table.add_row(
                f"{invoice_number:04d}",
                invoice_date.strftime('%Y-%m-%d'),
                due_date.strftime('%Y-%m-%d'),
                f"${amount:,.2f}",
                f"${paid:,.2f}",
                f"[{balance_color}]${balance:,.2f}[/{balance_color}]",
                f"[{status_color}]{status}[/{status_color}]",
                days_str
            )
        
        console.print(inv_table)
        
        total_outstanding = total_invoiced - total_paid
        outstanding_color = "green" if total_outstanding == 0 else "yellow"
        
        console.print(f"\n   Total Invoiced:     ${total_invoiced:>12,.2f}")
        console.print(f"   Total Paid:         ${total_paid:>12,.2f}")
        console.print(f"   [{outstanding_color}]Total Outstanding:  ${total_outstanding:>12,.2f}[/{outstanding_color}]")
        
        console.print(f"\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    else:
        console.print(f"[dim]No invoices found for this project.[/dim]\n")


@project.command('actual')
@click.argument('project_code', required=False)
def actual(project_code):
    """Display project baseline vs actual spending"""
    clear_screen()
    
    if not project_code:
        # Interactive mode
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   Select Project (Ctrl-C to exit)[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        project_code = show_project_list_for_actual()
        if not project_code:
            return
        
        clear_screen()
    
    show_project_actual(project_code)

