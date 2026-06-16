# ADR-007: LLM-as-a-Judge Design — Constraints, Tradeoffs, and Configurability

**Date:** 2026-06-16
**Status:** Accepted
**Author:** Mohan Krishna Kosetti

---

## Problem

The hallucination detection system (LLM-as-a-judge) needs to verify claims from the
summarizer against source material. The challenge is balancing **accuracy** (thorough
verification) against **latency** (demo usability) and **cost** (free tier API limits).

Three interconnected decisions were made:
1. Which model to use for judging
2. How many claims to verify and at what confidence threshold
3. How to handle URLs that can't be scraped

---

## Decision 1 — Judge Model: Same as Summarizer (Free Lite Model)

### Options Considered

**Option A: Dedicated high-quality judge model (e.g. Claude Sonnet, GPT-4o)**
- **Approach:** Use a larger, more capable model exclusively for judgment — higher
  reasoning quality, better at detecting subtle hallucinations.
- **Pros:** More accurate verdicts, better at nuanced claim verification. A stronger
  model can reason about implicit contradictions, paraphrased claims, and context the
  summarizer may have misread. This is the correct approach for production use.
- **Cons:** Requires a second API key + billing account for the judge provider.
  Cost: ~$3–15 per 1M tokens. Not viable on the free tier used for this demo.

**Option B: Same model as summarizer (chosen for demo)**
- **Approach:** Reuse the same `LLM_MODEL` (currently `gemini-2.5-flash-lite`) for
  both summarization and judgment. Single API key, single billing account.
- **Pros:** Zero extra cost. Simple config — one model setting controls everything.
- **Cons:** Lite models are less reliable at nuanced reasoning. A claim that's
  borderline may be incorrectly verified or incorrectly flagged. More critically,
  the same model that generated a hallucination may also fail to detect it — the
  judge and the summarizer share the same blind spots.

### Decision
**Option B** — single model for both roles, driven entirely by `LLM_MODEL` in `.env`.

This is a **demo-stage constraint**, not the recommended production approach.

### Rationale
For a demo with known, factual source URLs (blog posts, news articles), a lite model
is acceptable. The judge task is structurally simpler than summarization — it's a
binary yes/no against a short text excerpt, not open-ended synthesis.

**Ideal production setup:** Use a dedicated, stronger model for the judge role — for
example Claude Sonnet or GPT-4o — while keeping a faster, cheaper model for
summarization. The judge only runs on a small number of claims (capped at 3 by default),
so the cost increase is modest but the accuracy gain is significant. The architecture
already supports this: `judge.py` accepts any `BaseChatModel` instance, so wiring in
a separate judge model requires only a config addition (`JUDGE_PROVIDER`, `JUDGE_MODEL`)
and a second `get_llm()` call in the orchestrator — no structural change to the pipeline.

---

## Decision 2 — Claim Verification: Capped and Configurable

### The Problem
The naive approach verifies every claim from the summary against every source URL.
With 2 themes × 1 source + 2 activities × 1 source = 4 claims, and each judge call
taking 10–15s on a lite model, this adds 40–60s to the pipeline. With larger
summaries it could be 8–10 calls = 2+ minutes.

### Constraints Applied (all configurable via `.env`)

| Setting | Default | Effect |
|---|---|---|
| `PIPELINE_MAX_JUDGE_CLAIMS` | 3 | Cap total judge LLM calls per run |
| `PIPELINE_MAX_THEMES` | 2 | Limit themes from summarizer → fewer claims generated |
| `PIPELINE_MAX_COMPETITOR_ACTIVITIES` | 2 | Limit activities → fewer claims generated |
| `PIPELINE_HALLUCINATION_THRESHOLD` | 0.8 | Min confidence to flag as hallucination |
| `PIPELINE_MAX_SOURCE_CHARS` | 2000 | Truncate source text per judge call |

### Confidence Threshold Design

The judge LLM returns a `confidence` score (0.0–1.0) alongside `supported: bool`.
A claim is only counted as a **hallucination** if:
- `supported = false` AND
- `confidence > PIPELINE_HALLUCINATION_THRESHOLD`

This two-condition check prevents low-confidence "maybe unsupported" verdicts from
being flagged as definitive hallucinations. Default threshold is `0.8` — the judge
must be 80%+ confident the claim is unsupported before it's flagged.

**Why 0.8 and not higher?**
- `0.95+` — too liberal, almost nothing gets flagged even when clearly wrong
- `0.8` — catches high-confidence hallucinations, ignores uncertain verdicts
- `0.7` — original default, too strict for lite models which tend to express low confidence
- Configurable so evaluators can tune per their tolerance

