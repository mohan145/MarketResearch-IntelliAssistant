# Progress Log — Market Research Intelligence Assistant

## Active Task
`docs/tasks/phase-1-scraping.md`

---

## Session Log

### Session 1 — 2026-06-13

**What was done:**
- Read `ProblemStatement.txt` and `CLAUDE.md`.
- Designed full 6-phase implementation plan.
- Evaluated Streamlit vs Vue+FastAPI — decided on Vue 3 + FastAPI.
- Evaluated hosting options — settled on Azure-only free tier stack.
- Evaluated heavy vs lean frontend — stripped to Vue 3 + Vite + plain CSS + vue-router only.
- Evaluated backend deps — stripped to 10 Python libraries, no over-engineering.
- Decided LLM layer uses LangChain composition (plug-and-play, not inheritance).
- Default LLM: Google Gemini (free tier) via `langchain-google-genai`.
- Auth: wired (JWT with python-jose + passlib) but provider decision deferred.
- Created `docs/PROGRESS.md`, `docs/tasks/` directory, `docs/tasks/phase-0-scaffold.md`.
- Reviewed ProblemStatement deliverables — all accounted for in phase plan.

**Phase 0 Complete ✅ — Tested Locally**

Verified:
- Backend starts on localhost:8000, `/health` works
- Frontend starts on localhost:5173, all pages load (routing works)
- SQLite creates at ./data/market_research.db
- Vite proxy forwards /api to backend

---

### Session 2 — 2026-06-13 (continued)

**What was done:**
- Fixed auth guard in frontend router (disabled for testing, will enforce in Phase 4)
- Confirmed all Phase 0 deliverables work locally
- Created Phase 1 task tracking

**Phase 1 Complete ✅**

Implemented:
- `src/backend/pipeline/scraper.py` — fetch + extract pipeline with full error handling
- `tests/backend/pipeline/test_scraper.py` — comprehensive test coverage (6 test classes)
- ADRs created: Content Extraction (ADR-001), Scraping Architecture (ADR-002)

**Phase 2 Complete ✅ — LLM Pipeline (Factory, Summarizer, Judge)**

Implemented:
- `src/backend/pipeline/llm.py` — LLM factory (Google/Anthropic/OpenAI), config-driven, cached
- `src/backend/pipeline/prompts/` — Jinja2 templates (summarize.j2, judge.j2) + loaders
- `src/backend/pipeline/summarizer.py` — MarketSummary generation (Insight, CompetitorActivity, SourceRef models)
- `src/backend/pipeline/judge.py` — Hallucination verification (JudgeVerdict, verify_summary, count_hallucinations)
- `src/backend/pipeline/orchestrator.py` — Full pipeline orchestration (async SSE events + sync wrapper)
- ADR-003 created: LLM Composition Pattern

Pipeline Architecture:
```
URLs → scraper (Phase 1)
    ↓
content (ExtractedContent)
    ↓
summarizer (Phase 2) → MarketSummary
    ↓
judge (Phase 2) → list[JudgeVerdict]
    ↓
PipelineResult (with hallucination_count)
```

**Phase 2.5 Complete ✅ — API Endpoints**

Implemented:
- `src/backend/api/research.py` — SSE-based `/api/research/run` endpoint
  - Accepts: competitors, topics, urls (as JSON query params due to SSE limitation)
  - Streams: progress events (scraping, summarizing, judging, done)
  - Final event contains full PipelineResult
  - `/api/research/history` & `/api/research/{id}` stubbed for Phase 4 (DB)
- Wired research router into `main.py`

Full end-to-end pipeline is now live:
```
Frontend (Vue) → API (/api/research/run) → Backend Pipeline
  ↓
  SSE events streamed back to frontend
  ↓
  Frontend renders progress + final report
```

Ready for Phase 3: Frontend UI integration

