# Phase 2 — LLM Pipeline

## Goal
Build the LangChain composition layer: plug-and-play LLM factory, research phase, summarizer, and hallucination judge. All chains use `prompt | llm | parser` — no inheritance.

## Checklist

- [x] **Step 2.1** — Implement `src/backend/pipeline/llm.py` + prompt templates
  - `get_llm(provider: str = "google") -> BaseChatModel`
  - Factory dict: `{"google": ChatGoogleGenerativeAI(...), "anthropic": ..., "openai": ...}`
  - Default model: `gemini-1.5-flash`
  - Reads provider from `settings.LLM_PROVIDER` (overridable via env)
- [x] **Step 2.2** — Implement `src/backend/pipeline/summarizer.py`
  - Pydantic output models: `SourceRef`, `Insight`, `CompetitorActivity`, `MarketSummary`
  - `summarize(content, competitors, topics, llm) -> MarketSummary`
  - Chain: `prompt | llm | JsonOutputParser()`
  - Retry once on JSON parse failure with corrective prompt
- [x] **Step 2.3** — Implement `src/backend/pipeline/judge.py`
  - Pydantic model: `JudgeVerdict(claim, supported, confidence, explanation, source_url)`
  - `check_claim(claim, source_text, source_url, llm) -> JudgeVerdict`
  - `verify_summary(summary, source_texts, llm) -> list[JudgeVerdict]`
  - `count_hallucinations(verdicts, confidence_threshold=0.7) -> int`
- [x] **Step 2.4** — Implement `src/backend/pipeline/orchestrator.py`
  - `run_pipeline(urls, competitors, topics) -> PipelineResult`
  - `PipelineResult`: `summary`, `verdicts`, `hallucination_count`, `run_duration_seconds`, `scrape_results`
  - Yields SSE progress events: `scraping`, `researching`, `summarizing`, `judging`, `done`
- [x] **Step 2.5** — Wire SSE into `src/backend/api/research.py`
  - `POST /api/research/run` (via GET query params) — SSE stream, yields progress events
  - `GET /api/research/history` — returns list of past runs (Phase 4 adds DB)
  - `GET /api/research/{id}` — returns single run (Phase 4 adds DB)
  - Router wired into `main.py`
- [ ] **Step 2.6** — Write tests (mock `get_llm()` return value)
  - `test_summarizer.py` — correct parse of fixture JSON response
  - `test_judge.py` — correctly flags unsupported claim
- [ ] **Step 2.7** — Update `docs/PROGRESS.md`

## Phase 2.2-2.4 Complete ✅

Implemented:
- `summarizer.py` — MarketSummary generation with LangChain chain + retry logic
- `judge.py` — Hallucination verification (verify_summary, count_hallucinations)
- `orchestrator.py` — Full pipeline with async SSE events (run_pipeline_async, run_pipeline)

## Key Files
- `src/backend/pipeline/llm.py`
- `src/backend/pipeline/summarizer.py`
- `src/backend/pipeline/judge.py`
- `src/backend/pipeline/orchestrator.py`
- `src/backend/api/research.py`

## Libraries
- `langchain-core` — `BaseChatModel`, `PromptTemplate`, `JsonOutputParser`
- `langchain-google-genai` — `ChatGoogleGenerativeAI`
- `sse-starlette` — Server-Sent Events for FastAPI

## Sample Test URLs
- `https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/`
- `https://mistral.ai/news/mistral-large-2407/`
- `https://www.anthropic.com/news/claude-3-5-sonnet`
- `https://techcrunch.com/category/artificial-intelligence/`
- `https://www.theverge.com/ai-artificial-intelligence`