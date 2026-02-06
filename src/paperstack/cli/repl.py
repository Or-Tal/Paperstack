"""Interactive REPL for Paperstack."""
from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

from paperstack.config import get_settings

console = Console()


def get_completer() -> WordCompleter:
    """Get command completer."""
    commands = [
        "add", "add url", "add pdf", "add manual", "add search",
        "reading", "reading list", "reading show", "reading remove", "reading update",
        "done", "done mark", "done list", "done show", "done unmark",
        "search", "search local", "search deep", "search agent",
        "view",
        "prefs", "prefs show", "prefs set", "prefs reset",
        "stats",
        "help", "quit", "exit",
    ]
    return WordCompleter(commands, ignore_case=True)


def get_style() -> Style:
    """Get prompt style."""
    return Style.from_dict({
        "prompt": "#e94560 bold",
        "": "#eee",
    })


def run_repl():
    """Run the interactive REPL."""
    settings = get_settings()
    history_file = settings.home_dir / ".paperstack_history"
    settings.ensure_directories()

    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=get_completer(),
        style=get_style(),
    )

    console.print("\n[bold red]Paperstack[/bold red] [dim]Interactive Mode[/dim]")
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]\n")

    while True:
        try:
            text = session.prompt(
                [("class:prompt", "paperstack> ")],
                style=get_style(),
            ).strip()

            if not text:
                continue

            if text.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if text.lower() == "help":
                show_help()
                continue

            # Parse and execute command
            execute_command(text)

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'quit' to exit[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break


def show_help():
    """Show help for REPL commands."""
    console.print("""
[bold]Paperstack Commands[/bold]

[cyan]Paper Management:[/cyan]
  add url <URL>              Add paper from URL
  add pdf <id> <path>        Attach PDF to paper
  add manual --title "..."   Add paper manually
  add search <query>         Search and add papers

[cyan]Reading List:[/cyan]
  reading list               List papers in reading list
  reading show <id>          Show paper details
  reading remove <id>        Remove paper
  reading update <id> ...    Update paper metadata

[cyan]Done List:[/cyan]
  done mark <id> -c "..."    Mark paper as done with concepts
  done list                  List completed papers
  done show <id>             Show done entry details
  done unmark <id>           Move back to reading list

[cyan]Search:[/cyan]
  search local <query>       Semantic search over done papers
  search deep <query>        External search (Semantic Scholar, arXiv, etc.)
  search agent <query>       Agentic search with chat refinement

[cyan]Other:[/cyan]
  view <id>                  Open paper in PDF viewer
  prefs show                 Show preferences
  prefs set <key> <value>    Set preference
  stats                      Show library statistics
  help                       Show this help
  quit                       Exit REPL
""")


def execute_command(text: str):
    """Execute a REPL command."""
    import shlex
    import sys

    from paperstack.cli.app import app

    try:
        # Parse command into args
        args = shlex.split(text)

        if not args:
            return

        # Special handling for some commands
        cmd = args[0].lower()

        # Handle shortcuts
        shortcuts = {
            "ls": ["reading", "list"],
            "ll": ["reading", "list", "-v"],
            "rm": ["reading", "remove"],
            "s": ["search", "local"],
            "ds": ["search", "deep"],
        }

        if cmd in shortcuts:
            args = shortcuts[cmd] + args[1:]

        # Run through typer
        sys.argv = ["paperstack"] + args
        try:
            app(standalone_mode=False)
        except SystemExit:
            pass  # Typer raises SystemExit on completion

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
