"""Main Typer CLI application."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperstack.db import init_db

from .commands import add, done, prefs, reading, search, view

console = Console()

app = typer.Typer(
    name="paperstack",
    help="Academic paper management CLI with web-based viewer and agentic search.",
    no_args_is_help=False,
    invoke_without_command=True,
)

# Register command groups
app.add_typer(add.app, name="add", help="Add papers to your library")
app.add_typer(reading.app, name="reading", help="Manage reading list")
app.add_typer(done.app, name="done", help="Manage completed papers")
app.add_typer(search.app, name="search", help="Search papers")
app.add_typer(prefs.app, name="prefs", help="Manage preferences")


@app.command("view")
def view_paper(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to view (optional, uses browser if not provided)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    scholar: bool = typer.Option(False, "--scholar", "-s", help="Use Google Scholar PDF Reader"),
    builtin: bool = typer.Option(False, "--builtin", "-b", help="Use built-in PDF.js viewer"),
):
    """Open a paper in the PDF viewer."""
    if paper_id is None:
        # Launch interactive browser to select paper
        from paperstack.cli.browser import browse_papers, view_paper as browser_view_paper, Action

        action, paper = browse_papers(title="Select Paper to View")
        if paper and action == Action.VIEW:
            browser_view_paper(paper, console)
        return

    from paperstack.config import ViewerMode, get_settings
    from paperstack.db import Repository

    settings = get_settings()
    repo = Repository()
    paper = repo.get_paper(paper_id)
    repo.close()

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        raise typer.Exit(1)

    if not paper.pdf_path:
        # No local PDF - try to open from URL if it's a PDF URL
        if paper.url and _is_pdf_url(paper.url):
            pdf_url = _get_pdf_url(paper.url)
            console.print(f"[green]Opening PDF from URL:[/green] {paper.title}")
            _open_in_chrome(pdf_url)
            return
        console.print(f"[yellow]Paper '{paper.title}' has no PDF attached[/yellow]")
        console.print("Use 'paperstack add pdf <id> <path>' to attach a PDF")
        raise typer.Exit(1)

    # Determine viewer mode (flags override preference)
    viewer_mode = settings.viewer_mode
    if scholar:
        viewer_mode = ViewerMode.SCHOLAR
    elif builtin:
        viewer_mode = ViewerMode.BUILTIN

    if viewer_mode == ViewerMode.SCHOLAR:
        # Open PDF directly in browser - Chrome extension will take over
        _view_with_scholar(paper, settings, no_browser)
    else:
        # Use built-in Flask + PDF.js viewer
        _view_with_builtin(paper, paper_id, settings, no_browser)


def _view_with_scholar(paper, settings, no_browser: bool):
    """Open PDF with Google Scholar PDF Reader Chrome extension."""
    from pathlib import Path

    pdf_path = Path(paper.pdf_path)

    if not pdf_path.exists():
        console.print(f"[red]PDF file not found:[/red] {pdf_path}")
        raise typer.Exit(1)

    # Convert to file:// URL for Chrome to open
    file_url = f"file://{pdf_path.absolute()}"

    console.print(f"[green]Opening with Scholar PDF Reader:[/green] {paper.title}")
    console.print(f"[blue]File:[/blue] {pdf_path}")
    console.print()
    console.print("[dim]Make sure the Google Scholar PDF Reader extension is installed![/dim]")
    console.print("[dim]https://chromewebstore.google.com/detail/dahenjhkoodjbpjheillcadbppiidmhp[/dim]")

    if not no_browser:
        _open_in_chrome(file_url)


def _view_with_builtin(paper, paper_id: int, settings, no_browser: bool):
    """Open PDF with built-in Flask + PDF.js viewer."""
    from paperstack.viewer import run_viewer

    url = f"http://{settings.viewer_host}:{settings.viewer_port}/?paper_id={paper_id}"

    console.print(f"[green]Opening viewer for:[/green] {paper.title}")
    console.print(f"[blue]URL:[/blue] {url}")

    # run_viewer now handles opening the browser after server starts
    run_viewer(paper_id=paper_id, open_browser=not no_browser)


def _is_pdf_url(url: str) -> bool:
    """Check if URL points to a PDF (arXiv, direct PDF links, etc.)."""
    if not url:
        return False
    url_lower = url.lower()
    # Direct PDF links
    if url_lower.endswith(".pdf"):
        return True
    # arXiv PDF URLs
    if "arxiv.org/pdf/" in url_lower:
        return True
    # arXiv abstract URLs - convert to PDF
    if "arxiv.org/abs/" in url_lower:
        return True
    return False


def _get_pdf_url(url: str) -> str:
    """Convert URL to PDF URL if needed (e.g., arXiv abs -> pdf)."""
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/")
    return url


def _open_in_chrome(url: str):
    """Open URL specifically in Chrome browser."""
    import subprocess
    import sys
    import webbrowser

    if sys.platform == "darwin":  # macOS
        try:
            subprocess.run(["open", "-a", "Google Chrome", url], check=True)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Fall back to default browser
    elif sys.platform == "win32":  # Windows
        try:
            # Try common Chrome paths on Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for chrome_path in chrome_paths:
                try:
                    subprocess.run([chrome_path, url], check=True)
                    return
                except FileNotFoundError:
                    continue
        except subprocess.CalledProcessError:
            pass  # Fall back to default browser
    else:  # Linux
        try:
            subprocess.run(["google-chrome", url], check=True)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["chromium-browser", url], check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # Fall back to default browser

    # Fallback to default browser
    webbrowser.open(url)


@app.command()
def shell():
    """Start interactive REPL mode."""
    from .repl import run_repl
    run_repl()


@app.command()
def init(
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive setup"),
):
    """Initialize Paperstack database and directories."""
    from paperstack.config import StorageBackend, ViewerMode, get_settings, reload_settings
    import json

    settings = get_settings()
    settings.ensure_directories()
    init_db()

    console.print(f"[green]Initialized Paperstack at:[/green] {settings.home_dir}")
    console.print(f"  Database: {settings.db_path}")
    console.print(f"  Papers: {settings.papers_dir}")
    console.print(f"  Annotations: {settings.annotations_dir}")

    if interactive:
        config_data = {}
        if settings.config_file.exists():
            with open(settings.config_file) as f:
                config_data = json.load(f)

        # Storage Backend Setup
        console.print()
        console.print("[bold]Storage Setup[/bold]")
        console.print()
        console.print("Where would you like to store your PDFs?")
        console.print("  [cyan]1.[/cyan] Local storage (default, stored in ~/.paperstack/papers/)")
        console.print("  [cyan]2.[/cyan] Google Drive (sync across devices)")
        console.print()

        storage_choice = typer.prompt("Enter choice (1 or 2)", default="1")

        storage_backend = StorageBackend.LOCAL
        if storage_choice == "2":
            storage_backend = StorageBackend.GDRIVE
            console.print("[green]Using Google Drive storage[/green]")
            console.print()

            # Check if Google API libraries are installed
            try:
                import google.oauth2.credentials
                import google_auth_oauthlib.flow
                import googleapiclient.discovery
            except ImportError:
                console.print("[yellow]Google Drive libraries not installed.[/yellow]")
                console.print("[dim]Install with: pip install google-api-python-client google-auth-oauthlib[/dim]")
                console.print()
                install_libs = typer.confirm("Install Google Drive libraries now?", default=True)
                if install_libs:
                    import subprocess
                    console.print("[dim]Installing...[/dim]")
                    subprocess.run(
                        ["pip", "install", "google-api-python-client", "google-auth-oauthlib"],
                        capture_output=True
                    )
                    console.print("[green]Libraries installed![/green]")
                else:
                    console.print("[yellow]Falling back to local storage.[/yellow]")
                    storage_backend = StorageBackend.LOCAL
                    config_data["storage_backend"] = storage_backend.value

            if storage_backend == StorageBackend.GDRIVE:
                # Check for OAuth credentials
                creds_path = settings.home_dir / "gdrive_credentials.json"
                token_path = settings.home_dir / "gdrive_token.json"

                if not creds_path.exists():
                    console.print()
                    console.print("[bold]Google Drive OAuth Setup[/bold]")
                    console.print()
                    console.print("To use Google Drive, you need OAuth credentials:")
                    console.print("  [cyan]1.[/cyan] Go to https://console.cloud.google.com/")
                    console.print("  [cyan]2.[/cyan] Create a project (or select existing)")
                    console.print("  [cyan]3.[/cyan] Enable the Google Drive API")
                    console.print("  [cyan]4.[/cyan] Go to Credentials > Create Credentials > OAuth client ID")
                    console.print("  [cyan]5.[/cyan] Choose 'Desktop app' as application type")
                    console.print("  [cyan]6.[/cyan] Download the JSON file")
                    console.print(f"  [cyan]7.[/cyan] Save it as: {creds_path}")
                    console.print()

                    open_console = typer.confirm("Open Google Cloud Console?", default=True)
                    if open_console:
                        import webbrowser
                        webbrowser.open("https://console.cloud.google.com/apis/credentials")

                    console.print()
                    console.print(f"[dim]After saving credentials to {creds_path},[/dim]")
                    console.print("[dim]run 'paperstack init' again to complete authentication.[/dim]")

                elif not token_path.exists():
                    # Credentials exist but not authenticated yet
                    console.print()
                    console.print("[bold]Google Drive Authentication[/bold]")
                    console.print()
                    authenticate = typer.confirm("Open browser to authenticate with Google?", default=True)

                    if authenticate:
                        try:
                            from paperstack.storage.gdrive import GoogleDriveStorage
                            console.print("[dim]Opening browser for authentication...[/dim]")
                            gdrive = GoogleDriveStorage()
                            # This triggers the OAuth flow
                            _ = gdrive.service
                            console.print("[green]Successfully authenticated with Google Drive![/green]")
                        except Exception as e:
                            console.print(f"[red]Authentication failed: {e}[/red]")
                            console.print("[yellow]Falling back to local storage.[/yellow]")
                            storage_backend = StorageBackend.LOCAL
                else:
                    console.print("[green]Google Drive already authenticated![/green]")

                # Ask for folder ID
                if storage_backend == StorageBackend.GDRIVE:
                    console.print()
                    console.print("[dim]You'll need a Google Drive folder ID.[/dim]")
                    console.print("[dim]Create a folder in Drive, then copy the ID from the URL.[/dim]")
                    console.print("[dim](The ID is the long string after /folders/ in the URL)[/dim]")
                    folder_id = typer.prompt("Enter Google Drive folder ID (or press Enter to skip)", default="")

                    if folder_id:
                        config_data["gdrive_folder_id"] = folder_id
                        console.print("[green]Folder ID saved[/green]")
                    else:
                        console.print("[yellow]Skipped - set later with: paperstack prefs set gdrive_folder_id <ID>[/yellow]")
        else:
            console.print("[green]Using local storage[/green]")

        config_data["storage_backend"] = storage_backend.value

        # PDF Viewer Setup
        console.print()
        console.print("[bold]PDF Viewer Setup[/bold]")
        console.print()
        console.print("Choose your preferred PDF viewer:")
        console.print("  [cyan]1.[/cyan] Built-in viewer (Flask + PDF.js with annotations)")
        console.print("  [cyan]2.[/cyan] Google Scholar PDF Reader (Chrome extension)")
        console.print()
        console.print("[dim]The Scholar extension offers citation hover, AI outlines,[/dim]")
        console.print("[dim]and figure navigation. Install from:[/dim]")
        console.print("[dim]https://chromewebstore.google.com/detail/dahenjhkoodjbpjheillcadbppiidmhp[/dim]")
        console.print()

        viewer_choice = typer.prompt("Enter choice (1 or 2)", default="1")

        viewer_mode = ViewerMode.BUILTIN
        if viewer_choice == "2":
            viewer_mode = ViewerMode.SCHOLAR
            console.print("[green]Using Google Scholar PDF Reader[/green]")

            # Offer to open Chrome Web Store for installation
            install = typer.confirm("Open Chrome Web Store to install the extension?", default=True)
            if install:
                import webbrowser
                webbrowser.open("https://chromewebstore.google.com/detail/google-scholar-pdf-reader/dahenjhkoodjbpjheillcadbppiidmhp")
                console.print("[dim]Opening Chrome Web Store...[/dim]")
                console.print("[dim]Click 'Add to Chrome' to install the extension.[/dim]")
        else:
            console.print("[green]Using built-in PDF viewer[/green]")

        config_data["viewer_mode"] = viewer_mode.value

        # Save all preferences
        with open(settings.config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        reload_settings()

    console.print()
    console.print("[dim]Run 'paperstack add url <URL>' to add your first paper![/dim]")


@app.command()
def stats():
    """Show library statistics."""
    from paperstack.db import Repository
    from paperstack.memory import MemoryManager

    repo = Repository()

    reading_count = len(repo.list_reading())
    done_count = len(repo.list_done())
    total_count = len(repo.list_papers())

    # Get annotation count
    annotations_count = 0
    for paper in repo.list_papers():
        annotations_count += len(repo.get_annotations(paper.id))

    repo.close()

    # Get memory stats
    memory = MemoryManager()
    memory_stats = memory.get_stats()

    console.print("\n[bold]Paperstack Statistics[/bold]\n")
    console.print(f"  Papers:")
    console.print(f"    Reading: {reading_count}")
    console.print(f"    Done: {done_count}")
    console.print(f"    Total: {total_count}")
    console.print(f"  Annotations: {annotations_count}")
    console.print(f"  Search Memory:")
    console.print(f"    Active queries: {memory_stats['active_memories']}")
    console.print(f"    Sessions: {memory_stats['sessions']}")


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Initialize database on every command."""
    init_db()

    # Show interactive menu if no command provided
    if ctx.invoked_subcommand is None:
        show_main_menu()


