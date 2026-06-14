# Phase 3 — Vue Frontend

## Goal
Build a lightweight Vue 3 SPA (3 npm deps: vue, vue-router, vite). Three pages: New Research, History, Login placeholder. SSE-driven live progress. Clean, readable UI with plain CSS.

## Checklist

- [ ] **Step 3.1** — Implement `src/frontend/src/api.ts`
  - `runResearch(payload) -> EventSource` — opens SSE stream to `POST /api/research/run`
  - `getHistory() -> Promise<Run[]>`
  - `getRun(id: string) -> Promise<Run>`
  - All calls send JWT header if token in localStorage (auth-ready)
- [ ] **Step 3.2** — Implement `src/frontend/src/pages/NewResearch.vue`
  - Form: competitors/topics textarea + URLs textarea + submit button
  - URL validation before submit (basic format check)
  - SSE progress bar: shows each pipeline stage live (`scraping 1/3... researching... summarizing...`)
  - Report section (renders after `done` event):
    - Executive summary block
    - Trust score badge (`8/10 claims verified`)
    - Key themes list (theme name + finding + source badge per insight)
    - Competitor activity cards (one card per competitor)
    - Flagged hallucinations shown as inline warnings with judge explanation
- [ ] **Step 3.3** — Implement `src/frontend/src/pages/History.vue`
  - Table: date | topics | URL count | trust score | view button
  - Click view → renders same report layout as NewResearch
- [ ] **Step 3.4** — Implement `src/frontend/src/pages/Login.vue`
  - Login form (email + password fields + submit)
  - Wired to `POST /auth/login` but auth not enforced yet
  - Stores JWT token in localStorage on success
- [ ] **Step 3.5** — Implement `src/frontend/src/router.ts`
  - Routes: `/` → NewResearch, `/history` → History, `/login` → Login
  - Navigation guard stub (checks localStorage token — not enforced yet)
- [ ] **Step 3.6** — Implement `src/frontend/src/style.css`
  - CSS variables for colors, spacing, font
  - Responsive single-column layout on mobile
  - Card component styles, badge styles, warning styles
- [ ] **Step 3.7** — Test manually: run dev server, submit 2–3 real URLs, verify report renders correctly
- [ ] **Step 3.8** — Update `docs/PROGRESS.md`

## Key Files
- `src/frontend/src/api.ts`
- `src/frontend/src/pages/NewResearch.vue`
- `src/frontend/src/pages/History.vue`
- `src/frontend/src/pages/Login.vue`
- `src/frontend/src/style.css`

## npm Dependencies (3 only)
- `vue` — reactivity + components
- `vue-router` — client-side routing
- `vite` — build tool

## UI Layout Reference

```
NAVBAR: [Logo]  Market Intel Assistant    [History]  [Login]

── NEW RESEARCH ────────────────────────────────────────
  [ Competitors / Topics         ]  [ Source URLs       ]
  [ OpenAI, Mistral, Cohere      ]  [ https://...       ]
                                    [ https://...       ]
                    [ Run Analysis ]

── LIVE PROGRESS ───────────────────────────────────────
  ✅ Fetched openai.com/blog (1240 words)
  ✅ Fetched mistral.ai/news (890 words)
  ⏳ Fetching cohere.com/blog...
  🔍 Researching topics...
  🤖 Generating summary...
  ⚖️  Checking claims...

── REPORT ──────────────────────────────────────────────
  Executive Summary
  ┌────────────────────────────────────────────────┐
  │ The AI model provider landscape is seeing...   │
  └────────────────────────────────────────────────┘

  Trust Score: 8/10 claims verified ✅

  Key Themes
  ┌──────────────────────────────────────────────┐
  │ 📌 Enterprise Pricing Shifts                 │
  │ OpenAI introduced tiered API pricing...      │
  │ [source: openai.com/blog]                    │
  │ ⚠️ "Prices cut 50%" — UNVERIFIED             │
  │    Judge: not found in source text           │
  └──────────────────────────────────────────────┘

  Competitor Activity
  ┌────────────┐  ┌──────────────┐  ┌──────────┐
  │ OpenAI     │  │ Mistral AI   │  │ Cohere   │
  │ GPT-4o     │  │ Mixtral open │  │ Command  │
  │ launched   │  │ sourced      │  │ R+       │
  │ [source]   │  │ [source]     │  │ [source] │
  └────────────┘  └──────────────┘  └──────────┘
```