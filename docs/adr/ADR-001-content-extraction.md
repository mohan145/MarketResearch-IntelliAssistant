# ADR-001: Content Extraction Strategy (Trafilatura vs BeautifulSoup)

**Date:** 2026-06-13  
**Status:** Accepted  
**Author:** Claude + Mohan Krishna Kosetti

---

## Problem

We need to extract clean editorial text from 3-5 user-provided URLs (blogs, announcement pages, articles) to pass to an LLM for summarization. The extraction must:
1. Remove boilerplate (navigation, footers, ads, comments)
2. Preserve article structure (titles, paragraphs, lists)
3. Work reliably across different website layouts
4. Be maintainable without per-site tuning

## Options Considered

### Option 1: Trafilatura (Chosen)
- **Library:** `trafilatura` (purpose-built for editorial text extraction)
- **Approach:** ML heuristics trained on thousands of sites
- **Code:** Single function call, 3 lines
- **Accuracy:** ~90% on real articles

**Pros:**
- Works across sites without tuning (heuristics handle layout variation)
- Returns structured metadata (title, author, publish_date)
- Minimal boilerplate in output (built-in cleanup)
- Fast (~100ms per page)
- Handles JavaScript-rendered content (basic)

**Cons:**
- Adds dependency (`trafilatura`)
- Black-box behavior (hard to debug if extraction fails)
- Not customizable per-site

### Option 2: BeautifulSoup (Rejected)
- **Library:** `beautifulsoup4` (generic HTML parser)
- **Approach:** Manual CSS selectors + text extraction
- **Code:** 30+ lines per implementation
- **Accuracy:** Depends on CSS selectors

**Pros:**
- Fine-grained control over extraction
- Familiar to Python developers
- Works for structured data (not just articles)

**Cons:**
- Requires site-specific CSS selectors
- Breaks when sites redesign HTML
- Manual cleanup needed (remove extra whitespace, tags)
- 10-30x more code than trafilatura
- Each new site requires investigation + updates

### Option 3: Hybrid (BeautifulSoup + Trafilatura fallback)
- **Approach:** Try BeautifulSoup first, fall back to trafilatura if fails
- **Code:** 50+ lines
- **Accuracy:** Depends on implementation

**Pros:**
- Flexibility for known sites
- Fallback safety

**Cons:**
- Maintenance burden (two codepaths)
- Trafilatura alone is sufficient for this use case

---

## Decision

**Use Trafilatura with graceful degradation.**

### Implementation
1. **Primary:** `trafilatura.extract(html)` extracts clean text + metadata
2. **Fallback:** If trafilatura returns `None` (e.g., single-page app), strip HTML tags + basic cleanup
3. **Quality gate:** Reject content < 50 words (likely extraction failure)

### Data Model
```python
ExtractedContent = {
    "url": "https://openai.com/blog/...",
    "title": "Article Title",       # from trafilatura metadata
    "author": "John Doe",           # from trafilatura metadata
    "publish_date": "2024-06-13",   # from trafilatura metadata
    "text": "Clean article text...",
    "word_count": 1240
}
```

### Rationale
- **Scope:** 3-5 URLs are small dataset; no need for per-site tuning
- **Reliability:** Trafilatura's heuristics generalize across layouts
- **Maintainability:** Single codepath, no site-specific rules
- **Cost:** ~40KB dependency, trivial for this app
- **Fallback:** If extraction fails, we log + alert, don't crash

---

## Citation Tracking

Content extraction preserves source URL + metadata for citation:
- **Every extracted text chunk** includes source URL
- **LLM receives context tags:** `[URL: ... | TITLE: ... | TEXT: ...]`
- **Judge validates claims** against original source text (no lossy retrieval)

This is **not RAG** (no vector DB, no semantic retrieval) — it's direct context passing with source attribution.

---

## Future Considerations

### If requirements change to:
- **Scrape non-article content** (product listings, tables) → Switch to BeautifulSoup for those routes
- **Scale to 100+ URLs** → Add vector DB + semantic chunking (true RAG)
- **Per-site customization needed** → Extend trafilatura config or add BeautifulSoup rules per domain

### Monitoring
- Log extraction failures by URL (alert on > 10% failure rate)
- Track average word_count per extraction (alert if unexpectedly low)
- Monitor trafilatura library updates (security patches)

---

## References
- Trafilatura: https://trafilatura.readthedocs.io/
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/
- Editorial text extraction benchmark: https://github.com/adbar/trafilatura#benchmarks