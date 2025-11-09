#!/usr/bin/env python3
import os
import re
import psycopg2
import xlsxwriter
from datetime import datetime

COMPANY_NAME = "Breen GeoScience Management, Inc."
COMPANY_ADDR1 = "PMB #354, 4234 I-75 Business Spur"
COMPANY_ADDR2 = "Sault Ste. Marie, Michigan USA 49783"

PARENT = "/mnt/sda1/01_bgm_projman/Active/"
SUBFOLDERS = [
    "01_baseline",
    "02_invoices",
    "03_authorization",
    "04_subcontractors",
    "05_reports",
]

DB_HOST = "192.168.30.180"
DB_NAME = "copilot_db"
DB_USER = "frank"
DB_PASS = "basalt63"

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

def main():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.project_code,
            p.project_name,
            p.project_desc,
            p.client_po,
            p.status,
            p.project_city,
            p.project_state,
            p.project_country,
            c.code as client_code,
            c.name as client_name,
            c.address as client_addr,
            c.city as client_city,
            c.state as client_state,
            c.zip as client_zip,
            c.contact_name,
            p.project_year,
            p.project_number
        FROM bgs.project p
        JOIN bgs.client c ON p.client_code = c.code
        WHERE p.status = 'active'
    """)
    projects = cur.fetchall()

    for rec in projects:
        (project_code, project_name, project_desc, project_po, proj_status,
         project_city, project_state, project_country, client_code,
         client_name, client_addr, client_city, client_state, client_zip, contact_name,
         project_year, project_number) = rec

        abbr = sanitize(project_name if project_name else project_code)
        proj_dir = os.path.join(PARENT, client_code, f"{project_code}_{abbr}")
        os.makedirs(proj_dir, exist_ok=True)
        for sub in SUBFOLDERS:
            os.makedirs(os.path.join(proj_dir, sub), exist_ok=True)

        cur2 = conn.cursor()
        cur2.execute("""
            SELECT
                b.task_no,
                t.task_name,
                b.res_id,
                b.base_units,
                b.base_rate,
                b.base_expense,
                b.is_lump_sum,
                COALESCE(NULLIF(b.base_units * b.base_rate, 0), NULLIF(b.base_expense, 0), 0) as real_total,
                b.base_expense,
                b.base_miles,
                b.base_miles_rate,
                b.sub_task_no,
                t.task_notes
            FROM bgs.baseline b
            LEFT JOIN bgs.task t ON t.project_code = b.project_code AND t.task_no = b.task_no AND t.sub_task_no = b.sub_task_no
            WHERE b.project_code = %s
            ORDER BY b.task_no, b.sub_task_no, b.res_id
        """, (project_code,))
        baseline_rows = cur2.fetchall()

        tasks = dict()
        for row in baseline_rows:
            (task_no, task_name, res_id, base_units, base_rate, base_expense, is_lump_sum, real_total,
             base_expense2, base_miles, base_miles_rate, sub_task_no, task_notes) = row
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

        # FORMATS
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
        cell = wb.add_format({'font_size': 9})  # plain, generic

        ws.set_column('A:A', 18)
        ws.set_column('B:B', 11)
        ws.set_column('C:C', 11)
        ws.set_column('D:D', 12)
        ws.set_column('E:E', 15)
        ws.set_column('F:F', 45)

        row = 0

        # HEADER, COMPANY/PROJECT
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

        # Data tables
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

            # Record line item range for Baseline Total formula (using Excel 1-based row indices)
            if section_last >= section_first:
                all_line_row_ranges.append((section_first+1, section_last+1))
                subtotal_formula = f"=SUM(E{section_first+1}:E{section_last+1})"
                ws.write(row, 3, "Task Subtotal :", right_bold)
                ws.write_formula(row, 4, subtotal_formula, total_val_fmt)
                row += 2

        # Write Baseline Total: only sum line item rows, never subtotal rows
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
    print("All folders and correctly formatted baseline files created.")

if __name__ == "__main__":
    main()
    
    
