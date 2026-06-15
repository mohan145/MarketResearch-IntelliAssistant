# ADR-005: Pipeline Performance Tuning

**Date:** 2026-06-15
**Status:** Accepted
**Author:** Mohan Krishna Kosetti

---

## Problem

The end-to-end research pipeline was taking ~3 minutes per run. An evaluator or
demo user cannot wait 3 minutes — it kills the demo experience. The bottleneck
was identified as sequential LLM calls with large payloads.

---

## Root Cause Analysis

The pipeline makes LLM calls in this sequence:

```
1. Summarizer:  1 LLM call  — prompt includes full article text (up to 8000+ chars per article)
2. Judge:       N LLM calls — one per claim × one per source reference
                              e.g. 2 themes × 1 source + 2 activities × 1 source = 4 calls
                              each call includes full source article text again
```

With 2 Wikipedia articles (~8000 chars each) and Haiku (10-15s per call):
- Summarizer: ~15s
- Judge (4 calls × 15s): ~60s
- Scraping + overhead: ~10s
- **Total: ~85-180s observed (~3 minutes worst case)**

Each LLM call is sequential (one must finish before the next starts), so the cost
is additive, not parallel.

---

## Options Considered

### Option 1: Run judge calls in parallel (asyncio.gather)
- **Approach:** Fire all judge LLM calls concurrently using `asyncio.gather`.
- **Pros:** Could cut judge time from N×15s to ~15s total (parallel ceiling).
- **Cons:** The judge currently runs in sync code inside an async generator context.
  Refactoring to async adds significant complexity. Rate limits on Haiku API could
  cause burst failures. Scope risk for a demo.

### Option 2: Reduce payload size + cap call count (chosen)
- **Approach:** Three targeted limits applied before LLM calls:
  1. Truncate article text to `PIPELINE_MAX_ARTICLE_CHARS` (default: 3000) before
     passing to summarizer — reduces prompt size without losing key content.
  2. Truncate source text to `PIPELINE_MAX_SOURCE_CHARS` (default: 2000) before
     each judge call.
  3. Cap judge to `PIPELINE_MAX_JUDGE_CLAIMS` (default: 3) claims total, checking
     only the first N claims from the summary.
  4. Instruct summarizer to return max `PIPELINE_MAX_THEMES` themes and
     `PIPELINE_MAX_COMPETITOR_ACTIVITIES` activities — fewer outputs = fewer judge calls.
- **Pros:** Simple, zero structural change, immediately effective. All limits
  configurable via `.env` — can be raised for accuracy or lowered for speed.
- **Cons:** Truncation means the LLM sees less content — risk of missing insights
  from the tail of long articles. Judge only verifies a subset of claims.

### Option 3: Cache LLM results (Redis / in-memory)
- **Approach:** Cache summarizer output keyed by URL content hash. Same URL run
  again returns cached summary instantly.
- **Pros:** Zero latency on repeat runs of the same URLs.
- **Cons:** Only helps on repeat URLs. First run still slow. Adds Redis dependency
  or memory pressure. Over-engineered for a demo.

### Option 4: Switch to a faster/cheaper model
- **Approach:** Use a model with lower latency (e.g. GPT-4o mini, Gemini Flash).
- **Pros:** Direct latency reduction per call.
- **Cons:** Quality trade-off. Anthropic Haiku is already the fastest Claude model.
  Model choice is a separate config decision (see LLM_MODEL in .env).

---

## Decision

**Option 2 — payload truncation + call count caps, all configurable via `.env`.**

---

## Implementation

All limits live in `src/backend/config.py` as `Settings` fields, readable from `.env`:

| Setting | Default | Effect |
|---|---|---|
| `PIPELINE_MAX_ARTICLE_CHARS` | 3000 | Chars of article text sent to summarizer per article |
| `PIPELINE_MAX_SOURCE_CHARS` | 2000 | Chars of source text sent to each judge call |
| `PIPELINE_MAX_JUDGE_CLAIMS` | 3 | Max sequential judge LLM calls per run |
| `PIPELINE_MAX_THEMES` | 2 | Max themes requested in summarizer prompt |
| `PIPELINE_MAX_COMPETITOR_ACTIVITIES` | 2 | Max competitor activities requested |
| `PIPELINE_HALLUCINATION_THRESHOLD` | 0.95 | Min confidence (0.0–1.0) to flag a verdict as a hallucination. Higher = more liberal (fewer flags). Lower = stricter (more flags). |

Flow after changes:

```
Scraper → article text (e.g. 8000 chars)
         ↓ truncate to PIPELINE_MAX_ARTICLE_CHARS (3000)
Summarizer prompt (smaller, faster)
         ↓ LLM returns max PIPELINE_MAX_THEMES themes + PIPELINE_MAX_COMPETITOR_ACTIVITIES activities
Summary (2 themes, 2 activities = 4 claims max)
         ↓ take first PIPELINE_MAX_JUDGE_CLAIMS (3)
Judge (3 calls max, each with source truncated to PIPELINE_MAX_SOURCE_CHARS)
         ↓
Result
```

---

## Impact

| Metric | Before | After (defaults) |
|---|---|---|
| Summarizer prompt size | 8000–16000 chars | ~6000 chars (2 articles × 3000) |
| Judge calls | 4–8 (unbounded) | Max 3 |
| Source text per judge call | 8000 chars | 2000 chars |
| Total LLM calls | 5–9 | Max 4 (1 summarize + 3 judge) |
| Estimated wall time (Haiku) | 90–180s | ~45–60s |
| Claims verified | All | Top 3 |

---

## Pros and Cons of Chosen Approach

**Pros:**
- Immediate 3–4× speedup with no structural code change
- All limits are `.env` configurable — raise them for a thorough run, lower for demo
- Truncation at 3000 chars still captures the first ~500 words of an article, which
  contains the key facts in most blog posts and news articles (inverted pyramid style)
- Safer than parallelism for a demo — no race conditions, no burst rate limit risk

**Cons:**
- Tail content of long articles (Wikipedia, whitepapers) is dropped. An article
  about Python that mentions a key feature 4000 chars in will miss it.
- Judge only verifies 3 claims — hallucinations in claims 4+ go undetected.
- Output quality is reduced compared to full-text analysis. This is an explicit
  accuracy vs speed trade-off, acceptable for a demo where responsiveness matters more.

---

## Future: Removing These Trade-offs

| Improvement | How |
|---|---|
| Parallel judge calls | Refactor `verify_summary()` to `async`, use `asyncio.gather()` |
| Chunked summarization | Split long articles into chunks, summarize each, merge |
| Streaming summarizer | Stream LLM output token-by-token to show partial results sooner |
| Smart truncation | Use sentence boundary detection instead of hard char cut |
| Raise limits for production | Set `PIPELINE_MAX_ARTICLE_CHARS=8000`, `PIPELINE_MAX_JUDGE_CLAIMS=10` in prod `.env` |

---

## References

- Anthropic Haiku latency benchmarks: ~5-15s per call depending on output length
- Inverted pyramid writing: key facts appear in first 1/3 of most news/blog articles
- `src/backend/config.py` — all tuning settings
- `src/backend/pipeline/summarizer.py` — article truncation
- `src/backend/pipeline/judge.py` — claim cap + source truncation
- `src/backend/pipeline/prompts/summarize.j2` — max_themes / max_activities variables