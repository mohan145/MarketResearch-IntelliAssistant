import logging
import re
import time
from typing import AsyncGenerator

from pydantic import BaseModel

from src.backend.pipeline.judge import JudgeVerdict, verify_summary
from src.backend.pipeline.llm import get_llm_cached
from src.backend.pipeline.scraper import scrape_urls
from src.backend.pipeline.summarizer import MarketSummary, summarize

logger = logging.getLogger(__name__)


def _friendly_llm_error(exc: Exception) -> str:
    """Map raw LLM provider exceptions to short, user-readable messages."""
    msg = str(exc)
    if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg.lower():
        return (
            "The AI model is temporarily overloaded (free-tier demand spike). "
            "Please try again after some time."
        )
    if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower() or "exhausted" in msg.lower():
        return (
            "Free-tier rate limit reached. "
            "Wait a minute and retry, or check your Google AI Studio quota at aistudio.google.com."
        )
    if "401" in msg or "403" in msg or "api_key" in msg.lower() or "api key" in msg.lower():
        return "LLM API key is invalid or missing. Check GOOGLE_API_KEY in .env."
    # Strip raw Python dicts / JSON blobs — keep only the first sentence fragment
    clean = re.split(r"\{|\n", msg)[0].strip().rstrip(".")
    return clean or "LLM call failed. Check your API key and try again."


def _friendly_scrape_error(error: str | None) -> str:
    """Map raw scraper error strings to short, user-readable messages."""
    if not error:
        return "Could not fetch this URL."
    e = error.lower()
    if "403" in e or "forbidden" in e:
        return "Blocked by site (bot protection / Cloudflare). Try a different page from this site."
    if "404" in e or "not found" in e:
        return "Page not found (404). Check the URL is correct and publicly accessible."
    if "429" in e or "too many" in e:
        return "Rate-limited by the site. Wait a few minutes and retry."
    if "timeout" in e or "timed out" in e:
        return "Request timed out. The site may be slow or blocking automated access."
    if "ssl" in e or "certificate" in e:
        return "SSL/certificate error. The site may have an invalid certificate."
    if "no content" in e or "empty" in e or "nothing extracted" in e:
        return "No readable content extracted. The page may be JavaScript-rendered or paywalled."
    if "connection" in e or "network" in e or "refused" in e:
        return "Network error reaching the site. Check the URL and try again."
    return error


class PipelineResult(BaseModel):
    """Complete result of research pipeline execution."""

    summary: MarketSummary
    verdicts: list[JudgeVerdict]
    hallucination_count: int
    run_duration_seconds: float