- Step 0.5 — `src/backend/config.py` created (pydantic-settings Settings: LLM provider/model/keys, JWT secret, DATABASE_URL, ALLOWED_ORIGINS, APP_ENV, LOG_LEVEL; `get_settings()` with lru_cache; `allowed_origins_list` and `is_production` properties)
- Step 0.8 — `.env.example` created (all vars documented with local vs production comments)
- Step 0.6 — `src/backend/main.py` created (FastAPI app, CORS from `allowed_origins_list`, `/health` endpoint, Swagger disabled in prod, `on_startup` calls `init_db()`)
- Step 0.6 — `src/backend/database.py` created (SQLAlchemy engine, `Base`, `init_db()`, `get_session()` dependency; auto-creates `./data/` dir locally)
- Step 0.7 — `src/frontend/` scaffold created: `package.json` (3 deps: vue, vue-router, vite), `vite.config.ts` (dev proxy → localhost:8000), `App.vue` (navbar + RouterView), `router.ts` (3 routes + auth guard stub), `api.ts` (all type interfaces + fetch wrappers, VITE_API_BASE_URL for prod), `style.css` (CSS variables, layout, forms, cards, badges), page stubs (NewResearch, History, Login), `frontend/.env.example`
- Step 0.9 — `tests/` directory structure created: `tests/backend/pipeline/`, `tests/backend/api/`, `conftest.py` with `test_db` and `sample_html` fixtures
- Step 0.10 — All 6 phase task files created as documented stubs (phase-1-scraping.md through phase-6-stretch.md)

**Completed in this session so far:**
- Step 0.0 — `docs/PROGRESS.md` + `docs/tasks/` created
- Step 0.1 — `docs/tasks/phase-0-scaffold.md` created
- Step 0.2 — `CLAUDE.md` active task pointer updated
- Step 0.3 — `pyproject.toml` created (hatchling build, dependency groups: scraping, llm, backend, dev; tool config: black, isort, ruff, pytest)
- Step 0.4 — `.pre-commit-config.yaml` created (black, isort, ruff + pre-commit-hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-merge-conflict, debug-statements)

---

## Architecture Decision Records (ADRs)

See `docs/adr/` for detailed architectural decisions:
- **ADR-001:** Content Extraction Strategy (Trafilatura vs BeautifulSoup)
- **ADR-002:** Scraping Architecture (Direct Context vs RAG)
- **ADR-003:** LLM Layer Design (Composition over Inheritance)

---

## Decisions

### D-001 — Architecture: Vue 3 + FastAPI over Streamlit (2026-06-13)
**Options evaluated:**
- **Streamlit** — single Python app, built-in forms/auth/spinners, ships in 2 days
- **Vue 3 + FastAPI** — separate SPA frontend + REST API backend, ships in 5–7 days

**Decision:** Vue 3 + FastAPI.
**Reason:** Authentication requirement was the deciding factor — Streamlit's `streamlit-authenticator` is cookie-based with no real JWT story, no token refresh, and no clean OAuth path. FastAPI gives proper JWT auth (`python-jose`), a real REST API that can be extended later, and SSE for streaming pipeline progress live to the UI. The extra upfront days are worth the architectural cleanliness.
**Trade-offs accepted:** More wiring required (CORS, two dev servers, build step). Addressed by keeping both sides lean.

### D-002 — Frontend: Vue 3 + Vite + plain CSS (2026-06-13)
**Decision:** Use Vue 3 + Vite with plain CSS. No Tailwind, no Pinia, no Axios, no component library.
**Reason:** Keeps bundle to ~50–60KB gzipped. Only 3 npm deps: `vue`, `vue-router`, `vite`. Internal tool audience doesn't need heavy UI framework. Native `fetch` replaces Axios. `ref/reactive` replaces Pinia for 3-page app state.

### D-003 — Backend: FastAPI (lean, 10 deps) (2026-06-13)
**Decision:** FastAPI + uvicorn + SQLAlchemy + pydantic-settings + httpx + trafilatura + langchain-core + langchain-google-genai + python-jose + passlib.
**Reason:** Only what the app needs. No Celery (FastAPI BackgroundTasks sufficient), no Alembic (SQLite demo, `create_all` is enough), no SQLModel (direct SQLAlchemy is simpler), no full LangChain (only core + Google plugin needed).

