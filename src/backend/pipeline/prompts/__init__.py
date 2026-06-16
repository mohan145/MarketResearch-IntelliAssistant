"""Prompt template loaders.

Prompts are stored as Jinja2 templates (.j2 files) for:
- Separation of concerns (prompts in files, not code)
- Version control (iterate on prompts independently)
- Readability (templates are plain text)
- Reusability (same template works for multiple LLMs)
"""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Load templates from this directory
PROMPT_DIR = Path(__file__).parent
env = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get_template(name: str):
    """Load a Jinja2 template by name.

    Args:
        name: Template filename (e.g., 'summarize.j2', 'judge.j2')

    Returns:
        Jinja2 Template object
    """
    return env.get_template(name)


def render_summarize_prompt(
    competitors: list[str],
    topics: list[str],
    articles: list[dict],
    max_themes: int = 2,
    max_activities: int = 2,
) -> str:
    """Render the summarization prompt.

    Args:
        competitors: List of competitor names
        topics: List of topics to analyze
        articles: List of ExtractedContent (dict-like with url, title, text, etc.)
        max_themes: Maximum number of themes to request (see ADR-005)
        max_activities: Maximum number of competitor activities to request

    Returns:
        Rendered prompt string ready for LLM
    """
    template = get_template("summarize.j2")
    return template.render(
        competitors=competitors,
        topics=topics,
        articles=articles,
        max_themes=max_themes,
        max_activities=max_activities,
    )


def render_judge_prompt(
    claim: str,
    source_text: str,
    source_url: str,
) -> str:
    """Render the hallucination judge prompt.

    Args:
        claim: The claim to verify
        source_text: Full source article text
        source_url: URL of the source

    Returns:
        Rendered prompt string ready for LLM
    """
    template = get_template("judge.j2")
    return template.render(
        claim=claim,
        source_text=source_text,
        source_url=source_url,
    )