"""
Utility functions for Copilot
"""
import re

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

