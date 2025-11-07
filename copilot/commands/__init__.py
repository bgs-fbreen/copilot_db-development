"""BGS Copilot commands"""
from copilot.commands.version_cmd import version
from copilot.commands.timesheet_cmd import timesheet
from copilot.commands.new_cmd import new
from copilot.commands.edit_cmd import edit
from copilot.commands.ar_cmd import ar
from copilot.commands.invoice_cmd import invoice
from copilot.commands.client_cmd import client
from copilot.commands.project_cmd import project
from copilot.commands.baseline_export_cmd import export_baseline
from copilot.commands.project_workbook_cmd import create_workbook, add_invoice_to_workbook
from copilot.commands.cleanup_cmd import cleanup

__all__ = ['version', 'timesheet', 'new', 'edit', 'ar', 'invoice', 'client', 'project', 
           'export_baseline', 'create_workbook', 'add_invoice_to_workbook', 'cleanup']
