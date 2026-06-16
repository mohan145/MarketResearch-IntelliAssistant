# ADR-006: Azure Deployment Strategy

**Date:** 2026-06-15
**Status:** Accepted — Deployed ✅
**Author:** Mohan Krishna Kosetti

---

## Problem

The application needs to be publicly accessible via a live URL as a required deliverable.
We need to decide the hosting strategy, container registry, CI/CD approach, and how
environment variables and secrets are managed in production — all within free tier limits.

---

## Architecture Decision

```
GitHub Repo
    │
    ├── push to main
    │       │
    │       ▼
    │   GitHub Actions CI/CD
    │       ├── Build Docker image → push to ghcr.io (free)
    │       ├── Deploy backend  → Azure Container Apps
    │       └── Deploy frontend → Azure Static Web Apps
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  AZURE                                              │
│                                                     │
│  ┌──────────────────────┐   ┌───────────────────┐  │
│  │ Azure Static Web Apps│   │ Azure Container   │  │
│  │ (Free tier forever)  │   │ Apps (Consumption)│  │
│  │                      │   │                   │  │
│  │  Vue 3 SPA           │──▶│  FastAPI + Uvicorn│  │
│  │  Built by Vite       │   │  port 8000        │  │
│  │  VITE_API_BASE_URL   │   │                   │  │
│  │  → ACA backend URL   │   └────────┬──────────┘  │
│  └──────────────────────┘            │              │
│                                      │ mounts       │
│                               ┌──────▼──────────┐  │
│                               │ Azure File Share│  │
│                               │ /app/data/      │  │
│                               │ market_research │  │
│                               │ .db (SQLite)    │  │
│                               └─────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Resource Decisions

### Container Registry — GitHub Container Registry (ghcr.io)

**Chosen over Azure Container Registry (ACR) because:**
- ghcr.io is free for public and private repos
- ACR Basic tier costs ~$5/month — unnecessary for a demo
- Integrates natively with GitHub Actions (no extra credentials needed)
- Images are scoped to the GitHub org/user, same place as the code

### Frontend Hosting — Azure Static Web Apps (Free tier)

- Free forever, no expiry
- Serves the Vite-built Vue SPA
- Built-in global CDN
- Custom domain support (free)
- GitHub Actions deployment via official `azure/static-web-apps-deploy` action
- `staticwebapp.config.json` needed to route all paths → `index.html` (SPA routing)

### Backend Hosting — Azure Container Apps (Consumption tier)

- Free monthly grant: 180,000 vCPU-seconds + 360,000 GB-seconds
- Min replicas = 0 (scales to zero when idle — no idle cost)
- External ingress on port 8000, HTTPS automatic
- Secrets stored as ACA secrets (not plain env vars)
- Cold start: ~3-5s on first request after idle (acceptable for demo)

### Database Persistence — Azure File Share

- SQLite file mounted at `/app/data/market_research.db`
- Azure Storage General Purpose v2, LRS, ~$0.02/GB — effectively $0 for a tiny DB
- Without this, SQLite resets on every container restart (ephemeral container filesystem)
- File Share mounted as a volume in ACA container definition

---

## Environment Variables — Production vs Local

### Sensitive (ACA Secrets — never in env vars or code)
```
ANTHROPIC_API_KEY
SECRET_KEY
DEMO_PASSWORD
```

### Non-sensitive (ACA Environment Variables)
```
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
DEMO_EMAIL=demo@example.com
DATABASE_URL=sqlite:////app/data/market_research.db
ALLOWED_ORIGINS=https://<static-web-app>.azurestaticapps.net
APP_ENV=production
LOG_LEVEL=INFO
PIPELINE_MAX_ARTICLE_CHARS=3000
PIPELINE_MAX_SOURCE_CHARS=2000
PIPELINE_MAX_JUDGE_CLAIMS=3
PIPELINE_MAX_THEMES=2
PIPELINE_MAX_COMPETITOR_ACTIVITIES=2
PIPELINE_HALLUCINATION_THRESHOLD=0.8
```

### Frontend Build-time (Azure Static Web Apps application settings)
```
VITE_API_BASE_URL=https://<container-app-name>.<region>.azurecontainerapps.io
```

---

## Code Changes Required Before Deploy

| File | Change | Why |
|---|---|---|
| `infra/Dockerfile` | Create — python:3.11-slim, multi-stage build | Backend must run in container |
| `infra/docker-compose.yml` | Create — local dev parity | Test container locally before push |
| `src/frontend/staticwebapp.config.json` | Create — route all paths to index.html | SPA routing breaks without it |
| `src/frontend/vite.config.ts` | Already reads `VITE_API_BASE_URL` | No change needed |
| `src/backend/config.py` | `DATABASE_URL` default points to `./data/` | Production uses `/app/data/` via env var |
| `.github/workflows/deploy.yml` | Create — build + push image + deploy ACA + deploy SWA | CI/CD |
| `.env.example` | Update with all production vars documented | Onboarding |

---

## Deployment Steps (Manual — first time)

These run once to provision Azure resources. After that, GitHub Actions handles deploys.

```bash
# 1. Create resource group
az group create --name market-research-rg --location eastus

