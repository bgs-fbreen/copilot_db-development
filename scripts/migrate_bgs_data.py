#!/usr/bin/env python3
"""
Migrate BGS data from db_accounts_old to copilot_db
"""
import psycopg2
from psycopg2.extras import execute_batch
import os
from dotenv import load_dotenv

load_dotenv()

# Database connections
OLD_DB = {
    'host': os.getenv('OLD_DB_HOST'),
    'port': os.getenv('OLD_DB_PORT', 5432),
    'database': os.getenv('OLD_DB_NAME'),
    'user': os.getenv('OLD_DB_USER'),
    'password': os.getenv('OLD_DB_PASSWORD')
}

NEW_DB = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def migrate_clients():
    """Extract unique clients from projects"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating CLIENTS...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("SELECT DISTINCT fk_client FROM bgs.tbl_project WHERE fk_client IS NOT NULL ORDER BY fk_client")
        clients = [(row[0], row[0], 'active') for row in old_cur.fetchall()]
        
        execute_batch(new_cur, 
            "INSERT INTO bgs.client (code, name, status) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING",
            clients)
        new_conn.commit()
        print(f"  ✓ Migrated {len(clients)} clients")
    
    old_conn.close()
    new_conn.close()

def migrate_resources():
    """Migrate resources table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating RESOURCES...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT pk_res_id, res_name, res_contact, res_street01, res_street02,
                   res_city, res_state, res_zip, res_phone01, res_phone02,
                   res_email, res_website
            FROM bgs.tbl_res
        """)
        resources = old_cur.fetchall()
        
        execute_batch(new_cur, """
            INSERT INTO bgs.resource 
            (res_id, res_name, res_contact, res_street01, res_street02,
             res_city, res_state, res_zip, res_phone01, res_phone02,
             res_email, res_website, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            ON CONFLICT (res_id) DO NOTHING
        """, resources)
        new_conn.commit()
        print(f"  ✓ Migrated {len(resources)} resources")
    
    old_conn.close()
    new_conn.close()

def migrate_projects():
    """Migrate projects table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating PROJECTS...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT 
                pk_project_no,
                fk_client,
                project_name,
                project_desc,
                client_po,
                COALESCE(project_status, 'unknown')
            FROM bgs.tbl_project
        """)
        
        projects = []
        for row in old_cur.fetchall():
            proj_code = row[0]
            # Extract year and number from project code (e.g., tex.23.1891)
            parts = proj_code.split('.')
            if len(parts) >= 3:
                try:
                    year = 2000 + int(parts[1])
                    proj_num = int(parts[2].split('_')[0])  # Handle codes like tbls.21.1079_cwk
                except:
                    year = 2020
                    proj_num = 0
            else:
                year = 2020
                proj_num = 0
            
            projects.append((
                proj_code,      # project_code
                row[1],         # client_code
                year,           # project_year
                proj_num,       # project_number
                row[2],         # project_name
                row[3],         # project_desc
                row[4],         # client_po
                row[5]          # status
            ))
        
        execute_batch(new_cur, """
            INSERT INTO bgs.project 
            (project_code, client_code, project_year, project_number,
             project_name, project_desc, client_po, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_code) DO NOTHING
        """, projects)
        new_conn.commit()
        print(f"  ✓ Migrated {len(projects)} projects")
    
    old_conn.close()
    new_conn.close()

def migrate_tasks():
    """Migrate tasks table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating TASKS...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT fk_proj_no, task_no, task_name, task_notes,
                   sub_task_no, sub_task_name, task_co_no, task_co_name
            FROM bgs.tbl_task
        """)
        tasks = old_cur.fetchall()
        
        execute_batch(new_cur, """
            INSERT INTO bgs.task 
            (project_code, task_no, task_name, task_notes,
             sub_task_no, sub_task_name, task_co_no, task_co_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_code, task_no, sub_task_no) DO NOTHING
        """, tasks)
        new_conn.commit()
        print(f"  ✓ Migrated {len(tasks)} tasks")
    
    old_conn.close()
    new_conn.close()

def migrate_baseline():
    """Migrate baseline table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating BASELINE...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT fk_proj_no, fk_task_no, fk_sub_task_no, fk_res_id,
                   base_units, base_rate, base_miles, base_expense, base_miles_rate
            FROM bgs.tbl_base
        """)
        baseline = old_cur.fetchall()
        
        execute_batch(new_cur, """
            INSERT INTO bgs.baseline 
            (project_code, task_no, sub_task_no, res_id,
             base_units, base_rate, base_miles, base_expense, base_miles_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, baseline)
        new_conn.commit()
        print(f"  ✓ Migrated {len(baseline)} baseline records")
    
    old_conn.close()
    new_conn.close()

def migrate_timesheets():
    """Migrate timesheet table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating TIMESHEETS...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT yr_mon, fk_proj_no, fk_task_no, fk_sub_task_no, ts_date,
                   fk_res_id, ts_units, ts_mileage, ts_expense, ts_desc,
                   fk_inv_no, fk_task_co_no
            FROM bgs.tbl_ts
            ORDER BY ts_date
        """)
        timesheets = old_cur.fetchall()
        
        execute_batch(new_cur, """
            INSERT INTO bgs.timesheet 
            (yr_mon, project_code, task_no, sub_task_no, ts_date,
             res_id, ts_units, ts_mileage, ts_expense, ts_desc,
             invoice_code, task_co_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, timesheets)
        new_conn.commit()
        print(f"  ✓ Migrated {len(timesheets)} timesheet records")
    
    old_conn.close()
    new_conn.close()

def migrate_invoices():
    """Migrate invoice table"""
    old_conn = psycopg2.connect(**OLD_DB)
    new_conn = psycopg2.connect(**NEW_DB)
    
    print("Migrating INVOICES...")
    with old_conn.cursor() as old_cur, new_conn.cursor() as new_cur:
        old_cur.execute("""
            SELECT pk_invno, fk_proj_no, invdate, invamt, invstatus, invdesc
            FROM bgs.tbl_inv
        """)
        
        invoices = []
        for row in old_cur.fetchall():
            inv_code = row[0]
            # Extract invoice number from code (e.g., cnh.18.1880.0001 → 1)
            parts = inv_code.split('.')
            if len(parts) >= 4:
                try:
                    inv_num = int(parts[3])
                except:
                    inv_num = 1
            else:
                inv_num = 1
            
            invoices.append((
                inv_code,   # invoice_code
                row[1],     # project_code
                inv_num,    # invoice_number
                row[2],     # invoice_date
                row[3],     # amount
                row[4],     # status
                row[5]      # notes/desc
            ))
        
        execute_batch(new_cur, """
            INSERT INTO bgs.invoice 
            (invoice_code, project_code, invoice_number, invoice_date,
             amount, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invoice_code) DO NOTHING
        """, invoices)
        new_conn.commit()
        print(f"  ✓ Migrated {len(invoices)} invoices")
    
    old_conn.close()
    new_conn.close()

def print_summary():
    """Print migration summary"""
    conn = psycopg2.connect(**NEW_DB)
    
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    
    with conn.cursor() as cur:
        tables = [
            ('CLIENTS', 'bgs.client'),
            ('RESOURCES', 'bgs.resource'),
            ('PROJECTS', 'bgs.project'),
            ('TASKS', 'bgs.task'),
            ('BASELINE', 'bgs.baseline'),
            ('TIMESHEETS', 'bgs.timesheet'),
            ('INVOICES', 'bgs.invoice')
        ]
        
        for name, table in tables:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"{name:15} {count:>6} records")
    
    conn.close()

if __name__ == '__main__':
    print("Starting BGS data migration...")
    print("="*50)
    
    try:
        migrate_clients()
        migrate_resources()
        migrate_projects()
        migrate_tasks()
        migrate_baseline()
        migrate_timesheets()
        migrate_invoices()
        print_summary()
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
