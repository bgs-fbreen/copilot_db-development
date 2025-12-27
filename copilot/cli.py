"""Main CLI entry point for Copilot Accounting System"""
import click
from rich.console import Console
from copilot.commands import version, timesheet, new, edit, ar, invoice, client, project, cleanup

console = Console()

@click.group()
def cli():
    """
    Copilot Accounting System

    BGS, MHB (711pine, 905brown, 819helen)
    """
    pass

# Register commands
cli.add_command(version)
cli.add_command(timesheet)
cli.add_command(new)
cli.add_command(edit)
cli.add_command(ar)
cli.add_command(invoice)
cli.add_command(client)
cli.add_command(project)
cli.add_command(cleanup)

if __name__ == '__main__':
    cli()