async def run_pipeline_async(
    urls: list[str],
    competitors: list[str],
    topics: list[str],
    llm_provider: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Run research pipeline with SSE-style progress events.

    Yields progress updates as the pipeline runs, allowing frontend to display
    live status. Final event contains the complete result.

    This is an async generator that yields progress events as dicts:
    - stage: "scraping" | "researching" | "summarizing" | "judging" | "done"
    - message: Human-readable status message
    - progress: 0-100 percentage

    Args:
        urls: List of URLs to research
        competitors: List of competitor names
        topics: List of topics to analyze
        llm_provider: Which LLM to use (google, anthropic, openai)

    Yields:
        Progress event dicts, final event contains PipelineResult

    Example:
        async for event in run_pipeline_async(urls, competitors, topics):
            if event["stage"] == "done":
                result = event["result"]  # PipelineResult
            else:
                print(event["message"])  # Progress update
    """
    start_time = time.time()

    try:
        # Stage 1: Scraping
        yield {
            "stage": "scraping",
            "message": f"Fetching {len(urls)} URLs...",
            "progress": 5,
        }

        scrape_results = scrape_urls(urls)
        successful = [r for r in scrape_results if r.is_success()]

        # Emit per-URL result so frontend can show individual status
        for r in scrape_results:
            if r.is_success():
                yield {
                    "stage": "scraping",
                    "message": f"Fetched {r.url} ({r.extracted_content.word_count} words)",
                    "progress": 10,
                    "url_status": {"url": r.url, "ok": True},
                }
            else:
                friendly_err = _friendly_scrape_error(r.error)
                yield {
                    "stage": "scraping",
                    "message": f"Failed {r.url}: {friendly_err}",
                    "progress": 10,
                    "url_status": {"url": r.url, "ok": False, "error": friendly_err},
                }

        if not successful:
            yield {
                "stage": "error",
                "message": "Failed to scrape any URLs. Check that the URLs are publicly accessible.",
                "progress": 0,
            }
            return

        if len(successful) < len(urls):
            yield {
                "stage": "scraping",
                "message": f"Proceeding with {len(successful)}/{len(urls)} URLs — {len(urls) - len(successful)} failed",
                "progress": 20,
            }
        else:
            yield {
                "stage": "scraping",
                "message": f"All {len(successful)} URLs fetched successfully",
                "progress": 20,
            }

        # Extract content from successful scrapes
        content = [r.extracted_content for r in successful if r.extracted_content]

        # Stage 2: LLM Summarization
        yield {
            "stage": "summarizing",
            "message": "Analyzing content with LLM...",
            "progress": 30,
        }

        try:
            llm = get_llm_cached(llm_provider)
        except RuntimeError as e:
            yield {
                "stage": "error",
                "message": f"LLM not configured: {e}",
                "progress": 0,
            }
            return
        except Exception as e:
            yield {
                "stage": "error",
                "message": _friendly_llm_error(e),
                "progress": 0,
            }
            return

        try:
            summary = summarize(content, competitors, topics, llm)
        except Exception as e:
            yield {
                "stage": "error",
                "message": _friendly_llm_error(e),
                "progress": 0,
            }
            return

        yield {
            "stage": "summarizing",
            "message": f"Generated summary with {len(summary.key_themes)} themes",
            "progress": 60,
        }

        # Stage 3: Hallucination Checking
        yield {
            "stage": "judging",
            "message": "Verifying claims with LLM judge...",
            "progress": 70,
        }

        # Build source text dict for judge
        source_texts = {r.url: r.extracted_content.text for r in successful}

        try:
            verdicts = verify_summary(summary, source_texts, llm)
        except Exception as e:
            yield {
                "stage": "error",
                "message": _friendly_llm_error(e),
                "progress": 0,
            }
            return

        from src.backend.config import get_settings
        threshold = get_settings().pipeline_hallucination_threshold
        hallucination_count = sum(1 for v in verdicts if not v.supported and v.confidence > threshold)

        yield {
            "stage": "judging",
            "message": f"Verified {len(verdicts)} claims ({hallucination_count} issues found)",
            "progress": 90,
        }

        # Stage 4: Done
        duration = time.time() - start_time

        result = PipelineResult(
            summary=summary,
            verdicts=verdicts,
            hallucination_count=hallucination_count,
            run_duration_seconds=duration,
        )

        logger.info(f"Pipeline complete in {duration:.1f}s")

        yield {
            "stage": "done",
            "message": "Analysis complete!",
            "progress": 100,
            "result": result,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Pipeline failed after {duration:.1f}s: {e}")
        yield {
            "stage": "error",
            "message": f"Error: {str(e)}",
            "progress": 0,
        }


def run_pipeline(
    urls: list[str],
    competitors: list[str],
    topics: list[str],
    llm_provider: str | None = None,
) -> PipelineResult:
    """Run research pipeline synchronously (blocking).

    For use in tests or blocking contexts. For API endpoints,
    use run_pipeline_async() with FastAPI BackgroundTasks or @asyncio.

    Args:
        urls: List of URLs to research
        competitors: List of competitor names
        topics: List of topics to analyze
        llm_provider: Which LLM to use (google, anthropic, openai)

    Returns:
        PipelineResult with summary, verdicts, hallucination count

    Raises:
        Various exceptions from scraper, summarizer, or judge modules
    """
    import asyncio

    # Run async pipeline in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = None
        async def collect_result():
            nonlocal result
            async for event in run_pipeline_async(urls, competitors, topics, llm_provider):
                if event["stage"] == "done":
                    result = event["result"]
                elif event["stage"] == "error":
                    raise RuntimeError(event["message"])

        loop.run_until_complete(collect_result())
        if result is None:
            raise RuntimeError("Pipeline completed but no result was generated")
        return result

    finally:
        loop.close()