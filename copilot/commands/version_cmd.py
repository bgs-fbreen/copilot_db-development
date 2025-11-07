"""Version command"""
import click
from rich.console import Console

console = Console()

@click.command()
def version():
    """Show Copilot version information"""
    console.print("\n[bold cyan]Copilot Accounting System[/bold cyan] [green]v0.1.0[/green]")
    console.print("[dim]Database:[/dim] copilot_db")
    console.print("[dim]Entities:[/dim] BGS, MHB (711pine, 905brown, 819helen)\n")
