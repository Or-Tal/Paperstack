"""Claude API client for tagging, summarization, and chat."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from anthropic import Anthropic

from paperstack.config import get_settings


def _get_claude_code_headers() -> Optional[Dict[str, str]]:
    """Parse Claude Code proxy headers from environment.

    Returns headers dict if running in Claude Code environment, None otherwise.
    """
    custom_headers_str = os.environ.get("ANTHROPIC_CUSTOM_HEADERS", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")

    # Check if we're in a Claude Code environment
    if not base_url or "localhost" not in base_url:
        return None

    headers = {}
    for line in custom_headers_str.split('\n'):
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.strip()] = value.strip()

    return headers if headers else None


class ClaudeClient:
    """Client for Claude API interactions.

    Automatically detects Claude Code environment and uses the local proxy
    for seamless integration without requiring an API key.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.model = model or settings.llm_model

        # Check for Claude Code proxy environment first
        claude_code_headers = _get_claude_code_headers()

        if claude_code_headers:
            # Running in Claude Code - use proxy with dummy key
            self.client = Anthropic(
                api_key="claude-code-proxy",
                default_headers=claude_code_headers
            )
            self._using_proxy = True
        else:
            # Standard mode - require API key
            self.api_key = api_key or settings.anthropic_api_key

            if not self.api_key:
                raise ValueError(
                    "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                    "or configure via paperstack prefs set anthropic_api_key <key>"
                )

            self.client = Anthropic(api_key=self.api_key)
            self._using_proxy = False

    def generate_tags(self, title: str, abstract: Optional[str] = None) -> list[str]:
        """Generate tags for a paper based on title and abstract."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": f"""Generate 3-7 relevant academic tags for this paper.
Tags should be lowercase, concise (1-3 words each), and capture the main topics, methods, and domains.

{content}

Return ONLY a JSON array of strings, e.g.: ["deep learning", "transformers", "nlp"]""",
                }
            ],
        )

        try:
            text = response.content[0].text.strip()
            # Handle potential markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            # Fallback: extract words that look like tags
            return []

    def generate_description(
        self, title: str, abstract: Optional[str] = None, tags: Optional[list[str]] = None
    ) -> str:
        """Generate a brief description of a paper."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"
        if tags:
            content += f"\n\nTags: {', '.join(tags)}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"""Write a 1-2 sentence description of this academic paper that captures its main contribution and significance. Be concise and focus on what makes this paper notable.

{content}

Return ONLY the description text, no quotes or prefixes.""",
                }
            ],
        )

        return response.content[0].text.strip()

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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": f"""Create a compressed summary of this paper that will be useful for semantic search later.
The summary should:
1. Capture the main contributions and methods
2. Incorporate the reader's learned concepts
3. Be optimized for retrieval (include key terms)
4. Be 3-5 sentences

{content}

Return ONLY the summary text.""",
                }
            ],
        )

        return response.content[0].text.strip()

    def extract_key_contributions(self, title: str, abstract: Optional[str]) -> str:
        """Extract key contributions from a paper."""
        content = f"Title: {title}"
        if abstract:
            content += f"\n\nAbstract: {abstract}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": f"""List the 2-4 key contributions of this paper as bullet points.
Be specific and technical where appropriate.

{content}

Return ONLY the bullet points, one per line starting with "- ".""",
                }
            ],
        )

        return response.content[0].text.strip()

    def chat(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        """Send a chat message and get a response."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def refine_search_query(self, original_query: str, feedback: str) -> str:
        """Refine a search query based on user feedback."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""Refine this academic search query based on user feedback.

Original query: {original_query}
User feedback: {feedback}

Return ONLY the refined search query, nothing else.""",
                }
            ],
        )

        return response.content[0].text.strip()

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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": f"""Briefly explain how these search results relate to the query.
Highlight the most relevant papers and suggest potential follow-up searches if appropriate.

{content}

Be concise (2-3 sentences).""",
                }
            ],
        )

        return response.content[0].text.strip()
