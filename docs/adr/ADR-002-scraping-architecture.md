# ADR-002: Scraping Architecture (Direct Context vs RAG)

**Date:** 2026-06-13  
**Status:** Accepted  
**Author:** Claude + Mohan Krishna Kosetti

---

## Problem

We need to fetch and process user-provided URLs for market research. The system must:
1. Handle 3-5 URLs reliably
2. Extract clean text from each
3. Pass content to LLM for summarization
4. Track citations for every claim
5. Validate claims via LLM-as-a-judge

The decision: **how do we organize and pass content to the LLM?**

## Options Considered

### Option 1: Direct Context Passing (Chosen)
- **Approach:** Fetch all URLs → Extract text → Pass ALL text as context to LLM
- **Storage:** No vector DB
- **Retrieval:** None (user provides URLs, we process all)

**Pros:**
- Simple architecture (no embeddings DB)
- Citation tracking straightforward (we have original source text)
- Judge validation accurate (validates against actual source, not retrieved snippets)
- Fast (no embedding/retrieval latency)
- Cost-effective (no vector DB)
- Fits in Claude's 200K context window (3-5 URLs ≈ 10-50K tokens)

**Cons:**
- Doesn't scale beyond ~10 URLs (context window limit)
- No semantic search (judge validates whatever we send, good or bad)
- All text loaded in memory

### Option 2: Retrieval-Augmented Generation (RAG) (Rejected for now)
- **Approach:** Embed all chunks → On summarization, semantic search for relevant chunks → Pass top-k to LLM
- **Storage:** Vector DB (Pinecone, Weaviate, Supabase pgvector)
- **Retrieval:** Semantic similarity search

**Pros:**
- Scales to 100+ URLs
- Can filter by relevance before LLM
- Handles irrelevant content automatically

**Cons:**
- Complex setup (vector DB, embedding model, sync)
- Citation tracking harder (need to track which retrieval result led to which claim)
- Judge validation may miss context (validating against retrieved snippet, not full article)
- Extra latency (embedding + search before LLM call)
- Infrastructure cost (vector DB)

### Option 3: Hybrid (Lazy RAG)
- **Approach:** Direct context for Phase 1-5, add RAG in Phase 6+
- **Migration path:** No code changes needed (API stays same)

**Pros:**
- Start simple, scale later
- Proven approach (start small, add complexity on demand)

**Cons:**
- Requires design foresight (make direct context code easy to swap)

---

## Decision

**Option 1 (Direct Context) as default. Option 3 (Hybrid/Lazy RAG) as migration path.**

### Phase 1-5: Direct Context
```
scrape_urls(urls: list[str]) → list[ExtractedContent]
│
└─ Each ExtractedContent:
   - url: source URL
   - title, author, date: metadata
   - text: clean article text (~1000-5000 words)
   - word_count: validation
```

### LLM receives:
```
[URL: https://openai.com/blog | TITLE: ... | TEXT: Clean article text...]
[URL: https://mistral.ai/news | TITLE: ... | TEXT: Clean article text...]
[URL: https://cohere.com | TITLE: ... | TEXT: Clean article text...]
```

### Judge validates against:
Original source text (100% accurate, no retrieval approximation)

### Phase 6+ Migration: RAG (Optional)
If we need to handle 50+ URLs or have irrelevant content:
1. Add vector DB (Supabase pgvector preferred, stays in Azure ecosystem)
2. Chunk extracted content by paragraph/semantic boundary
3. Embed chunks
4. On summarization: semantic search for "pricing", "partnerships", etc.
5. Pass top-k chunks to LLM instead of all text

**Code change:** Swap `scrape_urls()` return type, LLM context building logic stays conceptually same.

---

## Citation Tracking

### Phase 1-5: Direct Context
- **Every piece of text** knows its source URL
- **Judge validates** against original source
- **Citations:** Simple URL + excerpt mapping

### Phase 6+: RAG
- **Each chunk** embedded with metadata (url, chunk_id)
- **Retrieval result** includes source URL + excerpt
- **Judge validates** against original source (same as now)

**No breaking changes** — citations work same way whether content came from "all text" or "retrieved chunks".

---

## Scalability Limits

| Scenario | Direct Context | RAG |
|---|---|---|
| 3-5 URLs (200-500 words each) | ✅ Perfect | ✅ Works (overkill) |
| 10 URLs (1K words each) | ✅ Still fits (10-50K tokens) | ✅ Works |
| 50+ URLs | ❌ Context window overflow | ✅ Handles via retrieval |
| Very large articles (10K+ words) | ⚠️ Truncate or split | ✅ Natural chunking |

**Current scope:** 3-5 URLs → **Direct context is ideal**.

---

## Implementation Details

### Chunking (if needed for context limit)
```python
# If single URL > 4000 words, split by paragraphs
TextChunk = {
    "url": "https://...",
    "title": "Article Title",
    "chunk_id": 0,           # which chunk of this article
    "text": "First 4K words of article...",
}
```

### Source Attribution
```python
SourceRef = {
    "url": "https://...",
    "excerpt": "OpenAI introduced tiered pricing..."  # 1-2 sentences
}
```

Each insight includes `sources: list[SourceRef]`.

---

## Future Decisions Enabled

This decision makes these choices easy later:
1. **Add semantic filtering:** Easily switch to RAG by changing retrieval logic
2. **Add multi-language:** Still works (trafilatura is language-agnostic)
3. **Add change tracking:** Store extracted content + diff against previous runs
4. **Add caching:** Cache extracted content by URL hash

---

## References
- Claude context window: 200K tokens (as of 2026)
- Trafilatura extraction: ~1K-5K tokens per article
- Vector DB comparison: https://superlinked.com/vector-db-comparison