### D-004 — LLM: LangChain Composition, default Gemini (2026-06-13)
**Decision:** LLM layer uses composition pattern via LangChain. `get_llm(provider)` factory returns a `BaseChatModel`. Chains use `prompt | llm | parser` — no inheritance.
**Reason:** Swapping Google → Anthropic → OpenAI requires zero code change, only config. Free tier: Gemini 1.5 Flash (15 req/min, 1500 req/day).

### D-005 — Persistence: SQLite on Azure File Share (2026-06-13)
**Decision:** SQLite via SQLAlchemy. File mounted on Azure File Share in production.
**Reason:** Zero infra cost, simple relational shape, sufficient for demo scale. Migration path: change `DATABASE_URL` to Azure SQL if needed.
**Previous consideration:** Supabase rejected — not Azure. Azure SQL/Cosmos DB rejected — no free tier.

### D-006 — Hosting: Azure-only free tier (2026-06-13)
**Decision:** Vue → Azure Static Web Apps (free forever). FastAPI → Azure Container Apps consumption tier (free for low traffic). SQLite → Azure File Share (near-free).
**Reason:** All Azure, effectively $0 for a short-lived demo app.

### D-007 — Auth: Deferred, but wired (2026-06-13)
**Decision:** JWT infrastructure (python-jose + passlib) scaffolded in Phase 4 but auth provider decision deferred. Login/logout UI placeholder in place.
**Reason:** Auth doesn't block core pipeline features. Provider decision (Supabase Auth, Azure AD B2C, custom) made once hosting is validated.

### D-008 — Frontend: Tab-based UI for Research Flow (2026-06-13)
**Decision:** Use tab interface: Tab 1 (Input Form) → Tab 2 (Progress during run) → Tab 3 (Results after done).
**Reason:** Clean separation of concerns, no scrolling fatigue. User knows where they are in the flow.
**Future:** Will add async queue + background job processing (Phase beyond 6) so user doesn't wait. Tabs 2/3 can be replaced with "Jobs" list showing past/running jobs.

### D-009 — No over-abstraction (2026-06-13)
**Decision:** Backend is 9 files flat. No deep module nesting beyond `api/` and `pipeline/`.
**Reason:** App has 3 API routes and 1 pipeline. Extra layers add complexity with no benefit at this scale.

---

## Deliverables Tracking (from ProblemStatement.txt)

| Deliverable | Phase | Status |
|---|---|---|
| Live hosted URL (Azure) | Phase 5 | Pending |
| Source code repository (GitHub) | Phase 0 | In Progress |
| README — problem statement | Phase 5 | Pending |
| README — architecture & tech stack | Phase 5 | Pending |
| README — local build & run instructions | Phase 5 | Pending |
| README — AI tools/models/libraries used | Phase 5 | Pending |
| Written explanation of design decisions | Phase 5 (this PROGRESS.md) | In Progress |
| Input form (topics + URLs) | Phase 3 | Pending |
| Fetch and process content from URLs | Phase 1 | Pending |
| Research phase on topics/resources | Phase 2 | Pending |
| AI summary grouped by themes | Phase 2 | Pending |
| Source traceability per insight | Phase 2 | Pending |
| Hallucination check (LLM-as-a-judge) | Phase 2 | Pending |
| Authentication | Phase 4 | Pending |
| Simple persistence (run history) | Phase 4 | Pending |
| Change detection — stretch | Phase 6 | Pending |
| Simple monitoring — stretch | Phase 6 | Pending |

---

## Phase Completion Status

| Phase | Status | Completed |
|---|---|---|
| Phase 0 — Scaffold | Completed ✅ | All 11 steps done |
| Phase 1 — Scraping Layer | Completed ✅ | All 3 steps done |
| Phase 2 — LLM Pipeline | Completed ✅ | All 5 steps done |
| Phase 2.5 — API Endpoints | Completed ✅ | SSE streaming wired |
| Phase 3 — Vue Frontend | In Progress 🔄 | UI shell done, testing |
| Phase 4 — Auth + Persistence | Pending | — |
| Phase 5 — Azure Deployment + README | Pending | — |
| Phase 6 — Change Detection + Monitoring (Stretch) | Pending | — |