# 2. Create storage account + file share (SQLite persistence)
az storage account create --name marketresearchstorage --resource-group market-research-rg --sku Standard_LRS
az storage share create --name sqlitedata --account-name marketresearchstorage

# 3. Create Container Apps environment with file share mount
az containerapp env create --name market-research-env --resource-group market-research-rg --location eastus

# 4. Create Container App (backend)
az containerapp create \
  --name market-research-api \
  --resource-group market-research-rg \
  --environment market-research-env \
  --image ghcr.io/<github-user>/market-research-api:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --secrets anthropic-key=<key> secret-key=<secret> demo-password=<password> \
  --env-vars \
      LLM_PROVIDER=anthropic \
      LLM_MODEL=claude-haiku-4-5-20251001 \
      APP_ENV=production \
      DEMO_EMAIL=demo@example.com \
      ANTHROPIC_API_KEY=secretref:anthropic-key \
      SECRET_KEY=secretref:secret-key \
      DEMO_PASSWORD=secretref:demo-password

# 5. Create Static Web App (frontend)
az staticwebapp create \
  --name market-research-ui \
  --resource-group market-research-rg \
  --source https://github.com/<user>/<repo> \
  --location eastus2 \
  --branch main \
  --app-location src/frontend \
  --output-location dist
```

---

## GitHub Actions Secrets Required

| Secret | Value |
|---|---|
| `AZURE_CREDENTIALS` | Output of `az ad sp create-for-rbac` |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | From Static Web Apps resource in portal |
| `GHCR_TOKEN` | GitHub PAT with `write:packages` scope |
| `ANTHROPIC_API_KEY` | LLM API key |
| `SECRET_KEY` | JWT signing secret |
| `DEMO_PASSWORD` | Demo user password |

---

## Prerequisites Checklist

- [x] Create Azure account (free tier)
- [x] Create GitHub repository and push code
- [x] Provision resources via Azure Portal + Cloud Shell
- [x] Add GitHub Actions secrets
- [x] Push to `main` — CI/CD deployed successfully

**Live URLs:**
- Frontend: https://green-river-07505240f.7.azurestaticapps.net
- Backend: https://market-research-api.wonderfulwave-7cb4df30.westus3.azurecontainerapps.io
- Health: https://market-research-api.wonderfulwave-7cb4df30.westus3.azurecontainerapps.io/health

**Known gaps:**
- SQLite File Share volume mount not yet wired — DB resets on container restart
  - Fix: `az containerapp env storage set` + YAML volume mount on the container
- `ANTHROPIC_API_KEY` secret not set (using Google only for now)

---

## What Still Needs to Be Built

- [ ] `infra/Dockerfile`
- [ ] `infra/docker-compose.yml`
- [ ] `src/frontend/staticwebapp.config.json`
- [ ] `.github/workflows/deploy.yml`
- [ ] `.env.example` update

---

## Consequences

- No vendor lock-in beyond Azure hosting — app runs identically in Docker locally
- Cold starts on ACA (scale-to-zero) mean first request after idle is slow — acceptable for demo
- SQLite on File Share is not suitable for concurrent writes — acceptable for single demo user
- Upgrade path: swap `DATABASE_URL` to Azure SQL Flexible Server if multi-user concurrency needed

## References

- Azure Container Apps pricing: https://azure.microsoft.com/pricing/details/container-apps/
- Azure Static Web Apps free tier: https://azure.microsoft.com/pricing/details/app-service/static/
- GitHub Container Registry: https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Azure free account: https://azure.microsoft.com/free