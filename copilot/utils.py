"""
Utility functions for Copilot
"""
import re
import calendar
from datetime import date

def sanitize_for_directory(text, max_length=30):
    """
    Convert text to safe directory name
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters except hyphens
    - Limit length
    
    Example:
        "Plant Decommissioning & Remediation" -> "plant-decommissioning-remed"
        "Case New Holland - Burlington, IA" -> "case-new-holland-burlington"
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and underscores with hyphens
    text = text.replace(' ', '-').replace('_', '-')
    
    # Remove special characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text

def get_project_directory_name(project_code, project_name, max_name_length=30):
    """
    Generate project directory name with abbreviated project name
    
    Format: {project_code}_{abbreviated_name}
    
    Example:
        cnh.25.1898, "Plant Decommissioning" -> "cnh.25.1898_plant-decommissioning"
        tbls.25.1904, "CP REA Evaluation" -> "tbls.25.1904_cp-rea-evaluation"
    """
    if not project_name:
        return project_code
    
    abbrev = sanitize_for_directory(project_name, max_name_length)
    
    if abbrev:
        return f"{project_code}_{abbrev}"
    else:
        return project_code


def get_project_directory(client_code, project_code, project_name=None):
    """
    Get the full path to a project directory
    
    Returns the path if it exists, None otherwise
    """
    import os
    from copilot.db import execute_query
    
    PROJECT_BASE = "/mnt/sda1/01_bgm_projman/Active"
    PROJECT_FALLBACK = os.path.expanduser("~/bgm_projects/Active")
    
    base_dir = PROJECT_BASE if os.path.exists(PROJECT_BASE) else PROJECT_FALLBACK
    
    # If we don't have project_name, fetch it
    if not project_name:
        result = execute_query("""
            SELECT project_name 
            FROM bgs.project 
            WHERE project_code = %s
        """, (project_code,))
        if result:
            project_name = result[0]['project_name']
    
    # Generate directory name
    dir_name = get_project_directory_name(project_code, project_name)
    project_path = os.path.join(base_dir, client_code, dir_name)
    
    if os.path.exists(project_path):
        return project_path
    
    # Fallback: try without abbreviated name
    project_path = os.path.join(base_dir, client_code, project_code)
    if os.path.exists(project_path):
        return project_path
    
    return None


def parse_period(period_str):
    """Parse period string into start and end dates.
    
    Formats:
        YYYY      -> Jan 1 to Dec 31
        YYYY-QN   -> Quarter start to quarter end
        YYYY-MM   -> Month start to month end
    
    Returns:
        tuple: (start_date, end_date) or (None, None) if invalid
    """
    if not period_str:
        return None, None
    
    # Annual: 2024
    if re.match(r'^\d{4}$', period_str):
        year = int(period_str)
        return date(year, 1, 1), date(year, 12, 31)
    
    # Quarterly: 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4
    match = re.match(r'^(\d{4})-Q([1-4])$', period_str, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        quarter_starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
        quarter_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
        start_month, start_day = quarter_starts[quarter]
        end_month, end_day = quarter_ends[quarter]
        return date(year, start_month, start_day), date(year, end_month, end_day)
    
    # Monthly: 2024-01, 2024-12
    match = re.match(r'^(\d{4})-(\d{2})$', period_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, 1), date(year, month, last_day)
    
    return None, None
