# Build Status — Market Research Intelligence Assistant

**Last Updated:** 2026-06-13  
**Status:** Phase 2.5 Complete — Backend pipeline ready for testing

---

## What's Built ✅

### Phase 0 — Project Scaffold ✅
- Project structure (src/backend, src/frontend, tests, docs)
- `pyproject.toml` with dependency groups
- `.pre-commit-config.yaml` with linting hooks
- Configuration system (pydantic-settings)
- Database ORM setup (SQLAlchemy)

### Phase 1 — Scraping Layer ✅
- `scraper.py` — fetch URLs + extract clean text
  - httpx with 3-retry transport
  - trafilatura for editorial extraction
  - Fallback to HTML stripping
- `test_scraper.py` — comprehensive test coverage

### Phase 2 — LLM Pipeline ✅
- `llm.py` — LLM factory (Google/Anthropic/OpenAI plug-and-play)
- `prompts/` — Jinja2 templates (summarize.j2, judge.j2)
- `summarizer.py` — MarketSummary generation via LangChain chain
- `judge.py` — Hallucination verification
- `orchestrator.py` — Full pipeline orchestration (async SSE events)
- `api/research.py` — FastAPI endpoints with SSE streaming

### Phase 3 — Frontend (Partial) ✅
- Vue 3 SPA scaffold (3 npm deps only)
- Tab-based UI (Input → Progress → Results)
- `api.ts` — typed API client (ready to call backend)
- `NewResearch.vue` — full UI shell (hooks need wiring)

---

## How to Test Locally

### 1. Install Dependencies

```bash
# Backend
pip install -e ".[backend,dev]"

# Frontend
cd src/frontend
npm install
cd ../..
```

### 2. Get Gemini API Key

Free tier: https://aistudio.google.com/app/apikey

```bash
# Add to .env
GOOGLE_API_KEY=your-key-here
```

### 3. Start Backend

```bash
uvicorn src.backend.main:app --reload
# Visits http://localhost:8000/health → {"status":"ok","env":"local"}
# Swagger docs: http://localhost:8000/docs
```

### 4. Start Frontend

```bash
cd src/frontend
npm run dev
# Visits http://localhost:5173/
```

### 5. Test End-to-End

1. Frontend: Navigate to "New Research"
2. Enter competitors: `OpenAI, Mistral AI`
3. Enter topics: `AI Pricing, Model Releases`
4. Enter URLs (samples below)
5. Click "Run Analysis"
6. Watch Tab 2 (Progress) stream events
7. Tab 3 (Results) shows report when done

#### Sample URLs
- `https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/`
- `https://mistral.ai/news/mistral-large-2407/`
- `https://www.anthropic.com/news/claude-3-5-sonnet`

---

## What's Next

### Phase 3 — Frontend Integration
- [ ] Wire `NewResearch.vue` to `streamResearch()` API call
- [ ] Handle SSE events → update progress
- [ ] Parse final result → render report tabs
- [ ] Error handling + loading states

### Phase 4 — Auth & Persistence
- [ ] Implement JWT auth (`auth.py` router)
- [ ] Add database models (User, ResearchRun)
- [ ] Implement repository CRUD
- [ ] Wire auth guard to routes

### Phase 5 — Azure Deployment
- [ ] Create Dockerfile
- [ ] Create docker-compose.yml (local test)
- [ ] Create Bicep IaC (Azure resources)
- [ ] Set up GitHub Actions CI/CD

### Phase 6 — Stretch Goals
- [ ] Change detection (diff previous runs)
- [ ] Monitoring dashboard

---

## Architecture Overview

