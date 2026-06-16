# Progress Log — Market Research Intelligence Assistant

## Active Task
`docs/tasks/phase-5-azure-deployment.md`

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

**Phase 3 Complete ✅ — Vue Frontend (2026-06-15)**

All 8 steps implemented:
- Step 3.1 ✅ `src/frontend/src/api.ts` — SSE streaming, type interfaces, auth headers
- Step 3.2 ✅ `src/frontend/src/pages/NewResearch.vue` — Tab-based UI (input/progress/results), form validation, SSE event handling
- Step 3.3 ✅ `src/frontend/src/pages/History.vue` — Table view + detail view with report rendering
- Step 3.4 ✅ `src/frontend/src/pages/Login.vue` — Login form wired to `/auth/login`, JWT stored in localStorage
- Step 3.5 ✅ `src/frontend/src/router.ts` — 3 routes with auth guard (disabled for Phase 3 testing)
- Step 3.6 ✅ `src/frontend/src/style.css` — Complete CSS system (variables, layout, cards, forms, badges, responsive)
- Step 3.7 ✅ Frontend dev server running on port 5174, backend on port 8000, proxy configured
- Fixed vite.config proxy port (9000 → 8000)

Frontend fully functional with live SSE progress streaming and full report rendering. Ready for manual testing and Phase 4 auth/persistence.

**Session 3 — Bug Fixes & Integration (2026-06-15)**

Issues fixed:
- **SSE Named Events Not Routing:** EventSource's `addEventListener("result", ...)` wasn't properly catching named events from the backend. Solution: simplified to send ALL events as default messages (no "event:" prefix) and detect type via stage field. Much more reliable across browsers
- **HTTP 403 Blocked Requests:** Added User-Agent header to scraper to avoid bot detection. URLs like openai.com return 403; Mistral and Anthropic URLs work fine
- **Unicode Encoding Error:** Removed checkmark characters (✓) from orchestrator messages — caused encoding errors on Windows cp1252. Changed to plain ASCII messages
- **Mock LLM Fallback:** Working correctly when ANTHROPIC_API_KEY not set — generates realistic demo responses for summarization and judgment

Architecture simplified:
```
Backend: Sends all events as default SSE messages with { stage, message, progress, result? }
         - progress stages: scraping, summarizing, judging
         - terminal stages: done (success), error (failure)
         
Frontend: Single onmessage handler parses all events
         - Detects done/error by stage field
         - Extracts result object for rendering
         - All logic in one clean path
```

End-to-end pipeline verified working:
```
URLs → scraper (with User-Agent header) → extract content
     → summarizer (mock LLM when no key set) → MarketSummary
     → judge (mock LLM) → hallucination verdicts
     → SSE stream (default messages) → frontend detects stage → UI renders results
```

All code changes backward-compatible. Ready for manual testing with browser.

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

---

### Session 4 — Phase 4 Auth + Persistence (2026-06-15)

