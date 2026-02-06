"""Interactive paper browser with keyboard navigation."""
from __future__ import annotations

import json
from enum import Enum
from typing import Callable, List, Optional, Tuple

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from rich.console import Console

from paperstack.db import Repository
from paperstack.db.models import Paper, PaperStatus


class Action(Enum):
    """Actions that can be performed on a paper."""
    VIEW = "view"
    DONE = "done"
    READING = "reading"
    DELETE = "delete"
    SHOW = "show"
    QUIT = "quit"


class PaperBrowser:
    """Interactive paper browser with keyboard navigation."""

    def __init__(
        self,
        papers: List[Paper],
        title: str = "Papers",
        show_status: bool = True,
    ):
        self.papers = papers
        self.title = title
        self.show_status = show_status
        self.selected_index = 0
        self.action: Optional[Action] = None
        self.selected_paper: Optional[Paper] = None
        self.console = Console()

    def _get_paper_display(self, paper: Paper, selected: bool) -> str:
        """Format a paper for display."""
        prefix = "► " if selected else "  "
        tags = json.loads(paper.tags) if paper.tags else []
        tags_str = f" [{', '.join(tags[:2])}]" if tags else ""
        status_str = f" ({paper.status})" if self.show_status else ""

        title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
        return f"{prefix}{paper.id:3d}. {title}{tags_str}{status_str}"

    def _get_formatted_text(self) -> List[Tuple[str, str]]:
        """Get formatted text for display."""
        lines: List[Tuple[str, str]] = []

        # Title
        lines.append(("class:title", f"\n  {self.title}\n\n"))

        if not self.papers:
            lines.append(("class:dim", "  No papers found.\n"))
            lines.append(("class:dim", "\n  Press 'q' to quit.\n"))
            return lines

        # Papers list
        for i, paper in enumerate(self.papers):
            selected = i == self.selected_index
            style = "class:selected" if selected else "class:paper"
            lines.append((style, self._get_paper_display(paper, selected) + "\n"))

        # Help text
        lines.append(("class:dim", "\n"))
        lines.append(("class:help", "  ↑/↓: Navigate  "))
        lines.append(("class:help", "Enter: Details  "))
        lines.append(("class:help", "v: View PDF  "))
        lines.append(("class:help", "d: Mark Done  "))
        lines.append(("class:help", "r: Move to Reading  "))
        lines.append(("class:help", "x: Delete  "))
        lines.append(("class:help", "q: Quit\n"))

        return lines

    def run(self) -> Tuple[Optional[Action], Optional[Paper]]:
        """Run the interactive browser. Returns (action, paper) or (None, None)."""
        if not self.papers:
            self.console.print(f"\n[bold]{self.title}[/bold]\n")
            self.console.print("[yellow]No papers found.[/yellow]")
            return None, None

        kb = KeyBindings()

        @kb.add("up")
        @kb.add("k")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        @kb.add("j")
        def move_down(event):
            if self.selected_index < len(self.papers) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select_show(event):
            self.action = Action.SHOW
            self.selected_paper = self.papers[self.selected_index]
            event.app.exit()

        @kb.add("v")
        def select_view(event):
            self.action = Action.VIEW
            self.selected_paper = self.papers[self.selected_index]
            event.app.exit()

        @kb.add("d")
        def select_done(event):
            self.action = Action.DONE
            self.selected_paper = self.papers[self.selected_index]
            event.app.exit()

        @kb.add("r")
        def select_reading(event):
            self.action = Action.READING
            self.selected_paper = self.papers[self.selected_index]
            event.app.exit()

        @kb.add("x")
        def select_delete(event):
            self.action = Action.DELETE
            self.selected_paper = self.papers[self.selected_index]
            event.app.exit()

        @kb.add("q")
        @kb.add("escape")
        def quit_browser(event):
            self.action = Action.QUIT
            event.app.exit()

        # Page navigation
        @kb.add("pageup")
        def page_up(event):
            self.selected_index = max(0, self.selected_index - 10)

        @kb.add("pagedown")
        def page_down(event):
            self.selected_index = min(len(self.papers) - 1, self.selected_index + 10)

        @kb.add("home")
        def go_home(event):
            self.selected_index = 0

        @kb.add("end")
        def go_end(event):
            self.selected_index = len(self.papers) - 1

        style = Style.from_dict({
            "title": "#e94560 bold",
            "selected": "#4caf50 bold",
            "paper": "#eeeeee",
            "dim": "#666666",
            "help": "#888888",
        })

        layout = Layout(
            Window(
                FormattedTextControl(self._get_formatted_text),
                wrap_lines=True,
            )
        )

        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=True,
        )

        app.run()

        return self.action, self.selected_paper


