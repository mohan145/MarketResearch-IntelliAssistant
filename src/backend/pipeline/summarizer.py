import logging
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from src.backend.pipeline.prompts import render_summarize_prompt
from src.backend.pipeline.scraper import ExtractedContent

logger = logging.getLogger(__name__)


class SourceRef(BaseModel):
    """Reference to a source with excerpt."""

    url: str = Field(..., description="Source URL")
    excerpt: str = Field(..., description="1-2 sentence quote from source")


class Insight(BaseModel):
    """Key theme or trend identified in articles."""

    theme: str = Field(..., description="Theme name (e.g., 'Pricing Strategy Shifts')")
    finding: str = Field(..., description="Specific finding grounded in articles")
    sources: list[SourceRef] = Field(..., description="Sources supporting this insight")


class CompetitorActivity(BaseModel):
    """Activity or announcement by a competitor."""

    competitor: str = Field(..., description="Company name")
    activity: str = Field(..., description="Specific activity or announcement")
    sources: list[SourceRef] = Field(..., description="Sources documenting the activity")


class MarketSummary(BaseModel):
    """Complete market research summary."""

    executive_summary: str = Field(
        ..., description="1-2 paragraph overview of key findings"
    )
    key_themes: list[Insight] = Field(..., description="Key themes and trends identified")
    competitor_activities: list[CompetitorActivity] = Field(
        ..., description="Competitor activities and announcements"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this summary was generated"
    )


def summarize(
    content: list[ExtractedContent],
    competitors: list[str],
    topics: list[str],
    llm: BaseChatModel,
    max_retries: int = 0,
) -> MarketSummary:
    """Summarize market research from extracted articles.

    Uses LangChain chain: prompt | llm | JsonOutputParser

    Args:
        content: List of extracted articles from scraper
        competitors: List of competitor names to analyze
        topics: List of topics to research
        llm: LLM instance (from get_llm())
        max_retries: Number of retries on JSON parse failure

    Returns:
        MarketSummary with themes, competitor activities, sources

    Raises:
        OutputParserException: If JSON parsing fails after retries
        ValueError: If content is empty
    """
    if not content:
        raise ValueError("No content provided for summarization")

    from src.backend.config import get_settings
    cfg = get_settings()

    # Truncate article text — keeps prompt size bounded for speed (see ADR-005)
    articles = [
        {
            "url": c.url,
            "title": c.title,
            "author": c.author,
            "publish_date": c.publish_date,
            "text": c.text[:cfg.pipeline_max_article_chars],
        }
        for c in content
    ]

    # Render prompt using Jinja2 template
    prompt_text = render_summarize_prompt(
        competitors, topics, articles,
        max_themes=cfg.pipeline_max_themes,
        max_activities=cfg.pipeline_max_competitor_activities,
    )
    logger.debug(f"Rendered prompt ({len(prompt_text)} chars)")

    # Create LangChain chain directly with HumanMessage (avoid f-string parsing issues)
    from langchain_core.messages import HumanMessage
    parser = JsonOutputParser(pydantic_object=MarketSummary)

    # Invoke chain with retry logic
    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Summarizing {len(articles)} articles about {', '.join(competitors)}"
            )

            # Call LLM directly with the rendered prompt
            response = llm.invoke([HumanMessage(content=prompt_text)])
            result = parser.parse(response.content)

            # Ensure datetime is set
            if isinstance(result, dict):
                result.setdefault("generated_at", datetime.utcnow())
                result = MarketSummary(**result)
            elif isinstance(result, MarketSummary):
                if not result.generated_at:
                    result.generated_at = datetime.utcnow()

            logger.info(
                f"Summary complete: {len(result.key_themes)} themes, "
                f"{len(result.competitor_activities)} competitor activities"
            )

            return result

        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"Summarization attempt {attempt + 1} failed: {e}. Retrying..."
                )
                # Don't retry - just re-raise to avoid f-string parsing issues
                continue

            else:
                logger.error(f"Summarization failed after {max_retries + 1} attempts")
                raise