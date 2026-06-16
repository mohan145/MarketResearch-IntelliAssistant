# Phase 6 — Change Detection + Monitoring (Stretch)

## Goal
Add "what's new since last run" diffing and a monitoring dashboard. Both are optional but directly address the stretch goals in ProblemStatement.txt.

## Checklist

- [ ] **Step 6.1** — Implement change detection in `src/backend/pipeline/`
  - `get_previous_run(user_id, topics, session) -> PipelineResult | None`
  - `compute_diff(current: PipelineResult, previous: PipelineResult) -> RunDiff`
  - `RunDiff`: new_themes, removed_themes, new_competitor_activities, summary_delta
  - Add `diff: RunDiff | None` field to `PipelineResult`
  - Update orchestrator: if previous run exists for same topics, compute diff
- [ ] **Step 6.2** — Update `src/frontend/src/pages/NewResearch.vue`
  - After report renders: if diff exists, show "What's new since last run" collapsible section
  - New themes shown in green, removed themes in strikethrough
- [ ] **Step 6.3** — Add `GET /api/research/stats` endpoint
  - Returns: total_runs, avg_trust_score, avg_duration_seconds, runs_by_week (list), hallucination_rate_by_run (list)
- [ ] **Step 6.4** — Add `src/frontend/src/pages/Monitoring.vue`
  - Metrics row: Total Runs | Avg Trust Score | Avg Duration
  - Hallucination rate over time (SVG line chart — no chart library, plain SVG)
  - Runs per week (SVG bar chart — plain SVG)
  - Add `/monitoring` route
- [ ] **Step 6.5** — Write tests for `compute_diff`
  - New theme added → appears in `new_themes`
  - Removed competitor activity → appears in `removed_competitor_activities`
  - Identical runs → empty diff
- [ ] **Step 6.6** — Update `docs/PROGRESS.md`

## Key Files
- `src/backend/pipeline/orchestrator.py` (updated)
- `src/backend/api/research.py` (updated — new stats endpoint)
- `src/frontend/src/pages/Monitoring.vue`
- `src/frontend/src/pages/NewResearch.vue` (updated — diff section)

## Note on Charts
Use plain SVG for monitoring charts — no Chart.js, no D3. Keeps frontend bundle lean.