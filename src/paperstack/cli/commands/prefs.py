"""Preferences commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage preferences")
console = Console()


@app.command("show")
def show_prefs():
    """Show current preferences."""
    from paperstack.config import get_settings
    from paperstack.db import Repository

    settings = get_settings()
    repo = Repository()
    db_prefs = repo.get_all_preferences()
    repo.close()

    console.print("\n[bold]Paperstack Configuration[/bold]\n")

    table = Table(show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    # Settings from file/env
    table.add_row("home_dir", str(settings.home_dir), "config")
    table.add_row("storage_backend", settings.storage_backend.value, "config")
    table.add_row("llm_model", settings.llm_model, "config")
    table.add_row("auto_tag", str(settings.auto_tag), "config")
    table.add_row("auto_description", str(settings.auto_description), "config")
    table.add_row("embedding_model", settings.embedding_model, "config")
    table.add_row("viewer_host", settings.viewer_host, "config")
    table.add_row("viewer_port", str(settings.viewer_port), "config")
    table.add_row("viewer_mode", settings.viewer_mode.value, "config")
    table.add_row("memory_retention_days", str(settings.memory_retention_days), "config")
    table.add_row("search_results_per_page", str(settings.search_results_per_page), "config")
    table.add_row(
        "anthropic_api_key",
        "***" if settings.anthropic_api_key else "[not set]",
        "env",
    )

    # Settings from database
    for key, value in db_prefs.items():
        if key not in ["storage_backend", "llm_model"]:  # Avoid duplicates
            table.add_row(key, value, "database")

    console.print(table)


@app.command("set")
def set_pref(
    key: str = typer.Argument(..., help="Setting key"),
    value: str = typer.Argument(..., help="Setting value"),
):
    """Set a preference value."""
    from paperstack.config import Settings, get_settings, reload_settings

    settings = get_settings()

    # Handle boolean conversions
    bool_settings = ["auto_tag", "auto_description"]
    int_settings = ["viewer_port", "memory_retention_days", "search_results_per_page", "max_search_results"]

    if key in bool_settings:
        value = value.lower() in ("true", "1", "yes", "on")

    if key in int_settings:
        try:
            value = int(value)
        except ValueError:
            console.print(f"[red]Invalid integer value for {key}[/red]")
            raise typer.Exit(1)

    # Update settings
    valid_keys = [
        "storage_backend", "gdrive_folder_id", "llm_model", "auto_tag",
        "auto_description", "embedding_model", "viewer_host", "viewer_port",
        "viewer_mode", "memory_retention_days", "search_results_per_page",
        "max_search_results",
    ]

    if key == "anthropic_api_key":
        console.print("[yellow]Set ANTHROPIC_API_KEY as an environment variable instead[/yellow]")
        raise typer.Exit(1)

    if key not in valid_keys:
        console.print(f"[red]Unknown setting: {key}[/red]")
        console.print(f"Valid settings: {', '.join(valid_keys)}")
        raise typer.Exit(1)

    # Load, update, and save settings
    config_data = {}
    if settings.config_file.exists():
        with open(settings.config_file) as f:
            config_data = json.load(f)

    config_data[key] = value

    with open(settings.config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    reload_settings()

    console.print(f"[green]Set {key} = {value}[/green]")


@app.command("reset")
def reset_pref(
    key: str = typer.Argument(None, help="Setting key to reset (or all)"),
    all_prefs: bool = typer.Option(False, "--all", help="Reset all preferences"),
):
    """Reset a preference to default."""
    from paperstack.config import Settings, get_settings, reload_settings

    settings = get_settings()

    if all_prefs:
        if settings.config_file.exists():
            settings.config_file.unlink()
        reload_settings()
        console.print("[green]Reset all preferences to defaults[/green]")
        return

    if not key:
        console.print("[red]Specify a key or use --all[/red]")
        raise typer.Exit(1)

    if not settings.config_file.exists():
        console.print(f"[yellow]{key} is already at default[/yellow]")
        return

    with open(settings.config_file) as f:
        config_data = json.load(f)

    if key in config_data:
        del config_data[key]
        with open(settings.config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        reload_settings()
        console.print(f"[green]Reset {key} to default[/green]")
    else:
        console.print(f"[yellow]{key} is already at default[/yellow]")


@app.callback(invoke_without_command=True)
def prefs_callback(
    ctx: typer.Context,
    chat: bool = typer.Option(False, "--chat", help="Interactive chat mode for preferences"),
):
    """Manage preferences. Use --chat for interactive configuration."""
    if chat:
        run_prefs_chat()
    elif ctx.invoked_subcommand is None:
        # Show prefs if no subcommand
        show_prefs()


def run_prefs_chat():
    """Interactive chat mode for preference configuration."""
    from paperstack.config import get_settings
    from paperstack.llm import get_llm_client

    settings = get_settings()

    console.print("\n[bold]Paperstack Preferences Chat[/bold]")
    console.print("[dim]Ask questions about settings or describe what you want to configure.[/dim]")
    console.print("[dim]Type 'quit' to exit.[/dim]\n")

    client = get_llm_client()

    system_prompt = """You are a helpful assistant for configuring Paperstack, an academic paper management CLI.

Available settings:
- storage_backend: 'local' or 'gdrive' - where to store PDFs
- gdrive_folder_id: Google Drive folder ID for storage
- llm_model: Claude model to use (e.g., claude-sonnet-4-20250514)
- auto_tag: true/false - automatically generate tags when adding papers
- auto_description: true/false - automatically generate descriptions
- embedding_model: sentence transformer model (e.g., all-MiniLM-L6-v2)
- viewer_host: host for PDF viewer (default: 127.0.0.1)
- viewer_port: port for PDF viewer (default: 5000)
- viewer_mode: 'builtin' or 'scholar' - PDF viewer to use
  - builtin: Flask + PDF.js viewer with annotations
  - scholar: Google Scholar PDF Reader Chrome extension (citation hover, AI outlines)
- memory_retention_days: days to keep search memory (default: 30)
- search_results_per_page: results per page in search (default: 5)
- max_search_results: maximum external search results (default: 50)

To change a setting, the user should run: paperstack prefs set <key> <value>

Help the user understand and configure these settings. Be concise."""

    messages = []

    while True:
        user_input = typer.prompt("\nYou")

        if user_input.lower() in ("quit", "q", "exit"):
            console.print("[dim]Exiting chat mode[/dim]")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat(messages, system=system_prompt, max_tokens=500)
            messages.append({"role": "assistant", "content": response})
            console.print(f"\n[blue]Assistant:[/blue] {response}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
