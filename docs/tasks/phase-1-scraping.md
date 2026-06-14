# Phase 1 — Scraping Layer

## Goal
Build a reliable module that fetches URLs and returns clean text ready for the LLM pipeline.

## Checklist

- [x] **Step 1.1** — Implement `src/backend/pipeline/scraper.py`
  - `fetch_url(url: str, timeout: int = 15) -> FetchResult`
  - `extract_content(html: str, url: str) -> ExtractedContent`
  - `scrape_urls(urls: list[str]) -> list[ScrapeResult]`
  - Use `httpx.HTTPTransport(retries=3)` for retry (no tenacity needed)
  - Use `trafilatura.extract()` for clean text; fallback if returns None
  - Raise `ContentTooShortError` if extracted text < 50 words
- [x] **Step 1.2** — Write `tests/backend/pipeline/test_scraper.py`
  - Test successful fetch + extraction using fixture HTML
  - Test retry on timeout
  - Test `ContentTooShortError` for near-empty content
- [x] **Step 1.3** — Update `docs/PROGRESS.md`

## Phase 1 Complete ✅

All scraping layer implemented:
- `fetch_url()` with httpx retry transport (3 attempts, exponential backoff)
- `extract_content()` with trafilatura (ML-based extraction, fallback to HTML stripping)
- `scrape_urls()` convenience wrapper (logs all outcomes)
- Full test coverage with mocked HTTP responses
- Citation tracking ready: each ExtractedContent includes URL + metadata

## Key Files
- `src/backend/pipeline/scraper.py`
- `tests/backend/pipeline/test_scraper.py`
- `tests/fixtures/sample_article.html`

## Architecture Decisions

See `docs/adr/`:
- **ADR-001:** Use trafilatura (not BeautifulSoup) for reliable cross-site extraction
- **ADR-002:** Direct context passing (not RAG) — all URLs passed to LLM, no vector DB

## Libraries
- `httpx` — HTTP client with built-in retry transport
- `trafilatura` — editorial text extraction (ML-based, works across layouts)