def show_main_menu():
    """Show interactive main menu."""
    import shutil

    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style

    from paperstack.db import Repository

    # Get terminal width
    term_width = shutil.get_terminal_size().columns

    # Get stats
    repo = Repository()
    reading_count = len(repo.list_reading())
    done_count = len(repo.list_done())
    repo.close()

    menu_items = [
        ("reading", "Browse Reading List", f"{reading_count} papers"),
        ("done", "Browse Completed Papers", f"{done_count} papers"),
        ("add", "Add New Paper", "from URL or search"),
        ("search", "Search Papers", "local or external"),
        ("stats", "Show Statistics", "library overview"),
        ("prefs", "Preferences", "configure settings"),
        ("shell", "Interactive Shell", "REPL mode"),
        ("quit", "Quit", "exit paperstack"),
    ]

    selected_index = 0
    result_action = None

    def get_formatted_text():
        lines = []

        # Header with ASCII art (centered)
        logo_lines = [
            "╔═══════════════════════════════════════════════════════════╗",
            "║   ██████╗  █████╗ ██████╗ ███████╗██████╗                 ║",
            "║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗                ║",
            "║   ██████╔╝███████║██████╔╝█████╗  ██████╔╝                ║",
            "║   ██╔═══╝ ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗                ║",
            "║   ██║     ██║  ██║██║     ███████╗██║  ██║                ║",
            "║   ╚═╝     ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝                ║",
            "║   ███████╗████████╗ █████╗  ██████╗██╗  ██╗               ║",
            "║   ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝               ║",
            "║   ███████╗   ██║   ███████║██║     █████╔╝                ║",
            "║   ╚════██║   ██║   ██╔══██║██║     ██╔═██╗                ║",
            "║   ███████║   ██║   ██║  ██║╚██████╗██║  ██╗               ║",
            "║   ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝               ║",
            "╚═══════════════════════════════════════════════════════════╝",
        ]

        lines.append(("", "\n"))
        logo_width = 63  # Width of the logo box
        for logo_line in logo_lines:
            padding = max(0, (term_width - logo_width) // 2)
            # Add unstyled padding, then styled logo
            lines.append(("", " " * padding))
            lines.append(("class:logo", logo_line + "\n"))

        lines.append(("", "\n"))

        # Menu items with proper spacing
        label_width = 30
        gap = "  ·····  "  # Visual separator between label and description

        for i, (key, label, desc) in enumerate(menu_items):
            # Calculate left padding to center the menu
            menu_content_width = 4 + label_width + len(gap) + 20  # prefix + label + gap + desc
            left_pad = max(2, (term_width - menu_content_width) // 2)

            # Add unstyled padding first, then styled content
            lines.append(("", " " * left_pad))
            if i == selected_index:
                lines.append(("class:selected", f"▸ {label:<{label_width}}"))
                lines.append(("class:gap", gap))
                lines.append(("class:selected-desc", f"{desc}\n"))
            else:
                lines.append(("class:menu", f"  {label:<{label_width}}"))
                lines.append(("class:gap", gap))
                lines.append(("class:desc", f"{desc}\n"))

        lines.append(("", "\n"))
        help_text = "↑/↓: Navigate   Enter: Select   q: Quit"
        help_pad = max(2, (term_width - len(help_text)) // 2)
        # Add unstyled padding, then styled help text
        lines.append(("", " " * help_pad))
        lines.append(("class:help", help_text + "\n"))

        return lines

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def move_up(event):
        nonlocal selected_index
        if selected_index > 0:
            selected_index -= 1

    @kb.add("down")
    @kb.add("j")
    def move_down(event):
        nonlocal selected_index
        if selected_index < len(menu_items) - 1:
            selected_index += 1

    @kb.add("enter")
    def select_item(event):
        nonlocal result_action
        result_action = menu_items[selected_index][0]
        event.app.exit()

    @kb.add("q")
    @kb.add("escape")
    def quit_menu(event):
        nonlocal result_action
        result_action = "quit"
        event.app.exit()

    style = Style.from_dict({
        "logo": "#e94560 bold",
        "selected": "#4caf50 bold",
        "selected-desc": "#81c784",
        "menu": "#eeeeee",
        "desc": "#888888",
        "gap": "#555555",
        "help": "#666666",
    })

    layout = Layout(
        Window(
            FormattedTextControl(get_formatted_text),
            wrap_lines=True,
        )
    )

    app_ui: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=True,
    )

    app_ui.run()

    # Handle selected action
    if result_action == "quit":
        return
    elif result_action == "reading":
        from paperstack.cli.browser import interactive_loop
        interactive_loop(status="reading", title="Reading List")
        # Return to main menu after browsing
        show_main_menu()
    elif result_action == "done":
        from paperstack.cli.browser import interactive_loop
        interactive_loop(status="done", title="Completed Papers")
        # Return to main menu after browsing
        show_main_menu()
    elif result_action == "add":
        # Show add submenu
        console.print("\n[bold]Add Paper[/bold]")
        console.print("  paperstack add url <URL>     - Add from URL")
        console.print("  paperstack add search <Q>    - Search and add")
        console.print("  paperstack add manual -t '.' - Add manually")
        url = typer.prompt("\nEnter paper URL (or press Enter to go back)", default="")
        if url:
            from paperstack.cli.commands.add import url as add_url_cmd
            add_url_cmd(url)
        # Return to main menu
        show_main_menu()
    elif result_action == "search":
        console.print("\n[bold]Search[/bold]")
        query = typer.prompt("Enter search query (or press Enter to go back)", default="")
        if query:
            # Call search directly instead of through Typer command
            from paperstack.embeddings import SemanticSearch
            from paperstack.memory import MemoryManager

            console.print(f"[blue]Searching:[/blue] {query}")

            search = SemanticSearch()
            results = search.search(query, top_k=10, done_only=True)

            memory = MemoryManager()
            memory.record_search(query, [{"id": r.paper.id, "title": r.paper.title} for r in results])

            if not results:
                console.print("[yellow]No matching papers found[/yellow]")
                similar = memory.find_similar_searches(query, top_k=3)
                if similar:
                    console.print("\n[dim]Similar past searches:[/dim]")
                    for s in similar:
                        console.print(f"  - {s['query']}")
            else:
                console.print(f"\n[green]Found {len(results)} matching papers:[/green]\n")
                for i, result in enumerate(results, 1):
                    paper = result.paper
                    score_pct = int(result.score * 100)
                    console.print(f"[cyan]{i}.[/cyan] [bold]{paper.title}[/bold] ({score_pct}% match)")

            console.input("\n[dim]Press Enter to continue...[/dim]")
        # Return to main menu
        show_main_menu()
    elif result_action == "stats":
        stats()
        console.input("\n[dim]Press Enter to continue...[/dim]")
        show_main_menu()
    elif result_action == "prefs":
        from paperstack.cli.commands.prefs import show_prefs
        show_prefs()
        console.input("\n[dim]Press Enter to continue...[/dim]")
        show_main_menu()
    elif result_action == "shell":
        from .repl import run_repl
        run_repl()
        # Return to main menu after shell exits
        show_main_menu()


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