**What was done:**
- Implemented `src/backend/models.py` — `User` and `ResearchRun` SQLAlchemy models
- Implemented `src/backend/api/auth.py` — `POST /auth/login`, JWT issuance, `get_current_user()` dependency
- Switched from passlib bcrypt to direct `bcrypt` library (passlib wrap-bug on Python 3.11+)
- Demo user seeded in `init_db()` on startup — idempotent, survives restarts
- All research routes protected with `Depends(get_current_user)`
- SSE endpoint uses `?token=` query param (EventSource can't set headers — see ADR-004)
- Research runs saved to SQLite on pipeline completion
- History page wired to `/api/research/history` — returns runs scoped to current user
- Frontend router guard enforced — unauthenticated users redirected to `/login`
- `api.ts` `apiFetch` wrapper auto-redirects on 401
- App.vue navbar reactive via `router.afterEach`

**Phase 4 Complete ✅**

---

### Session 5 — UI Improvements + Performance (2026-06-15/16)

**What was done:**
- Redesigned `NewResearch.vue` — two-column form (competitors+topics | URLs), URL preview chips, per-URL status grid in progress tab, source domain badges on results
- Orchestrator emits per-URL `url_status` events for individual scrape status
- Added `Topics` as separate field (was merged with competitors)
- Performance tuning (ADR-005): article truncation, judge call cap, configurable via `.env`
- Added `PIPELINE_HALLUCINATION_THRESHOLD` — configurable confidence cutoff (default 0.8)
- All LLM model/provider hardcodes removed — fully driven by `.env`
- `LLM_MODEL` startup validation — fails fast with clear message if not set
- LLM cache key includes model name — prevents stale instances on config change
- Google Gemini `max_retries=0` + `QuotaFallbackLLM` wrapper — stops 429 retry loops
- Friendly HTTP error messages in scraper (403, 404, 429, 500, 503)
- `ENABLE_DOCS` flag — controls Swagger availability independent of APP_ENV
- History page fixed — trust score badge, loadError state, empty state with link

**ADRs written:**
- ADR-004: Auth strategy (FastAPI JWT + seeded demo user)
- ADR-005: Pipeline performance tuning

---

### Session 6 — Azure Deployment (2026-06-16)

**What was done:**
- Created `infra/Dockerfile` — multi-stage python:3.11-slim build
- Created `infra/docker-compose.yml` — local container testing
- Created `src/frontend/staticwebapp.config.json` — SPA routing fix
- Created `.github/workflows/deploy.yml` — full CI/CD pipeline
- Provisioned Azure resources (all free tier):
  - Resource group: `market-research-rg` (West US 3)
  - Storage account: `mkintlstore` + File Share `sqlitedata`
  - Container Apps environment: `market-research-env`
  - Container App: `market-research-api`
  - Static Web App: `market-research-ui`
- Switched from `azure/container-apps-deploy-action` to direct `az` CLI in workflow (more reliable env var handling)
- Switched container registry from ACR to ghcr.io (free)
- Fixed image name casing — ghcr.io requires lowercase, used `github.repository_owner`
- Added Docker Buildx setup for GHA cache support

**Live URLs:**
- Frontend: `https://green-river-07505240f.7.azurestaticapps.net`
- Backend: `https://market-research-api.wonderfulwave-7cb4df30.westus3.azurecontainerapps.io`
- Health: `https://market-research-api.wonderfulwave-7cb4df30.westus3.azurecontainerapps.io/health`

**Known limitation:** SQLite File Share volume mount not yet wired — DB resets on container restart. Run history not persistent in production. Fix: mount `sqlitedata` file share to `/app/data` in ACA.

**ADR written:** ADR-006: Azure deployment strategy

**Phase 5 Complete ✅ (deployment done, README complete)**

---

### Session 7 — README (2026-06-16)

**What was done:**
- Step 5.6: Wrote full `README.md` (9 sections: title, live URLs, demo account, architecture diagram, tech stack + decisions, development story + folder structure, local setup guide, ADR summaries, AI tools and models)
- Checked off Step 5.6 in `docs/tasks/phase-5-azure-deployment.md`
- Updated deliverables table in PROGRESS.md — all README rows now complete

All problem statement deliverables satisfied. Project complete through Phase 5.

---

## Deliverables Tracking (from ProblemStatement.txt)

| Deliverable | Status |
|---|---|
| Live hosted URL (Azure) | ✅ https://green-river-07505240f.7.azurestaticapps.net |
| Source code repository (GitHub) | ✅ pushed to main |
| README — problem statement | ✅ README.md §1 |
| README — architecture & tech stack | ✅ README.md §4–5 |
| README — local build & run instructions | ✅ README.md §7 |
| README — AI tools/models/libraries used | ✅ README.md §9 |
| Written explanation of design decisions | ✅ ADRs 001–006 in docs/adr/ |
| Input form (topics + URLs) | ✅ |
| Fetch and process content from URLs | ✅ |
| Research phase on topics/resources | ✅ |
| AI summary grouped by themes | ✅ |
| Source traceability per insight | ✅ |
| Hallucination check (LLM-as-a-judge) | ✅ |
| Authentication | ✅ JWT + demo user |
| Simple persistence (run history) | ✅ SQLite (ephemeral in prod until File Share mounted) |
| Change detection — stretch | ⬜ |
| Simple monitoring — stretch | ⬜ |

---

## Phase Completion Status

| Phase | Status | Completed |
|---|---|---|
| Phase 0 — Scaffold | ✅ Completed | All 11 steps done |
| Phase 1 — Scraping Layer | ✅ Completed | Trafilatura + User-Agent + error handling |
| Phase 2 — LLM Pipeline | ✅ Completed | Summarizer + Judge + Orchestrator |
| Phase 2.5 — API Endpoints | ✅ Completed | SSE streaming wired |
| Phase 3 — Vue Frontend | ✅ Completed | Two-column form, per-URL progress, results |
| Phase 4 — Auth + Persistence | ✅ Completed | JWT, demo user, SQLite history |
| Phase 5 — Azure Deployment | ✅ Completed | Live on Azure, CI/CD via GitHub Actions |
| Phase 6 — Change Detection + Monitoring | ⬜ Stretch | — |