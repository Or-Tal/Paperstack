"""Add command for adding papers."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Add papers to your library")
console = Console()


@app.command()
def url(
    paper_url: str = typer.Argument(..., help="URL of the paper (arXiv, DOI, etc.)"),
    no_tags: bool = typer.Option(False, "--no-tags", help="Skip auto-tagging"),
    no_description: bool = typer.Option(False, "--no-description", help="Skip description generation"),
):
    """Add a paper from URL with auto-extracted metadata."""
    from paperstack.config import get_settings
    from paperstack.db import Repository
    from paperstack.metadata import MetadataExtractor

    console.print(f"[blue]Fetching metadata from:[/blue] {paper_url}")

    # Extract metadata
    extractor = MetadataExtractor()
    metadata = extractor.extract_from_url(paper_url)

    if metadata is None:
        console.print("[red]Could not extract metadata from URL[/red]")
        console.print("Try adding manually with 'paperstack add manual'")
        raise typer.Exit(1)

    console.print(f"[green]Found:[/green] {metadata.title}")

    # Check if paper already exists
    repo = Repository()
    existing = repo.get_paper_by_url(paper_url)
    if existing:
        console.print(f"[yellow]Paper already exists with ID {existing.id}[/yellow]")
        repo.close()
        raise typer.Exit(1)

    # Auto-generate tags and description (uses Claude Code proxy if available)
    tags = []
    description = None
    settings = get_settings()

    if settings.auto_tag and not no_tags:
        try:
            from paperstack.llm import get_llm_client
            console.print("[dim]Generating tags...[/dim]")
            client = get_llm_client()
            tags = client.generate_tags(metadata.title, metadata.abstract)
            console.print(f"[dim]Tags: {', '.join(tags)}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate tags: {e}[/yellow]")

    if settings.auto_description and not no_description:
        try:
            from paperstack.llm import get_llm_client
            console.print("[dim]Generating description...[/dim]")
            client = get_llm_client()
            description = client.generate_description(metadata.title, metadata.abstract, tags)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate description: {e}[/yellow]")

    # Add to database
    paper = repo.add_paper(
        url=paper_url,
        title=metadata.title,
        authors=metadata.authors,
        abstract=metadata.abstract,
        doi=metadata.doi,
        arxiv_id=metadata.arxiv_id,
        bibtex=metadata.bibtex,
        tags=tags,
        description=description,
    )
    paper_id = paper.id
    paper_title = paper.title
    repo.close()

    console.print(f"\n[green]Added paper #{paper_id}:[/green] {paper_title}")
    if tags:
        console.print(f"[blue]Tags:[/blue] {', '.join(tags)}")
    if description:
        console.print(f"[blue]Description:[/blue] {description}")


@app.command()
def pdf(
    paper_id: int = typer.Argument(..., help="Paper ID to attach PDF to"),
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
):
    """Attach a PDF file to an existing paper."""
    from pathlib import Path

    from paperstack.db import Repository
    from paperstack.storage import LocalStorage

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"[red]File not found:[/red] {pdf_path}")
        repo.close()
        raise typer.Exit(1)

    if not pdf_file.suffix.lower() == ".pdf":
        console.print("[yellow]Warning: File does not have .pdf extension[/yellow]")

    # Save PDF
    storage = LocalStorage()
    saved_path = storage.save_pdf(paper_id, pdf_file.read_bytes())

    # Update paper
    repo.update_paper(paper_id, pdf_path=saved_path)
    repo.close()

    console.print(f"[green]Attached PDF to paper #{paper_id}[/green]")


@app.command()
def manual(
    title: str = typer.Option(..., "--title", "-t", help="Paper title"),
    url: str = typer.Option("", "--url", "-u", help="Paper URL"),
    authors: str = typer.Option("", "--authors", "-a", help="Authors (comma-separated)"),
    abstract: str = typer.Option("", "--abstract", help="Abstract"),
    doi: str = typer.Option("", "--doi", help="DOI"),
    arxiv_id: str = typer.Option("", "--arxiv", help="arXiv ID"),
    tags: list[str] = typer.Option([], "--tag", "-g", help="Tags (can be used multiple times)"),
):
    """Add a paper manually with provided metadata."""
    from paperstack.db import Repository

    repo = Repository()

    paper = repo.add_paper(
        url=url or f"manual:{title[:50]}",
        title=title,
        authors=authors or None,
        abstract=abstract or None,
        doi=doi or None,
        arxiv_id=arxiv_id or None,
        tags=tags if tags else None,
    )
    paper_id = paper.id
    paper_title = paper.title
    repo.close()

    console.print(f"[green]Added paper #{paper_id}:[/green] {paper_title}")


@app.command("search")
def search_add(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results"),
):
    """Search for papers and add from results."""
    from paperstack.metadata import MetadataExtractor

    console.print(f"[blue]Searching for:[/blue] {query}")

    extractor = MetadataExtractor()
    results = extractor.search(query, limit=limit)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        raise typer.Exit(0)

    # Display results
    table = Table(title="Search Results")
    table.add_column("#", style="dim")
    table.add_column("Title")
    table.add_column("Year")
    table.add_column("Source")

    for i, paper in enumerate(results, 1):
        table.add_row(
            str(i),
            paper.title[:60] + "..." if len(paper.title) > 60 else paper.title,
            str(paper.year) if paper.year else "-",
            paper.source,
        )

    console.print(table)

    # Ask user which to add
    choice = typer.prompt("Enter number to add (or 'q' to quit)", default="q")
    if choice.lower() == "q":
        raise typer.Exit(0)

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            selected = results[idx]
            # Add the paper
            from paperstack.db import Repository

            repo = Repository()
            paper = repo.add_paper(
                url=selected.url or f"search:{selected.title[:50]}",
                title=selected.title,
                authors=selected.authors,
                abstract=selected.abstract,
                doi=selected.doi,
                arxiv_id=selected.arxiv_id,
                bibtex=selected.bibtex,
            )
            paper_id = paper.id
            paper_title = paper.title
            repo.close()
            console.print(f"[green]Added paper #{paper_id}:[/green] {paper_title}")
        else:
            console.print("[red]Invalid selection[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")
