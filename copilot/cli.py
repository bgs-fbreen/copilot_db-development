"""Main CLI entry point for Copilot Accounting System"""
import click
from rich.console import Console
from copilot.commands import (version, timesheet, new, edit, ar, invoice, client, 
                                project, report, baseline, import_cmd, allocate,
                                staging_cmd, trial_cmd)

console = Console()

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    Copilot Accounting System

    BGS, MHB (711pine, 905brown, 819helen)
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided, launch interactive menu
        from copilot.interactive import run_interactive_menu
        run_interactive_menu()

# Register commands
cli.add_command(version)
cli.add_command(timesheet)
cli.add_command(new)
cli.add_command(edit)
cli.add_command(ar)
cli.add_command(invoice)
cli.add_command(client)
cli.add_command(project)
cli.add_command(report)
cli.add_command(baseline)
cli.add_command(import_cmd)
cli.add_command(allocate)
cli.add_command(staging_cmd)
cli.add_command(trial_cmd)

if __name__ == '__main__':
    cli()
