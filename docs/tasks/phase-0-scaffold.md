# Phase 0 — Project Scaffold

## Goal
Establish the full project skeleton: directory layout, tooling config, settings module, and documentation. No business logic — just the foundation every subsequent phase builds on.

## Stack (locked)
- **Frontend:** Vue 3 + Vite + plain CSS + vue-router (3 npm deps only)
- **Backend:** FastAPI + uvicorn + SQLAlchemy + pydantic-settings + httpx + trafilatura + langchain-core + langchain-google-genai + python-jose + passlib
- **LLM:** Google Gemini 1.5 Flash via LangChain composition (`get_llm()` factory)
- **DB:** SQLite via SQLAlchemy
- **Hosting:** Azure Static Web Apps (frontend) + Azure Container Apps consumption tier (backend)

## Target Directory Layout
```
MarketResearch-IntelliAssistant/
├── src/
│   ├── backend/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── research.py
│   │   │   └── auth.py
│   │   └── pipeline/
│   │       ├── __init__.py
│   │       ├── scraper.py
│   │       ├── llm.py
│   │       ├── summarizer.py
│   │       └── judge.py
│   └── frontend/
│       ├── index.html
│       ├── vite.config.ts
│       ├── package.json
│       └── src/
│           ├── main.ts
│           ├── router.ts
│           ├── api.ts
│           ├── style.css
│           └── pages/
│               ├── NewResearch.vue
│               ├── History.vue
│               └── Login.vue
├── tests/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── test_scraper.py
│   │   │   ├── test_summarizer.py
│   │   │   └── test_judge.py
│   │   └── api/
│   │       ├── __init__.py
│   │       └── test_research.py
├── docs/
│   ├── PROGRESS.md
│   └── tasks/
│       ├── phase-0-scaffold.md       ← this file
│       ├── phase-1-scraping.md
│       ├── phase-2-llm-pipeline.md
│       ├── phase-3-frontend.md
│       ├── phase-4-auth-persistence.md
│       ├── phase-5-azure-deployment.md
│       └── phase-6-stretch.md
├── infra/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── azure/
│       ├── main.bicep
│       └── parameters.json
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── .env.example
├── .gitignore
├── CLAUDE.md
├── ProblemStatement.txt
└── README.md
```

## Checklist

- [x] **Step 0.0** — Create `docs/PROGRESS.md` and `docs/tasks/` directory
- [x] **Step 0.1** — Create `docs/tasks/phase-0-scaffold.md` (this file)
- [x] **Step 0.2** — Update `CLAUDE.md` active task pointer to `phase-0-scaffold.md`
- [x] **Step 0.3** — Create `pyproject.toml` (project metadata, dependency groups, tool config: black, isort, ruff, pytest)
- [x] **Step 0.4** — Create `.pre-commit-config.yaml` (black, isort, ruff hooks)
- [x] **Step 0.5** — Create `src/backend/config.py` (pydantic-settings `Settings`: `GOOGLE_API_KEY`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_ORIGINS`, `LOG_LEVEL`)
- [x] **Step 0.6** — Create `src/backend/main.py` (FastAPI app stub: CORS, router registration, health endpoint)
- [x] **Step 0.7** — Create `src/frontend/` scaffold (package.json, vite.config.ts, index.html, main.ts, router.ts, style.css, page stubs)
- [x] **Step 0.8** — Create `.env.example` with all required environment variables
- [x] **Step 0.9** — Create `tests/` directory structure with `__init__.py` files and `conftest.py`
- [x] **Step 0.10** — Create stub task files for Phases 1–6 in `docs/tasks/`
- [x] **Step 0.11** — Final verification: directory structure complete, config ready, all env vars documented

## Phase 0 Complete ✅

All scaffolding done. Project structure locked and ready for Phase 1.

**What was built:**
- Backend: FastAPI app with config, database ORM setup, health endpoint, CORS
- Frontend: Vue 3 SPA with router, API client, authentication forms, lean stylesheet
- Tooling: pyproject.toml with 4 dependency groups, pre-commit hooks, pytest config
- Documentation: 6 phase task files, PROGRESS.md with decisions log
- Environment: .env files for local (SQLite ./data/) and production (Azure File Share)

## Libraries Introduced

| Library | Purpose |
|---|---|
| `fastapi` | API framework |
| `uvicorn` | ASGI server |
| `pydantic-settings` | Typed config from `.env` |
| `black` | Code formatter |
| `isort` | Import sorter |
| `ruff` | Linter |
| `pytest` + `pytest-cov` | Test runner |
| `httpx` (dev) | HTTP client for tests |
| `pre-commit` | Git hooks |