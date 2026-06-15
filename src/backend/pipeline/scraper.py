import logging
from datetime import datetime
from dataclasses import dataclass

import httpx
import trafilatura

logger = logging.getLogger(__name__)


class ContentTooShortError(Exception):
    """Raised when extracted content is too short to be useful."""

    pass


@dataclass
class FetchResult:
    """Result of fetching a URL."""

    url: str
    status_code: int
    html: str | None
    error: str | None
    fetched_at: datetime

    def is_success(self) -> bool:
        return self.status_code == 200 and self.html is not None


@dataclass
class ExtractedContent:
    """Extracted article content with metadata."""

    url: str
    title: str | None
    author: str | None
    publish_date: str | None
    text: str
    word_count: int


@dataclass
class ScrapeResult:
    """Result of scraping a single URL (fetch + extraction)."""

    url: str
    fetch_result: FetchResult
    extracted_content: ExtractedContent | None
    error: str | None

    def is_success(self) -> bool:
        return self.error is None and self.extracted_content is not None


def fetch_url(url: str, timeout: int = 15) -> FetchResult:
    """Fetch URL with automatic retry on transient errors.

    Uses httpx with built-in retry transport: 3 attempts with exponential backoff.
    Returns FetchResult with status code and HTML (or error message).
    """
    try:
        # httpx.HTTPTransport(retries=3) handles connection failures, timeouts
        transport = httpx.HTTPTransport(retries=3)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        client = httpx.Client(transport=transport, timeout=timeout, headers=headers)

        response = client.get(url, follow_redirects=True)
        response.raise_for_status()

        return FetchResult(
            url=url,
            status_code=response.status_code,
            html=response.text,
            error=None,
            fetched_at=datetime.utcnow(),
        )

    except httpx.TimeoutException:
        return FetchResult(
            url=url,
            status_code=0,
            html=None,
            error=f"Timeout after {timeout}s",
            fetched_at=datetime.utcnow(),
        )

    except httpx.HTTPStatusError as e:
        return FetchResult(
            url=url,
            status_code=e.response.status_code,
            html=None,
            error=f"HTTP {e.response.status_code}",
            fetched_at=datetime.utcnow(),
        )

    except httpx.RequestError as e:
        return FetchResult(
            url=url,
            status_code=0,
            html=None,
            error=str(e),
            fetched_at=datetime.utcnow(),
        )

    finally:
        client.close()


def extract_content(html: str, url: str) -> ExtractedContent:
    """Extract clean article text from HTML using trafilatura.

    Trafilatura uses ML heuristics to identify the main article content,
    removing boilerplate (nav, footer, ads, comments).

    Raises ContentTooShortError if extracted text is < 50 words.
    Falls back to basic HTML stripping if trafilatura returns None.
    """
    # Primary: trafilatura extraction
    result = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )

    # Fallback: if trafilatura returns None, strip HTML tags
    if result is None:
        try:
            result = trafilatura.extract(
                html,
                favor_recall=False,  # stricter extraction
            )
        except Exception:
            pass

    # If still None, basic HTML cleanup
    if result is None:
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []

            def handle_data(self, data):
                self.text.append(data.strip())

        try:
            parser = TextExtractor()
            parser.feed(html)
            result = " ".join(parser.text)
        except Exception:
            result = ""

    # Extract metadata using trafilatura.extract_with_metadata (trafilatura 2.1.0+)
    title = None
    author = None
    publish_date = None

    if html:
        try:
            text_with_meta = trafilatura.extract_with_metadata(
                html,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
                output_format="python",
            )
            # extract_with_metadata returns a dict with 'text' and 'metadata'
            if isinstance(text_with_meta, dict):
                result = text_with_meta.get("text", result)
                meta = text_with_meta.get("metadata", {})
                title = meta.get("title")
                author = meta.get("author")
                publish_date = meta.get("date")
        except Exception:
            # Fallback to text-only extraction already attempted above
            pass

    text = result.strip() if result else ""
    word_count = len(text.split())

    # Quality gate
    if word_count < 50:
        raise ContentTooShortError(
            f"Extracted content too short ({word_count} words) from {url}"
        )

    return ExtractedContent(
        url=url,
        title=title if title else None,
        author=author if author else None,
        publish_date=publish_date if publish_date else None,
        text=text,
        word_count=word_count,
    )


def scrape_urls(urls: list[str]) -> list[ScrapeResult]:
    """Scrape multiple URLs and return results.

    For each URL:
    1. Fetch HTML
    2. Extract clean text using trafilatura
    3. Return ScrapeResult (success or error details)

    Logs each URL's status at INFO level.
    """
    results = []

    for url in urls:
        try:
            # Step 1: Fetch
            fetch_result = fetch_url(url)
            if not fetch_result.is_success():
                logger.warning(f"Fetch failed for {url}: {fetch_result.error}")
                results.append(
                    ScrapeResult(
                        url=url,
                        fetch_result=fetch_result,
                        extracted_content=None,
                        error=fetch_result.error,
                    )
                )
                continue

            # Step 2: Extract
            try:
                extracted = extract_content(fetch_result.html, url)
                logger.info(
                    f"Scraped {url}: {extracted.word_count} words, title={extracted.title}"
                )
                results.append(
                    ScrapeResult(
                        url=url,
                        fetch_result=fetch_result,
                        extracted_content=extracted,
                        error=None,
                    )
                )

            except ContentTooShortError as e:
                logger.warning(f"Content too short for {url}: {e}")
                results.append(
                    ScrapeResult(
                        url=url,
                        fetch_result=fetch_result,
                        extracted_content=None,
                        error=str(e),
                    )
                )

            except Exception as e:
                logger.error(f"Extraction failed for {url}: {e}")
                results.append(
                    ScrapeResult(
                        url=url,
                        fetch_result=fetch_result,
                        extracted_content=None,
                        error=f"Extraction error: {str(e)}",
                    )
                )

        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            results.append(
                ScrapeResult(
                    url=url,
                    fetch_result=FetchResult(
                        url=url,
                        status_code=0,
                        html=None,
                        error=str(e),
                        fetched_at=datetime.utcnow(),
                    ),
                    extracted_content=None,
                    error=str(e),
                )
            )

    return results