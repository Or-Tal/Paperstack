"""Search commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Search papers")
console = Console()


@app.command("local")
def search_local(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, "--top", "-k", help="Number of results"),
    all_papers: bool = typer.Option(False, "--all", "-a", help="Search all papers, not just done"),
):
    """Semantic search over your completed papers."""
    from paperstack.embeddings import SemanticSearch
    from paperstack.memory import MemoryManager

    console.print(f"[blue]Searching:[/blue] {query}")

    search = SemanticSearch()
    results = search.search(query, top_k=top_k, done_only=not all_papers)

    # Record search in memory
    memory = MemoryManager()
    memory.record_search(query, [{"id": r.paper.id, "title": r.paper.title} for r in results])

    if not results:
        console.print("[yellow]No matching papers found[/yellow]")

        # Suggest similar past searches
        similar = memory.find_similar_searches(query, top_k=3)
        if similar:
            console.print("\n[dim]Similar past searches:[/dim]")
            for s in similar:
                console.print(f"  - {s['query']}")

        raise typer.Exit(0)

    console.print(f"\n[green]Found {len(results)} matching papers:[/green]\n")

    for i, result in enumerate(results, 1):
        paper = result.paper
        score_pct = int(result.score * 100)

        console.print(f"[cyan]#{paper.id}[/cyan] [bold]{paper.title}[/bold]")
        console.print(f"  [dim]Match: {score_pct}%[/dim]")

        if result.summary:
            console.print(f"  {result.summary[:150]}...")
        elif result.matched_content:
            console.print(f"  [dim]{result.matched_content[:150]}...[/dim]")

        if paper.tags:
            console.print(f"  Tags: {', '.join(paper.tags)}")

        console.print()


@app.command("deep")
def search_deep(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum total results"),
    connected: bool = typer.Option(False, "--connected-papers", "-c", help="Include Connected Papers"),
    sources: list[str] = typer.Option(
        None, "--source", "-s", help="Sources to search (semantic_scholar, arxiv, crossref)"
    ),
):
    """Deep external search across Semantic Scholar, arXiv, and CrossRef."""
    from paperstack.db import Repository
    from paperstack.embeddings import SemanticSearch
    from paperstack.memory import MemoryManager
    from paperstack.search import SearchAggregator

    console.print(f"[blue]Deep search:[/blue] {query}")

    # Step 1: Search local done list first
    console.print("\n[dim]Step 1: Checking your library...[/dim]")
    search = SemanticSearch()
    local_results = search.search(query, top_k=5, done_only=True)

    if local_results:
        console.print(f"\n[green]Related papers in your library:[/green]")
        for r in local_results[:3]:
            console.print(f"  - #{r.paper.id}: {r.paper.title[:60]}...")
        console.print()

    # Step 2: External search
    console.print("[dim]Step 2: Searching external sources...[/dim]")
    aggregator = SearchAggregator()

    search_sources = sources if sources else ["semantic_scholar", "arxiv", "crossref"]
    results = aggregator.search(query, max_results=limit, sources=search_sources)

    if not results:
        console.print("[yellow]No external results found[/yellow]")
        raise typer.Exit(0)

    # Record in memory
    memory = MemoryManager()
    session_id = memory.start_session()
    memory.record_step(session_id, "deep_search", query, f"Found {len(results)} results")
    memory.record_search(
        query,
        [{"title": r.title, "doi": r.doi, "source": r.source} for r in results[:10]],
    )

    # Paginate results
    page = 1
    per_page = 5

    while True:
        start = (page - 1) * per_page
        end = start + per_page
        page_results = results[start:end]

        if not page_results:
            console.print("[yellow]No more results[/yellow]")
            break

        console.print(f"\n[bold]Results (page {page}, showing {start + 1}-{min(end, len(results))} of {len(results)}):[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", width=50)
        table.add_column("Year", width=6)
        table.add_column("Cite", width=6)
        table.add_column("Source", width=10)

        for i, paper in enumerate(page_results, start + 1):
            table.add_row(
                str(i),
                paper.title[:48] + "..." if len(paper.title) > 48 else paper.title,
                str(paper.year) if paper.year else "-",
                str(paper.citation_count) if paper.citation_count else "-",
                paper.source,
            )

        console.print(table)

        # Show options
        console.print("\n[dim]Commands: (n)ext, (p)rev, (a)dd #, (s)how #, (b)ibtex #, (q)uit[/dim]")
        cmd = typer.prompt("Command", default="n")

        if cmd.lower() == "q":
            break
        elif cmd.lower() == "n":
            if end < len(results):
                page += 1
            else:
                console.print("[yellow]No more results[/yellow]")
        elif cmd.lower() == "p":
            if page > 1:
                page -= 1
        elif cmd.lower().startswith("s"):
            try:
                idx = int(cmd[1:].strip()) - 1
                if 0 <= idx < len(results):
                    paper = results[idx]
                    console.print(Panel(
                        f"[bold]{paper.title}[/bold]\n\n"
                        f"Authors: {', '.join(paper.authors[:5])}\n"
                        f"Year: {paper.year or 'N/A'}\n"
                        f"Venue: {paper.venue or 'N/A'}\n"
                        f"Citations: {paper.citation_count or 'N/A'}\n"
                        f"DOI: {paper.doi or 'N/A'}\n"
                        f"arXiv: {paper.arxiv_id or 'N/A'}\n\n"
                        f"Abstract:\n{paper.abstract[:500] if paper.abstract else 'N/A'}...",
                        title=f"Paper #{idx + 1}"
                    ))
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")
        elif cmd.lower().startswith("a"):
            try:
                idx = int(cmd[1:].strip()) - 1
                if 0 <= idx < len(results):
                    paper = results[idx]
                    repo = Repository()

                    added = repo.add_paper(
                        url=paper.url or f"search:{paper.title[:50]}",
                        title=paper.title,
                        authors=", ".join(paper.authors),
                        abstract=paper.abstract,
                        doi=paper.doi,
                        arxiv_id=paper.arxiv_id,
                    )
                    repo.close()
                    console.print(f"[green]Added as paper #{added.id}[/green]")

                    memory.record_step(session_id, "add_paper", None, f"Added: {paper.title}")
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")
        elif cmd.lower().startswith("b"):
            try:
                idx = int(cmd[1:].strip()) - 1
                if 0 <= idx < len(results):
                    paper = results[idx]
                    bibtex = aggregator.get_bibtex(paper)
                    if bibtex:
                        console.print(f"\n```bibtex\n{bibtex}\n```\n")
                    else:
                        console.print("[yellow]BibTeX not available[/yellow]")
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")


@app.command("agent")
def search_agent(
    query: str = typer.Argument(..., help="Initial search query"),
):
    """Agentic search with chat-based refinement."""
    from paperstack.config import get_settings
    from paperstack.embeddings import SemanticSearch
    from paperstack.memory import MemoryManager

    settings = get_settings()

    from paperstack.llm import get_llm_client

    console.print(f"[blue]Starting agentic search:[/blue] {query}")
    console.print("[dim]Type 'quit' to exit, or refine your search with natural language[/dim]\n")

    search = SemanticSearch()
    memory = MemoryManager()
    client = get_llm_client()

    session_id = memory.start_session()
    current_query = query
    messages = []

    while True:
        # Perform search
        memory.record_step(session_id, "search", current_query)
        results = search.search(current_query, top_k=5)

        if results:
            console.print(f"\n[green]Found {len(results)} matching papers:[/green]\n")
            results_for_llm = []

            for i, r in enumerate(results, 1):
                console.print(f"[cyan]{i}.[/cyan] {r.paper.title}")
                console.print(f"   [dim]Score: {int(r.score * 100)}%[/dim]")
                if r.summary:
                    console.print(f"   {r.summary[:100]}...")
                console.print()

                results_for_llm.append({
                    "title": r.paper.title,
                    "summary": r.summary or r.matched_content,
                    "score": r.score,
                })

            # Get LLM explanation
            explanation = client.explain_search_results(current_query, results_for_llm)
            console.print(f"[blue]Analysis:[/blue] {explanation}\n")

        else:
            console.print("[yellow]No matching papers found[/yellow]\n")

        # Get user input
        user_input = typer.prompt("Refine search (or 'quit')")

        if user_input.lower() in ("quit", "q", "exit"):
            console.print("[dim]Ending search session[/dim]")
            break

        # Refine query using LLM
        memory.record_step(session_id, "refine", user_input)
        current_query = client.refine_search_query(current_query, user_input)
        console.print(f"[dim]Refined query: {current_query}[/dim]")
