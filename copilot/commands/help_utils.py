"""
Shared utilities for help/cheat sheet formatting across all CLI modules.

Provides consistent styling using Rich library for:
- Header panels
- Command tables
- Example panels
- Color schemes
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

# Color scheme constants
COLOR_TITLE = "bold cyan"
COLOR_SECTION = "bold yellow"
COLOR_COMMAND = "cyan"
COLOR_DESCRIPTION = "white"
COLOR_PARAM = "green"
COLOR_EXAMPLE = "dim"


def print_header(title):
    """
    Print a formatted header panel for the cheat sheet.
    
    Args:
        title: The title text to display in the header
    """
    text = Text(title, style=COLOR_TITLE, justify="center")
    console.print()
    console.print(Panel(text, border_style="cyan", padding=(0, 2)))
    console.print()


def print_section(title, commands):
    """
    Print a formatted section of commands.
    
    Args:
        title: Section title (e.g., "PROPERTY MANAGEMENT")
        commands: List of tuples (command_syntax, description)
    """
    console.print(f"[{COLOR_SECTION}]{title}[/{COLOR_SECTION}]")
    console.print("─" * 79)
    
    for command, description in commands:
        console.print(f"  [{COLOR_COMMAND}]{command:<45}[/{COLOR_COMMAND}] {description}")
    
    console.print()


def print_command_table(title, commands):
    """
    Print commands in a table format.
    
    Args:
        title: Table title
        commands: List of tuples (command, description) or (command, description, params)
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Command", style=COLOR_COMMAND, no_wrap=False)
    table.add_column("Description", style=COLOR_DESCRIPTION)
    
    for cmd in commands:
        if len(cmd) == 2:
            table.add_row(cmd[0], cmd[1])
        elif len(cmd) == 3:
            table.add_row(f"{cmd[0]} {cmd[2]}", cmd[1])
    
    console.print(table)
    console.print()


def print_examples(title, examples):
    """
    Print formatted examples section.
    
    Args:
        title: Examples section title (default: "EXAMPLES")
        examples: List of tuples (description, command)
    """
    console.print(f"[{COLOR_SECTION}]{title}[/{COLOR_SECTION}]")
    console.print("─" * 79)
    console.print()
    
    for description, command in examples:
        console.print(f"  [dim]# {description}[/dim]")
        console.print(f"  {command}")
        console.print()


def print_module_overview(modules):
    """
    Print overview of available modules for global help.
    
    Args:
        modules: List of tuples (module_name, description)
    """
    console.print(f"[{COLOR_SECTION}]AVAILABLE MODULES[/{COLOR_SECTION}]")
    console.print("─" * 79)
    
    for module, description in modules:
        console.print(f"  [{COLOR_COMMAND}]{module:<12}[/{COLOR_COMMAND}] {description}")
    
    console.print()
    console.print("[dim]Use 'copilot <module> help' for detailed cheat sheet of each module.[/dim]")
    console.print("[dim]Use 'copilot help --all' for complete reference of all commands.[/dim]")
    console.print()
