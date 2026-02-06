"""Claude Code integration for LLM features without API key.

This module provides LLM functionality by integrating with Claude Code sessions.
When no API key is available, it falls back to an interactive mode where prompts
are displayed for the user to get responses from their Claude Code session.
"""
from __future__ import annotations

import json
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


console = Console()


class ClaudeCodeClient:
    """Client that integrates with Claude Code for LLM features.

    This client displays prompts and accepts responses interactively,
    allowing users to leverage their Claude Code session for LLM tasks.
    """

    def __init__(self):
        self.model = "claude-code"

    def _get_llm_response(self, prompt: str, response_type: str = "text") -> str:
        """Display prompt and get response from user (via Claude Code).

        Args:
            prompt: The prompt to display
            response_type: Expected response type ('text', 'json_array', 'json')

        Returns:
            The user's response
        """
        console.print()
        console.print(Panel(
            prompt,
            title="[bold cyan]Ask Claude Code[/bold cyan]",
            subtitle="Copy this prompt to Claude Code, then paste the response below",
            border_style="cyan"
        ))
        console.print()

        if response_type == "json_array":
            console.print("[dim]Expected format: [\"tag1\", \"tag2\", \"tag3\"][/dim]")

        console.print("[yellow]Paste response (press Enter twice when done):[/yellow]")

        lines = []
        empty_count = 0
        while empty_count < 1:
            try:
                line = input()
                if line == "":
                    empty_count += 1
                else:
                    empty_count = 0
                    lines.append(line)
            except EOFError:
                break

        return "\n".join(lines).strip()

    def generate_tags(self, title: str, abstract: Optional[str] = None) -> list[str]:
        """Generate tags for a paper based on title and abstract."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"

        prompt = f"""Generate 3-7 relevant academic tags for this paper.
Tags should be lowercase, concise (1-3 words each), and capture the main topics, methods, and domains.

{content}

Return ONLY a JSON array of strings, e.g.: ["deep learning", "transformers", "nlp"]"""

        response = self._get_llm_response(prompt, response_type="json_array")

        try:
            # Handle potential markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            # Try to extract anything that looks like a list
            console.print("[yellow]Could not parse response as JSON. Please enter tags manually.[/yellow]")
            manual = Prompt.ask("Enter tags (comma-separated)")
            return [t.strip() for t in manual.split(",") if t.strip()]

    def generate_description(
        self, title: str, abstract: Optional[str] = None, tags: Optional[list[str]] = None
    ) -> str:
        """Generate a brief description of a paper."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"
        if tags:
            content += f"\n\nTags: {', '.join(tags)}"

        prompt = f"""Write a 1-2 sentence description of this academic paper that captures its main contribution and significance. Be concise and focus on what makes this paper notable.

{content}

Return ONLY the description text, no quotes or prefixes."""

        return self._get_llm_response(prompt, response_type="text")

    def generate_compressed_summary(
        self,
        title: str,
        abstract: Optional[str],
        user_concepts: list[str],
        annotations: Optional[list[dict]] = None,
    ) -> str:
        """Generate a compressed summary combining abstract, concepts, and annotations."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"

        content += f"\n\nKey concepts learned by reader: {', '.join(user_concepts)}"

        if annotations:
            highlights = [a["text"] for a in annotations if a.get("type") == "highlight"]
            notes = [a["content"] for a in annotations if a.get("type") == "note" and a.get("content")]

            if highlights:
                content += f"\n\nHighlighted passages: {'; '.join(highlights[:5])}"
            if notes:
                content += f"\n\nReader notes: {'; '.join(notes[:5])}"

        prompt = f"""Create a compressed summary of this paper that will be useful for semantic search later.
The summary should:
1. Capture the main contributions and methods
2. Incorporate the reader's learned concepts
3. Be optimized for retrieval (include key terms)
4. Be 3-5 sentences

{content}

Return ONLY the summary text."""

        return self._get_llm_response(prompt, response_type="text")

    def extract_key_contributions(self, title: str, abstract: Optional[str]) -> str:
        """Extract key contributions from a paper."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"

        prompt = f"""List the 2-4 key contributions of this paper as bullet points.
Be specific and technical where appropriate.

{content}

Return ONLY the bullet points, one per line starting with "- "."""

        return self._get_llm_response(prompt, response_type="text")

    def chat(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        """Send a chat message and get a response."""
        prompt_parts = []
        if system:
            prompt_parts.append(f"System: {system}\n")

        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")

        prompt = "\n\n".join(prompt_parts)
        prompt += "\n\nProvide your response as Assistant:"

        return self._get_llm_response(prompt, response_type="text")

    def refine_search_query(self, original_query: str, feedback: str) -> str:
        """Refine a search query based on user feedback."""
        prompt = f"""Refine this academic search query based on user feedback.

Original query: {original_query}
User feedback: {feedback}

Return ONLY the refined search query, nothing else."""

        return self._get_llm_response(prompt, response_type="text")

    def explain_search_results(
        self, query: str, results: list[dict], context: Optional[str] = None
    ) -> str:
        """Explain search results in context of the query."""
        results_text = "\n".join(
            f"- {r['title']}: {r.get('summary', r.get('abstract', ''))[:200]}"
            for r in results[:5]
        )

        content = f"Query: {query}\n\nResults:\n{results_text}"
        if context:
            content += f"\n\nAdditional context: {context}"

        prompt = f"""Briefly explain how these search results relate to the query.
Highlight the most relevant papers and suggest potential follow-up searches if appropriate.

{content}

Be concise (2-3 sentences)."""

        return self._get_llm_response(prompt, response_type="text")


def get_llm_client():
    """Get the appropriate LLM client based on available configuration.

    Automatically detects Claude Code environment and uses the proxy.
    Falls back to ClaudeCodeClient (interactive) if neither API key nor
    Claude Code environment is available.
    """
    try:
        # Try ClaudeClient first - it auto-detects Claude Code proxy
        from paperstack.llm.claude_client import ClaudeClient
        return ClaudeClient()
    except ValueError:
        # No API key and no Claude Code proxy - use interactive mode
        console.print("[cyan]No API key or Claude Code environment found.[/cyan]")
        console.print("[dim]Using interactive mode - you'll need to provide LLM responses manually.[/dim]")
        return ClaudeCodeClient()
