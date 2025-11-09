#!/usr/bin/env python3
import os
import psycopg2

DB_HOST = "192.168.30.180"
DB_NAME = "copilot_db"
DB_USER = "frank"
DB_PASS = "basalt63"

PARENT = "/mnt/sda1/01_bgm_projman/Active/"
SUBFOLDERS = [
    "01_baseline",
    "02_invoices",
    "03_authorization",
    "04_subcontractors",
    "05_reports",
]

def sanitize(s):
    """Sanitize for safe folder names: Replace spaces with underscores, remove bad chars."""
    if s is None:
        return ""
    return "".join(
        c if c.isalnum() or c in ('_', '-') else '_' for c in s.replace(" ", "_")
    )

def main():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            p.project_code, 
            p.project_name, 
            c.code as client_code
        FROM bgs.project p
        JOIN bgs.client c ON p.client_code = c.code
        WHERE p.status = 'active'
    """)
    print("Create Directory Structure\n")
    for project_code, project_name, client_code in cur.fetchall():
        print(f"Project: {project_name or '(No Project Name)'}")
        print(f"Client: {client_code}")
        print(f"Project Code: {project_code}\n")

        # Decide directory naming format
        if project_name and project_name.strip() != "":
            safe_name = sanitize(project_name)
            folder_name = f"{project_code}_{safe_name}"
        else:
            folder_name = project_code

        proj_dir = os.path.join(PARENT, client_code, folder_name)
        confirmation = input(f"Create directories? [y/n] (y): ").strip().lower()
        if confirmation not in ("", "y", "yes"):
            print("Skipped.")
            continue

        os.makedirs(proj_dir, exist_ok=True)
        for sub in SUBFOLDERS:
            sub_dir = os.path.join(proj_dir, sub)
            os.makedirs(sub_dir, exist_ok=True)

        print("\n✓ Directories created!")
        print(f"Location: {proj_dir}\n")
        print("Structure:")
        print(f"  {client_code}/")
        print(f"    └── {folder_name}/")
        for sub in SUBFOLDERS:
            print(f"        ├── {sub}/")
        print()
    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
