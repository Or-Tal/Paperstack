"""Done list commands."""
from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from paperstack.db.models import PaperStatus

app = typer.Typer(help="Manage completed papers")
console = Console()


@app.callback(invoke_without_command=True)
def done_callback(
    ctx: typer.Context,
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Use interactive browser"),
):
    """Browse completed papers. Use arrow keys to navigate, press keys for actions."""
    if ctx.invoked_subcommand is not None:
        return

    if interactive:
        from paperstack.cli.browser import interactive_loop
        interactive_loop(status=PaperStatus.DONE.value, title="Completed Papers")
    else:
        # Show simple list
        list_done(limit=20, verbose=False)


@app.command("mark")
def mark_done(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to mark as done (optional, uses browser if not provided)"),
    concepts: list[str] = typer.Option(
        [], "--concepts", "-c", help="Concepts learned (can be used multiple times)"
    ),
    summary: str = typer.Option(None, "--summary", "-s", help="Custom summary"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip LLM summary generation"),
):
    """Mark a paper as done with learned concepts."""
    if paper_id is None:
        # Launch interactive browser to select paper
        from paperstack.cli.browser import browse_papers, mark_paper_done, Action

        action, paper = browse_papers(status=PaperStatus.READING.value, title="Select Paper to Mark Done")
        if paper and action == Action.DONE:
            mark_paper_done(paper, console)
        return

    from paperstack.db import Repository
    from paperstack.embeddings import SemanticSearch

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    if paper.status == "done":
        console.print(f"[yellow]Paper #{paper_id} is already marked as done[/yellow]")
        update = typer.confirm("Update with new concepts?")
        if not update:
            repo.close()
            raise typer.Exit(0)

    # Generate compressed summary using LLM if available
    compressed_summary = summary
    key_contributions = None

    # Try to use LLM unless --no-llm or custom summary provided
    if not summary and not no_llm:
        try:
            from paperstack.llm import get_llm_client

            console.print("[dim]Generating summary...[/dim]")
            client = get_llm_client()

            # Get annotations for context
            annotations = repo.get_annotations(paper_id)
            ann_list = [
                {"type": a.type, "text": a.selection_text, "content": a.content}
                for a in annotations
            ]

            compressed_summary = client.generate_compressed_summary(
                title=paper.title,
                abstract=paper.abstract,
                user_concepts=concepts,
                annotations=ann_list,
            )

            key_contributions = client.extract_key_contributions(
                title=paper.title,
                abstract=paper.abstract,
            )

        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate summary: {e}[/yellow]")

    # Mark as done
    done_entry = repo.mark_done(
        paper_id=paper_id,
        user_concepts=concepts if concepts else None,
        compressed_summary=compressed_summary,
        key_contributions=key_contributions,
    )

    # Index for semantic search
    console.print("[dim]Indexing for search...[/dim]")
    search = SemanticSearch(repo=repo)
    emb_count = search.index_paper(paper_id)

    repo.close()

    console.print(f"\n[green]Marked paper #{paper_id} as done[/green]")
    if concepts:
        console.print(f"[blue]Concepts:[/blue] {', '.join(concepts)}")
    if compressed_summary:
        console.print(f"[blue]Summary:[/blue] {compressed_summary[:200]}...")
    console.print(f"[dim]Created {emb_count} embeddings for search[/dim]")


@app.command("list")
def list_done(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum papers to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show more details"),
):
    """List completed papers (non-interactive)."""
    from paperstack.db import Repository

    repo = Repository()
    papers = repo.list_done()[:limit]

    if not papers:
        console.print("[yellow]No completed papers[/yellow]")
        console.print("Mark papers as done with: paperstack done mark <id> --concepts '...'")
        repo.close()
        raise typer.Exit(0)

    table = Table(title=f"Completed Papers ({len(papers)} papers)")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Concepts", style="green")
    if verbose:
        table.add_column("Completed")

    for paper in papers:
        done_entry = repo.get_done_entry(paper.id)
        concepts = []
        if done_entry and done_entry.user_concepts:
            concepts = json.loads(done_entry.user_concepts)

        concepts_str = ", ".join(concepts[:3])
        if len(concepts) > 3:
            concepts_str += f" (+{len(concepts) - 3})"

        row = [
            str(paper.id),
            paper.title[:45] + "..." if len(paper.title) > 45 else paper.title,
            concepts_str,
        ]
        if verbose and done_entry:
            row.append(done_entry.completed_at.strftime("%Y-%m-%d"))

        table.add_row(*row)

    repo.close()
    console.print(table)


@app.command("show")
def show_done(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to show (optional, uses browser if not provided)"),
):
    """Show detailed done entry for a paper."""
    if paper_id is None:
        # Launch interactive browser
        from paperstack.cli.browser import browse_papers, show_paper_details, Action

        action, paper = browse_papers(status=PaperStatus.DONE.value, title="Select Paper to View")
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

    done_entry = repo.get_done_entry(paper_id)
    if done_entry is None:
        console.print(f"[yellow]Paper #{paper_id} is not marked as done[/yellow]")
        repo.close()
        raise typer.Exit(1)

    concepts = json.loads(done_entry.user_concepts) if done_entry.user_concepts else []

    console.print(f"\n[bold cyan]#{paper.id}[/bold cyan] [bold]{paper.title}[/bold]")
    console.print(f"[dim]Completed: {done_entry.completed_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
    console.print()

    if concepts:
        console.print("[blue]Concepts Learned:[/blue]")
        for concept in concepts:
            console.print(f"  - {concept}")
        console.print()

    if done_entry.compressed_summary:
        console.print("[blue]Summary:[/blue]")
        console.print(f"  {done_entry.compressed_summary}")
        console.print()

    if done_entry.key_contributions:
        console.print("[blue]Key Contributions:[/blue]")
        for line in done_entry.key_contributions.split("\n"):
            if line.strip():
                console.print(f"  {line}")
        console.print()

    if paper.bibtex:
        console.print("[blue]BibTeX:[/blue]")
        console.print(f"```\n{paper.bibtex}\n```")

    repo.close()


@app.command("unmark")
def unmark_done(
    paper_id: Optional[int] = typer.Argument(None, help="Paper ID to unmark (optional, uses browser if not provided)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Move a paper back to reading list."""
    if paper_id is None:
        # Launch interactive browser
        from paperstack.cli.browser import browse_papers, move_to_reading, Action

        action, paper = browse_papers(status=PaperStatus.DONE.value, title="Select Paper to Move Back")
        if paper and action == Action.READING:
            move_to_reading(paper, console)
        return

    from paperstack.db import Repository

    repo = Repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        console.print(f"[red]Paper {paper_id} not found[/red]")
        repo.close()
        raise typer.Exit(1)

    if paper.status != "done":
        console.print(f"[yellow]Paper #{paper_id} is not marked as done[/yellow]")
        repo.close()
        raise typer.Exit(0)

    if not force:
        confirm = typer.confirm(f"Move '{paper.title}' back to reading list?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            repo.close()
            raise typer.Exit(0)

    repo.update_paper(paper_id, status=PaperStatus.READING.value)
    repo.close()

    console.print(f"[green]Moved paper #{paper_id} back to reading list[/green]")