```
┌─────────────────────────────────┐
│  Frontend (Vue 3 SPA)           │
│  http://localhost:5173/         │
│                                 │
│  ├─ NewResearch.vue             │
│  ├─ History.vue                 │
│  ├─ Login.vue (Phase 4)         │
│  └─ api.ts (fetch wrapper)      │
└────────────┬────────────────────┘
             │ REST + SSE
             ↓
┌─────────────────────────────────┐
│  FastAPI Backend                │
│  http://localhost:8000/         │
│                                 │
│  ├─ /api/research/run (SSE)     │
│  ├─ /api/research/history       │
│  ├─ /api/research/{id}          │
│  └─ /auth/* (Phase 4)           │
└────────────┬────────────────────┘
             │
      ┌──────┴──────┐
      ↓             ↓
  Pipeline      Database
  ├─ scraper     (SQLite)
  ├─ summarizer  (Phase 4)
  ├─ judge
  └─ orchestrator
```

---

## Technology Stack

| Layer | Tech | Version |
|---|---|---|
| Frontend | Vue 3 | ^3.5.0 |
| Frontend Build | Vite | ^5.4.0 |
| Backend | FastAPI | >=0.115.0 |
| Backend Server | Uvicorn | >=0.30.0 |
| Web Scraping | httpx + trafilatura | >=0.27.0 + >=1.12.0 |
| LLM Framework | LangChain | >=0.3.0 |
| LLM Default | Google Gemini | 1.5-flash (free) |
| Database | SQLAlchemy + SQLite | >=2.0.0 |
| Auth | python-jose + passlib | >=3.3.0 + >=1.7.4 |
| SSE Streaming | sse-starlette | >=2.1.0 |
| Linting | ruff, black, isort | Latest |
| Testing | pytest | >=8.0.0 |

---

## Key Files

```
src/
├── backend/
│   ├── main.py ..................... FastAPI app
│   ├── config.py ................... Settings (pydantic)
│   ├── database.py ................. SQLAlchemy setup
│   ├── api/
│   │   └── research.py ............. SSE endpoints
│   └── pipeline/
│       ├── scraper.py .............. URL fetching + text extraction
│       ├── llm.py .................. LLM factory
│       ├── summarizer.py ........... LLM summary generation
│       ├── judge.py ................ Hallucination checking
│       ├── orchestrator.py ......... Pipeline orchestration
│       └── prompts/
│           ├── summarize.j2 ........ Summary prompt template
│           └── judge.j2 ............ Judge prompt template
└── frontend/
    └── src/
        ├── pages/
        │   ├── NewResearch.vue ..... Research UI (Tab: Input/Progress/Results)
        │   ├── History.vue ......... Past runs (Phase 4)
        │   └── Login.vue ........... Auth form (Phase 4)
        ├── api.ts .................. API client
        ├── router.ts ............... Vue Router
        ├── App.vue ................. Root component
        └── style.css ............... Global styles
```

---

## Environment Variables

See `.env.example` for full reference. Key ones:

```bash
# LLM (required for run)
GOOGLE_API_KEY=your-gemini-key

# App
APP_ENV=local|production
LLM_PROVIDER=google|anthropic|openai
DATABASE_URL=sqlite:///./data/market_research.db
ALLOWED_ORIGINS=http://localhost:5173
```

---

## Development Commands

```bash
# Backend tests
pytest tests/backend/pipeline/

# Backend linting
black src/
isort src/
ruff check src/

# Frontend dev server
cd src/frontend && npm run dev

# Backend dev server
uvicorn src.backend.main:app --reload

# Full local stack (docker)
docker-compose -f infra/docker-compose.yml up
```

---

## Next Session Checklist

- [ ] Get Gemini API key (free: https://aistudio.google.com/app/apikey)
- [ ] Install deps: `pip install -e ".[backend,dev]"` + `cd src/frontend && npm install`
- [ ] Start backend: `uvicorn src.backend.main:app --reload`
- [ ] Start frontend: `npm run dev`
- [ ] Test `/health` endpoint: `http://localhost:8000/health`
- [ ] Test UI loads: `http://localhost:5173/`
- [ ] Wire frontend to API (Phase 3 step 1)