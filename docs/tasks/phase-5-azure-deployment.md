# Phase 5 — Azure Deployment + README

## Goal
Containerize the backend, deploy to Azure Container Apps (free consumption tier), deploy frontend to Azure Static Web Apps (free forever), set up CI/CD, and write the full README to satisfy deliverables.

## Checklist

- [ ] **Step 5.1** — Create `infra/Dockerfile`
  - Base: `python:3.11-slim`
  - Multi-stage: `builder` installs deps, `runtime` copies installed packages + src
  - `EXPOSE 8000`
  - `CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- [ ] **Step 5.2** — Create `infra/docker-compose.yml`
  - Service `backend`: builds from Dockerfile, mounts `./data:/app/data`, env from `.env`
  - Service `frontend`: `node:20-alpine`, runs `vite preview` on port 5173
  - Healthcheck on `http://localhost:8000/health`
- [ ] **Step 5.3** — Create `infra/azure/main.bicep`
  - `Microsoft.App/managedEnvironments` — ACA environment
  - `Microsoft.App/containerApps` — FastAPI backend (consumption tier, min replicas = 0)
  - `Microsoft.Storage/storageAccounts` + file share — SQLite volume mount at `/app/data`
  - `Microsoft.ContainerRegistry/registries` — ACR for container images
  - Ingress: external, targetPort 8000
  - Secrets: `GOOGLE_API_KEY`, `SECRET_KEY` as ACA secret refs (never in env vars)
- [ ] **Step 5.4** — Create `infra/azure/parameters.json` with placeholder values
- [ ] **Step 5.5** — Create `.github/workflows/ci.yml`
  - Trigger: push to `main`, PR to `main`
  - Job `lint-test`: ruff, black --check, isort --check, pytest --cov-fail-under=70
  - Job `deploy-backend` (main only, after lint-test): docker build → az acr login → docker push → az containerapp update
  - Job `deploy-frontend` (main only): Azure Static Web Apps Action (official GitHub Action)
  - Secrets: `AZURE_CREDENTIALS`, `ACR_LOGIN_SERVER`, `AZURE_STATIC_WEB_APPS_API_TOKEN`
- [x] **Step 5.6** — Write `README.md` (satisfies all ProblemStatement deliverables)
  - Problem statement section
  - Architecture diagram (ASCII)
  - Tech stack table (frontend, backend, LLM, DB, hosting)
  - Local build & run instructions (backend: uvicorn, frontend: vite dev)
  - Azure deploy instructions (`az deployment group create`)
  - AI tools/models/libraries used (with citations/links)
  - Design decisions summary (link to `docs/PROGRESS.md` Decisions section)
- [ ] **Step 5.7** — Deploy and verify: `curl https://<aca-fqdn>/health` returns `{"status":"ok"}`
- [ ] **Step 5.8** — Update `docs/PROGRESS.md` with live URL

## Key Files
- `infra/Dockerfile`
- `infra/docker-compose.yml`
- `infra/azure/main.bicep`
- `.github/workflows/ci.yml`
- `README.md`

## Deliverables Completed in This Phase
- Live hosted URL
- README with all required sections
- Written design decisions (docs/PROGRESS.md)