### Tradeoffs Accepted

| Tradeoff | Impact | Mitigation |
|---|---|---|
| Only top 3 claims verified | Claims 4+ go unchecked | Raise `PIPELINE_MAX_JUDGE_CLAIMS` for thoroughness |
| Lite model less reliable | May miss subtle hallucinations | Swap `LLM_MODEL` for a more capable model |
| Source truncated to 2000 chars | Tail of long articles not checked | Raise `PIPELINE_MAX_SOURCE_CHARS` |
| Sequential calls (not parallel) | Adds latency proportional to claim count | Future: `asyncio.gather()` for parallel calls |

---

## Decision 3 — Unscrapable URLs: Graceful Degradation

### The Problem
Many websites block automated scraping:
- **403 Forbidden** — site detects bot user-agent (e.g. openai.com, many corporate sites)
- **429 Too Many Requests** — rate limited
- **Timeout** — site too slow or unreachable
- **404** — page removed or URL wrong

### Approach: Partial Success, Never Hard Fail

The pipeline uses a **partial success** model:
1. Scrape all URLs independently
2. Collect results — success or failure per URL
3. If **at least one** URL succeeds → continue pipeline with available content
4. If **all URLs fail** → emit error event, stop pipeline cleanly
5. Per-URL status reported to frontend in real time via SSE `url_status` events

The frontend displays each URL with a live status indicator:
- ⏳ Pending (before scrape attempt)
- ✅ Fetched (N words)
- ❌ Failed with friendly message

### Friendly Error Messages

Raw HTTP status codes replaced with human-readable messages:

| HTTP Code | Message shown in UI |
|---|---|
| 403 | "Access denied (403) — site blocks automated access" |
| 404 | "Page not found (404)" |
| 429 | "Rate limited (429) — too many requests" |
| 500 | "Server error (500)" |
| 503 | "Service unavailable (503)" |
| Timeout | "Timed out after 15s — site too slow or unreachable" |

### User-Agent Spoofing

A browser-like User-Agent header is sent with every request to reduce 403 rate:
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
```
This works for most sites. Sites with advanced bot detection (Cloudflare, OpenAI)
still return 403 regardless.

### URLs Known to Work Reliably
- Wikipedia articles
- Mistral AI blog (`mistral.ai/news/`)
- Anthropic blog (`anthropic.com/news/`)
- Most standard news/blog sites without aggressive bot protection

### URLs Known to Block
- `openai.com` — Cloudflare bot protection, always 403
- Corporate sites with WAF (Web Application Firewall)
- Sites requiring JavaScript rendering (SPA content behind JS)

### Future Improvement
- Playwright/Puppeteer headless browser for JS-rendered sites
- Proxy rotation for rate-limited sites
- Sitemap-based URL discovery

---

## Summary of All Constraints and Their Purpose

| Constraint | Default | Reason | Override |
|---|---|---|---|
| Max judge claims | 3 | Prevent 2+ min latency | `PIPELINE_MAX_JUDGE_CLAIMS=10` |
| Max themes | 2 | Fewer outputs = fewer judge calls | `PIPELINE_MAX_THEMES=5` |
| Max activities | 2 | Same as above | `PIPELINE_MAX_COMPETITOR_ACTIVITIES=5` |
| Article truncation | 3000 chars | Keep summarizer prompt small | `PIPELINE_MAX_ARTICLE_CHARS=8000` |
| Source truncation | 2000 chars | Keep judge prompt small | `PIPELINE_MAX_SOURCE_CHARS=5000` |
| Hallucination threshold | 0.8 | Avoid false positives with lite model | `PIPELINE_HALLUCINATION_THRESHOLD=0.95` |
| Single model for judge | `LLM_MODEL` | Cost — no second API key needed | Set `LLM_MODEL` to larger model |

All constraints are in `src/backend/config.py` and overridable via `.env` or
Azure Container Apps environment variables — no code change required.

---

## References

- `src/backend/pipeline/judge.py` — claim verification logic, threshold, claim cap
- `src/backend/pipeline/summarizer.py` — article truncation, max_themes/activities
- `src/backend/pipeline/scraper.py` — User-Agent, friendly error messages
- `src/backend/pipeline/orchestrator.py` — per-URL SSE events, partial success logic
- `src/backend/config.py` — all tuning settings
- ADR-005: Pipeline performance tuning (broader context)