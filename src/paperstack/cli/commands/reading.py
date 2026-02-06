"""Reading list commands."""
from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from paperstack.db.models import PaperStatus

app = typer.Typer(help="Manage reading list")
console = Console()


@app.callback(invoke_without_command=True)
def reading_callback(
    ctx: typer.Context,
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Use interactive browser"),
):
    """Browse reading list. Use arrow keys to navigate, press keys for actions."""
    if ctx.invoked_subcommand is not None:
        return

    if interactive:
        from paperstack.cli.browser import interactive_loop
        interactive_loop(status=PaperStatus.READING.value, title="Reading List")
    else:
        # Show simple list
        list_reading(limit=20, verbose=False)


@app.command("list")
def list_reading(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum papers to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show more details"),
):
    """List papers in reading list (non-interactive)."""
    from paperstack.db import Repository

    repo = Repository()
    papers = repo.list_reading()[:limit]
    repo.close()

    if not papers:
        console.print("[yellow]No papers in reading list[/yellow]")
        console.print("Add papers with: paperstack add url <URL>")
        raise typer.Exit(0)

    table = Table(title=f"Reading List ({len(papers)} papers)")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Tags", style="green")
    if verbose:
        table.add_column("Added")

    for paper in papers:
        tags = json.loads(paper.tags) if paper.tags else []
        tags_str = ", ".join(tags[:3])
        if len(tags) > 3:
            tags_str += f" (+{len(tags) - 3})"

        row = [
            str(paper.id),
            paper.title[:50] + "..." if len(paper.title) > 50 else paper.title,
            tags_str,
        ]
        if verbose:
            row.append(paper.added_at.strftime("%Y-%m-%d"))

        table.add_row(*row)

    console.print(table)


@app.command("show")
def show_paper(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to show (optional, uses browser if not provided)"),
):
    """Show detailed information about a paper."""
    if paper_id is None:
        # Launch interactive browser
        from paperstack.cli.browser import browse_papers, show_paper_details, Action

        action, paper = browse_papers(status=PaperStatus.READING.value, title="Select Paper to View")
        if paper and action == Action.SHOW:
            show_paper_details(paper, console)
        return

    from paperstack.db import Repository

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    annotations = repo.get_annotations(paper_id)
    repo.close()

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
    else:
        console.print("[yellow]PDF:[/yellow] Not attached")

    if paper.description:
        console.print(f"\n[blue]Description:[/blue]")
        console.print(f"  {paper.description}")

    if paper.abstract:
        console.print(f"\n[blue]Abstract:[/blue]")
        words = paper.abstract.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 80:
                lines.append("  " + " ".join(current_line))
                current_line = []
        if current_line:
            lines.append("  " + " ".join(current_line))
        console.print("\n".join(lines[:10]))
        if len(lines) > 10:
            console.print(f"  [dim]... ({len(lines) - 10} more lines)[/dim]")

    if annotations:
        console.print(f"\n[blue]Annotations:[/blue] {len(annotations)}")
        for ann in annotations[:5]:
            text = ann.selection_text or ann.content or "Note"
            console.print(f"  - Page {ann.page}: {text[:50]}...")
        if len(annotations) > 5:
            console.print(f"  [dim]... and {len(annotations) - 5} more[/dim]")

    if paper.bibtex:
        console.print(f"\n[blue]BibTeX:[/blue]")
        for line in paper.bibtex.split("\n")[:6]:
            console.print(f"  {line}")
        if len(paper.bibtex.split("\n")) > 6:
            console.print("  ...")


@app.command("remove")
def remove_paper(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to remove (optional, uses browser if not provided)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a paper from the library."""
    if paper_id is None:
        # Launch interactive browser
        from paperstack.cli.browser import browse_papers, delete_paper, Action

        action, paper = browse_papers(title="Select Paper to Remove")
        if paper and action == Action.DELETE:
            delete_paper(paper, console)
        return

    from paperstack.db import Repository
    from paperstack.storage import LocalStorage

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Remove '{paper.title}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            repo.close()
            raise typer.Exit(0)

    # Delete PDF if exists
    if paper.pdf_path:
        storage = LocalStorage()
        storage.delete_pdf(paper.pdf_path)

    repo.delete_paper(paper_id)
    repo.close()

    console.print(f"[green]Removed paper #{paper_id}[/green]")


@app.command("update")
def update_paper(
    paper_id: int = typer.Argument(..., help="Paper ID to update"),
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    tags: list[str] = typer.Option(None, "--tag", "-g", help="New tags"),
    description: str = typer.Option(None, "--description", "-d", help="New description"),
):
    """Update paper metadata."""
    from paperstack.db import Repository

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    updates = {}
    if title:
        updates["title"] = title
    if tags:
        updates["tags"] = tags
    if description:
        updates["description"] = description

    if not updates:
        console.print("[yellow]No updates provided[/yellow]")
        repo.close()
        raise typer.Exit(0)

    repo.update_paper(paper_id, **updates)
    repo.close()

    console.print(f"[green]Updated paper #{paper_id}[/green]")