def browse_papers(
    status: Optional[str] = None,
    title: str = "Papers",
) -> Tuple[Optional[Action], Optional[Paper]]:
    """Browse papers interactively."""
    repo = Repository()

    if status:
        papers = repo.list_papers(status=status)
    else:
        papers = repo.list_papers()

    # Keep papers in session for the browser
    browser = PaperBrowser(papers, title=title, show_status=(status is None))
    action, paper = browser.run()

    # Get fresh paper reference if needed for operations
    if paper:
        paper = repo.get_paper(paper.id)

    repo.close()
    return action, paper


def handle_action(action: Action, paper: Paper, console: Console) -> bool:
    """Handle an action on a paper. Returns True to continue browsing."""
    if action == Action.QUIT:
        return False

    if action == Action.SHOW:
        show_paper_details(paper, console)
        return True

    if action == Action.VIEW:
        view_paper(paper, console)
        return False  # Exit after launching viewer

    if action == Action.DONE:
        mark_paper_done(paper, console)
        return True

    if action == Action.READING:
        move_to_reading(paper, console)
        return True

    if action == Action.DELETE:
        delete_paper(paper, console)
        return True

    return False


def show_paper_details(paper: Paper, console: Console) -> None:
    """Show detailed paper information."""
    import json

    tags = json.loads(paper.tags) if paper.tags else []

    console.print(f"\n[bold cyan]#{paper.id}[/bold cyan] [bold]{paper.title}[/bold]")
    console.print()

    if paper.authors:
        console.print(f"[blue]Authors:[/blue] {paper.authors}")
    if paper.doi:
        console.print(f"[blue]DOI:[/blue] {paper.doi}")
    if paper.arxiv_id:
        console.print(f"[blue]arXiv:[/blue] {paper.arxiv_id}")
    if tags:
        console.print(f"[blue]Tags:[/blue] {', '.join(tags)}")

    console.print(f"[blue]Status:[/blue] {paper.status}")
    console.print(f"[blue]URL:[/blue] {paper.url}")

    if paper.pdf_path:
        console.print(f"[blue]PDF:[/blue] {paper.pdf_path}")

    if paper.description:
        console.print(f"\n[blue]Description:[/blue] {paper.description}")

    if paper.abstract:
        console.print(f"\n[blue]Abstract:[/blue]")
        abstract = paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract
        console.print(f"  {abstract}")

    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


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
            pass
    elif sys.platform == "win32":  # Windows
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for chrome_path in chrome_paths:
            try:
                subprocess.run([chrome_path, url], check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
    else:  # Linux
        for cmd in ["google-chrome", "chromium-browser"]:
            try:
                subprocess.run([cmd, url], check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

    # Fallback to default browser
    webbrowser.open(url)


def view_paper(paper: Paper, console: Console) -> None:
    """Open paper in PDF viewer."""
    if not paper.pdf_path:
        # No local PDF - try to open from URL if it's a PDF URL
        if paper.url and _is_pdf_url(paper.url):
            pdf_url = _get_pdf_url(paper.url)
            console.print(f"[green]Opening PDF from URL:[/green] {paper.title}")
            _open_in_chrome(pdf_url)
            return
        console.print("[yellow]No PDF attached to this paper.[/yellow]")
        console.print("Use 'paperstack add pdf <id> <path>' to attach a PDF.")
        console.input("[dim]Press Enter to continue...[/dim]")
        return

    from pathlib import Path
    from paperstack.config import ViewerMode, get_settings

    settings = get_settings()

    if settings.viewer_mode == ViewerMode.SCHOLAR:
        # Open PDF directly for Chrome extension
        pdf_path = Path(paper.pdf_path)
        if not pdf_path.exists():
            console.print(f"[red]PDF file not found:[/red] {pdf_path}")
            return

        file_url = f"file://{pdf_path.absolute()}"
        console.print(f"[green]Opening with Scholar PDF Reader:[/green] {paper.title}")
        console.print("[dim]Make sure the Google Scholar PDF Reader extension is installed![/dim]")
        _open_in_chrome(file_url)
    else:
        # Use built-in Flask + PDF.js viewer
        from paperstack.viewer import run_viewer

        url = f"http://{settings.viewer_host}:{settings.viewer_port}/?paper_id={paper.id}"
        console.print(f"[green]Opening viewer for:[/green] {paper.title}")
        _open_in_chrome(url)
        run_viewer(paper_id=paper.id)


def mark_paper_done(paper: Paper, console: Console) -> None:
    """Mark a paper as done with concepts."""
    from prompt_toolkit import prompt

    if paper.status == PaperStatus.DONE.value:
        console.print(f"[yellow]Paper #{paper.id} is already marked as done.[/yellow]")
        return

    console.print(f"\n[bold]Mark as Done:[/bold] {paper.title}")
    concepts_input = prompt("Enter concepts learned (comma-separated): ")

    if not concepts_input.strip():
        console.print("[yellow]No concepts provided. Cancelled.[/yellow]")
        return

    concepts = [c.strip() for c in concepts_input.split(",") if c.strip()]

    repo = Repository()

    # Generate summary using LLM (interactive if no API key)
    compressed_summary = None
    try:
        from paperstack.llm import get_llm_client
        console.print("[dim]Generating summary...[/dim]")
        client = get_llm_client()
        compressed_summary = client.generate_compressed_summary(
            title=paper.title,
            abstract=paper.abstract,
            user_concepts=concepts,
        )
    except Exception as e:
        console.print(f"[yellow]Warning: Could not generate summary: {e}[/yellow]")

    repo.mark_done(
        paper_id=paper.id,
        user_concepts=concepts,
        compressed_summary=compressed_summary,
    )

    # Index for search
    from paperstack.embeddings import SemanticSearch
    search = SemanticSearch(repo=repo)
    search.index_paper(paper.id)

    repo.close()
    console.print(f"[green]Marked paper #{paper.id} as done with concepts: {', '.join(concepts)}[/green]")


def move_to_reading(paper: Paper, console: Console) -> None:
    """Move a paper back to reading list."""
    if paper.status == PaperStatus.READING.value:
        console.print(f"[yellow]Paper #{paper.id} is already in reading list.[/yellow]")
        return

    repo = Repository()
    repo.update_paper(paper.id, status=PaperStatus.READING.value)
    repo.close()

    console.print(f"[green]Moved paper #{paper.id} back to reading list.[/green]")


def delete_paper(paper: Paper, console: Console) -> None:
    """Delete a paper after confirmation."""
    from prompt_toolkit import prompt

    console.print(f"\n[bold red]Delete:[/bold red] {paper.title}")
    confirm = prompt("Are you sure? (y/N): ")

    if confirm.lower() != "y":
        console.print("[yellow]Cancelled.[/yellow]")
        return

    repo = Repository()

    # Delete PDF if exists
    if paper.pdf_path:
        from paperstack.storage import LocalStorage
        storage = LocalStorage()
        storage.delete_pdf(paper.pdf_path)

    repo.delete_paper(paper.id)
    repo.close()

    console.print(f"[green]Deleted paper #{paper.id}.[/green]")


def interactive_loop(
    status: Optional[str] = None,
    title: str = "Papers",
) -> None:
    """Run interactive browser in a loop until quit."""
    console = Console()

    while True:
        action, paper = browse_papers(status=status, title=title)

        if action is None or action == Action.QUIT:
            break

        if paper:
            continue_browsing = handle_action(action, paper, console)
            if not continue_browsing:
                break
