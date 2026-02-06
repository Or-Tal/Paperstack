"""Interactive paper browser with keyboard navigation."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

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
    BIBTEX = "bibtex"
    QUIT = "quit"


class PaperBrowser:
    """Interactive paper browser with keyboard navigation and multi-select."""

    def __init__(
        self,
        papers: List[Paper],
        title: str = "Papers",
        show_status: bool = True,
        current_status: Optional[str] = None,  # "reading" or "done" to hide irrelevant options
    ):
        self.papers = papers
        self.title = title
        self.show_status = show_status
        self.current_status = current_status
        self.selected_index = 0
        self.marked_indices: Set[int] = set()  # Multi-select
        self.action: Optional[Action] = None
        self.selected_paper: Optional[Paper] = None
        self.selected_papers: List[Paper] = []  # For batch operations
        self.console = Console()

    def _get_paper_display(self, paper: Paper, index: int) -> Tuple[str, str]:
        """Format a paper for display. Returns (prefix, text)."""
        is_selected = index == self.selected_index
        is_marked = index in self.marked_indices

        # Prefix shows selection and mark status
        if is_selected and is_marked:
            prefix = "►● "
        elif is_selected:
            prefix = "►  "
        elif is_marked:
            prefix = " ● "
        else:
            prefix = "   "

        tags = json.loads(paper.tags) if paper.tags else []
        tags_str = f" [{', '.join(tags[:2])}]" if tags else ""
        status_str = f" ({paper.status})" if self.show_status else ""

        title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
        return prefix, f"{paper.id:3d}. {title}{tags_str}{status_str}"

    def _get_formatted_text(self) -> List[Tuple[str, str]]:
        """Get formatted text for display."""
        lines: List[Tuple[str, str]] = []

        # Title with marked count
        marked_info = f" ({len(self.marked_indices)} marked)" if self.marked_indices else ""
        lines.append(("class:title", f"\n  {self.title}{marked_info}\n\n"))

        if not self.papers:
            lines.append(("class:dim", "  No papers found.\n"))
            lines.append(("class:dim", "\n  Press 'q' to quit.\n"))
            return lines

        # Papers list
        for i, paper in enumerate(self.papers):
            prefix, text = self._get_paper_display(paper, i)
            is_selected = i == self.selected_index
            is_marked = i in self.marked_indices

            if is_selected:
                style = "class:selected"
            elif is_marked:
                style = "class:marked"
            else:
                style = "class:paper"

            lines.append((style, prefix + text + "\n"))

        # Help text - context aware
        lines.append(("class:dim", "\n"))
        lines.append(("class:help", "  ↑/↓: Navigate  "))
        lines.append(("class:help", "Space: Mark  "))
        lines.append(("class:help", "Enter: Details  "))
        lines.append(("class:help", "v: View  "))
        lines.append(("class:help", "b: BibTeX  "))

        # Only show relevant actions based on current view
        if self.current_status != "done":
            lines.append(("class:help", "d: Done  "))
        if self.current_status != "reading":
            lines.append(("class:help", "r: Reading  "))

        lines.append(("class:help", "x: Delete  "))
        lines.append(("class:help", "q: Quit\n"))

        return lines

    def _get_selected_papers(self) -> List[Paper]:
        """Get list of marked papers, or current paper if none marked."""
        if self.marked_indices:
            return [self.papers[i] for i in sorted(self.marked_indices)]
        elif self.papers:
            return [self.papers[self.selected_index]]
        return []

    def run(self) -> Tuple[Optional[Action], List[Paper]]:
        """Run the interactive browser. Returns (action, papers_list)."""
        if not self.papers:
            self.console.print(f"\n[bold]{self.title}[/bold]\n")
            self.console.print("[yellow]No papers found.[/yellow]")
            return None, []

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

        @kb.add("space")
        @kb.add("m")
        def toggle_mark(event):
            """Toggle mark on current paper."""
            if self.selected_index in self.marked_indices:
                self.marked_indices.remove(self.selected_index)
            else:
                self.marked_indices.add(self.selected_index)
            # Move down after marking
            if self.selected_index < len(self.papers) - 1:
                self.selected_index += 1

        @kb.add("a")
        def select_all(event):
            """Select/deselect all papers."""
            if len(self.marked_indices) == len(self.papers):
                self.marked_indices.clear()
            else:
                self.marked_indices = set(range(len(self.papers)))

        @kb.add("enter")
        def select_show(event):
            self.action = Action.SHOW
            self.selected_papers = self._get_selected_papers()
            event.app.exit()

        @kb.add("v")
        def select_view(event):
            self.action = Action.VIEW
            self.selected_papers = self._get_selected_papers()
            event.app.exit()

        @kb.add("b")
        def select_bibtex(event):
            self.action = Action.BIBTEX
            self.selected_papers = self._get_selected_papers()
            event.app.exit()

        @kb.add("d")
        def select_done(event):
            # Only allow if not already in done view
            if self.current_status != "done":
                self.action = Action.DONE
                self.selected_papers = self._get_selected_papers()
                event.app.exit()

        @kb.add("r")
        def select_reading(event):
            # Only allow if not already in reading view
            if self.current_status != "reading":
                self.action = Action.READING
                self.selected_papers = self._get_selected_papers()
                event.app.exit()

        @kb.add("x")
        def select_delete(event):
            self.action = Action.DELETE
            self.selected_papers = self._get_selected_papers()
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
            "marked": "#ffc107",
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

        return self.action, self.selected_papers


def browse_papers(
    status: Optional[str] = None,
    title: str = "Papers",
) -> Tuple[Optional[Action], List[Paper]]:
    """Browse papers interactively."""
    repo = Repository()

    if status:
        papers = repo.list_papers(status=status)
    else:
        papers = repo.list_papers()

    # Keep papers in session for the browser
    browser = PaperBrowser(
        papers,
        title=title,
        show_status=(status is None),
        current_status=status,
    )
    action, selected_papers = browser.run()

    # Get fresh paper references if needed for operations
    fresh_papers = []
    for paper in selected_papers:
        fresh = repo.get_paper(paper.id)
        if fresh:
            fresh_papers.append(fresh)

    repo.close()
    return action, fresh_papers


def handle_action(action: Action, papers: List[Paper], console: Console, current_status: Optional[str] = None) -> bool:
    """Handle an action on papers. Returns True to continue browsing."""
    if action == Action.QUIT or not papers:
        return False

    if action == Action.SHOW:
        # Show details for first paper only
        show_paper_details(papers[0], console)
        return True

    if action == Action.VIEW:
        # View first paper only
        view_paper(papers[0], console)
        return False  # Exit after launching viewer

    if action == Action.BIBTEX:
        get_bibtex(papers, console)
        return True

    if action == Action.DONE:
        if current_status == "done":
            console.print("[yellow]Papers are already marked as done.[/yellow]")
            return True
        for paper in papers:
            mark_paper_done(paper, console, batch_mode=len(papers) > 1)
        return True

    if action == Action.READING:
        if current_status == "reading":
            console.print("[yellow]Papers are already in reading list.[/yellow]")
            return True
        for paper in papers:
            move_to_reading(paper, console)
        return True

    if action == Action.DELETE:
        delete_papers(papers, console)
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

    if paper.bibtex:
        console.print(f"\n[blue]BibTeX:[/blue]")
        console.print(f"[dim]{paper.bibtex[:200]}...[/dim]" if len(paper.bibtex) > 200 else f"[dim]{paper.bibtex}[/dim]")

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


def get_bibtex(papers: List[Paper], console: Console) -> None:
    """Get BibTeX for one or more papers."""
    from prompt_toolkit import prompt

    if not papers:
        return

    console.print(f"\n[bold]BibTeX Export[/bold] ({len(papers)} paper{'s' if len(papers) > 1 else ''})")

    bibtex_entries = []
    repo = Repository()

    for paper in papers:
        bibtex = None

        # Check if paper already has bibtex
        if paper.bibtex:
            bibtex = paper.bibtex
            console.print(f"  [green]✓[/green] {paper.title[:50]}... (cached)")
        else:
            # Try to fetch BibTeX
            console.print(f"  [dim]Fetching:[/dim] {paper.title[:50]}...")
            bibtex = fetch_bibtex(paper, console)

            if bibtex:
                # Cache the bibtex in the database
                repo.update_paper(paper.id, bibtex=bibtex)
                console.print(f"  [green]✓[/green] {paper.title[:50]}...")
            else:
                console.print(f"  [yellow]✗[/yellow] {paper.title[:50]}... (not found)")

        if bibtex:
            bibtex_entries.append(bibtex)

    repo.close()

    if not bibtex_entries:
        console.print("\n[yellow]No BibTeX entries found.[/yellow]")
        console.input("[dim]Press Enter to continue...[/dim]")
        return

    # Combine all entries
    combined_bibtex = "\n\n".join(bibtex_entries)

    if len(papers) == 1:
        # Single paper - just display it
        console.print(f"\n[bold]BibTeX:[/bold]")
        console.print(f"[dim]{combined_bibtex}[/dim]")

        # Copy to clipboard option
        copy = prompt("\nCopy to clipboard? (y/N): ")
        if copy.lower() == "y":
            try:
                import subprocess
                import sys
                if sys.platform == "darwin":
                    subprocess.run(["pbcopy"], input=combined_bibtex.encode(), check=True)
                    console.print("[green]Copied to clipboard![/green]")
                elif sys.platform == "win32":
                    subprocess.run(["clip"], input=combined_bibtex.encode(), check=True)
                    console.print("[green]Copied to clipboard![/green]")
                else:
                    # Try xclip on Linux
                    subprocess.run(["xclip", "-selection", "clipboard"], input=combined_bibtex.encode(), check=True)
                    console.print("[green]Copied to clipboard![/green]")
            except Exception as e:
                console.print(f"[yellow]Could not copy to clipboard: {e}[/yellow]")
    else:
        # Multiple papers - ask for output file
        console.print(f"\n[green]Found {len(bibtex_entries)} BibTeX entries.[/green]")
        default_path = "citations.bib"
        output_path = prompt(f"Save to file (default: {default_path}): ") or default_path

        try:
            output_file = Path(output_path).expanduser()
            with open(output_file, "w") as f:
                f.write(combined_bibtex)
            console.print(f"[green]Saved {len(bibtex_entries)} entries to {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving file: {e}[/red]")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def fetch_bibtex(paper: Paper, console: Console) -> Optional[str]:
    """Fetch BibTeX for a paper from various sources."""
    import httpx
    import re
    import time

    # Try DOI first (most reliable)
    if paper.doi:
        bibtex = fetch_bibtex_from_doi(paper.doi)
        if bibtex:
            return validate_and_clean_bibtex(bibtex, paper)

    # Try arXiv
    if paper.arxiv_id:
        bibtex = fetch_bibtex_from_arxiv(paper.arxiv_id, paper)
        if bibtex:
            return bibtex

    # Try Google Scholar search
    bibtex = fetch_bibtex_from_scholar(paper)
    if bibtex:
        return validate_and_clean_bibtex(bibtex, paper)

    # Generate a basic BibTeX entry as fallback
    return generate_basic_bibtex(paper)


def fetch_bibtex_from_doi(doi: str) -> Optional[str]:
    """Fetch BibTeX from DOI using CrossRef."""
    import httpx

    try:
        # Use DOI content negotiation
        headers = {"Accept": "application/x-bibtex"}
        response = httpx.get(
            f"https://doi.org/{doi}",
            headers=headers,
            follow_redirects=True,
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None


def fetch_bibtex_from_arxiv(arxiv_id: str, paper: Paper) -> Optional[str]:
    """Generate BibTeX for an arXiv paper."""
    # arXiv doesn't provide BibTeX directly, so we generate it
    import re

    # Clean arxiv_id
    arxiv_id = arxiv_id.replace("arXiv:", "").strip()

    # Generate citation key from first author and year
    authors = paper.authors or "Unknown"
    first_author = authors.split(",")[0].split()[-1] if authors else "Unknown"

    # Extract year from arxiv_id (format: YYMM.NNNNN or category/YYMMNNN)
    year_match = re.search(r"(\d{2})\d{2}\.", arxiv_id)
    if year_match:
        year = "20" + year_match.group(1)
    else:
        year = "2024"

    cite_key = f"{first_author.lower()}{year}arxiv"

    # Format authors for BibTeX
    author_list = authors.replace(",", " and") if authors else "Unknown"

    bibtex = f"""@article{{{cite_key},
  title={{{paper.title}}},
  author={{{author_list}}},
  journal={{arXiv preprint arXiv:{arxiv_id}}},
  year={{{year}}},
  url={{https://arxiv.org/abs/{arxiv_id}}}
}}"""

    return bibtex


def fetch_bibtex_from_scholar(paper: Paper) -> Optional[str]:
    """Try to fetch BibTeX from Google Scholar."""
    # Note: Google Scholar doesn't have an official API and blocks automated requests
    # This is a best-effort approach using Semantic Scholar instead
    import httpx

    try:
        # Use Semantic Scholar API which is more reliable
        query = paper.title[:100]  # Limit query length
        response = httpx.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "fields": "title,authors,year,venue,externalIds",
                "limit": 1,
            },
            timeout=10.0,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                result = data["data"][0]

                # Check if title matches reasonably well
                if result.get("title", "").lower()[:30] == paper.title.lower()[:30]:
                    # Try to get DOI from external IDs
                    external_ids = result.get("externalIds", {})
                    if external_ids.get("DOI"):
                        return fetch_bibtex_from_doi(external_ids["DOI"])
    except Exception:
        pass

    return None


def validate_and_clean_bibtex(bibtex: str, paper: Paper) -> str:
    """Validate and clean a BibTeX entry."""
    import re

    # Basic validation - check it has required fields
    if not bibtex or "@" not in bibtex:
        return generate_basic_bibtex(paper)

    # Clean up common issues
    bibtex = bibtex.strip()

    # Ensure it ends with }
    if not bibtex.rstrip().endswith("}"):
        bibtex = bibtex.rstrip() + "\n}"

    return bibtex


def generate_basic_bibtex(paper: Paper) -> str:
    """Generate a basic BibTeX entry from paper metadata."""
    import re
    from datetime import datetime

    # Generate citation key
    authors = paper.authors or "Unknown"
    first_author = authors.split(",")[0].split()[-1] if authors else "unknown"
    first_author = re.sub(r"[^a-zA-Z]", "", first_author).lower()

    # Get year from added_at or use current year
    year = paper.added_at.year if paper.added_at else datetime.now().year

    # Create unique key
    title_word = re.sub(r"[^a-zA-Z]", "", paper.title.split()[0]).lower() if paper.title else "paper"
    cite_key = f"{first_author}{year}{title_word}"

    # Format authors
    author_list = authors.replace(",", " and") if authors else "Unknown"

    # Determine entry type
    entry_type = "article"
    if paper.arxiv_id:
        entry_type = "article"

    bibtex = f"""@{entry_type}{{{cite_key},
  title={{{paper.title}}},
  author={{{author_list}}},
  year={{{year}}}"""

    if paper.doi:
        bibtex += f",\n  doi={{{paper.doi}}}"

    if paper.arxiv_id:
        bibtex += f",\n  eprint={{{paper.arxiv_id}}},\n  archivePrefix={{arXiv}}"

    if paper.url:
        bibtex += f",\n  url={{{paper.url}}}"

    bibtex += "\n}"

    return bibtex


def mark_paper_done(paper: Paper, console: Console, batch_mode: bool = False) -> None:
    """Mark a paper as done with concepts."""
    from prompt_toolkit import prompt

    if paper.status == PaperStatus.DONE.value:
        console.print(f"[yellow]Paper #{paper.id} is already marked as done.[/yellow]")
        return

    if not batch_mode:
        console.print(f"\n[bold]Mark as Done:[/bold] {paper.title}")
        concepts_input = prompt("Enter concepts learned (comma-separated): ")

        if not concepts_input.strip():
            console.print("[yellow]No concepts provided. Cancelled.[/yellow]")
            return

        concepts = [c.strip() for c in concepts_input.split(",") if c.strip()]
    else:
        # In batch mode, use empty concepts
        concepts = []
        console.print(f"  [dim]Marking done:[/dim] {paper.title[:50]}...")

    repo = Repository()

    # Generate summary using LLM (skip in batch mode for speed)
    compressed_summary = None
    if not batch_mode:
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

    if not batch_mode:
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


def delete_papers(papers: List[Paper], console: Console) -> None:
    """Delete one or more papers after confirmation."""
    from prompt_toolkit import prompt

    if len(papers) == 1:
        console.print(f"\n[bold red]Delete:[/bold red] {papers[0].title}")
    else:
        console.print(f"\n[bold red]Delete {len(papers)} papers:[/bold red]")
        for p in papers[:5]:
            console.print(f"  - {p.title[:50]}...")
        if len(papers) > 5:
            console.print(f"  ... and {len(papers) - 5} more")

    confirm = prompt("Are you sure? (y/N): ")

    if confirm.lower() != "y":
        console.print("[yellow]Cancelled.[/yellow]")
        return

    repo = Repository()

    for paper in papers:
        # Delete PDF if exists
        if paper.pdf_path:
            from paperstack.storage import LocalStorage
            storage = LocalStorage()
            storage.delete_pdf(paper.pdf_path)

        repo.delete_paper(paper.id)
        console.print(f"  [dim]Deleted:[/dim] #{paper.id}")

    repo.close()

    console.print(f"[green]Deleted {len(papers)} paper{'s' if len(papers) > 1 else ''}.[/green]")


def interactive_loop(
    status: Optional[str] = None,
    title: str = "Papers",
) -> None:
    """Run interactive browser in a loop until quit."""
    console = Console()

    while True:
        action, papers = browse_papers(status=status, title=title)

        if action is None or action == Action.QUIT:
            break

        if papers:
            continue_browsing = handle_action(action, papers, console, current_status=status)
            if not continue_browsing:
                break
