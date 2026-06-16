# Phase 4 — Auth + Persistence

## Goal
Wire full JWT authentication and SQLite persistence. Every research run saved to DB, scoped to the logged-in user. Auth enforced on all protected routes.

## Checklist

- [ ] **Step 4.1** — Implement `src/backend/database.py`
  - SQLAlchemy engine from `settings.DATABASE_URL`
  - `get_session()` dependency (yields `Session`)
  - `init_db()` — `Base.metadata.create_all(engine)`
- [ ] **Step 4.2** — Implement `src/backend/models.py`
  - `User`: id, email, hashed_password, created_at, is_active
  - `ResearchRun`: id, user_id (FK), topics (JSON str), competitors (JSON str), urls (JSON str), result_json (full PipelineResult), hallucination_count, run_duration_seconds, created_at
- [ ] **Step 4.3** — Implement `src/backend/api/auth.py`
  - `POST /auth/register` — hash password (passlib bcrypt), save User
  - `POST /auth/login` — verify password, return JWT (python-jose, 24h expiry)
  - `get_current_user()` dependency — decodes JWT, returns User
- [ ] **Step 4.4** — Update `src/backend/api/research.py`
  - Add `current_user: User = Depends(get_current_user)` to all routes
  - Save `PipelineResult` to `ResearchRun` after pipeline completes
  - `GET /api/research/history` scoped to `current_user.id`
- [ ] **Step 4.5** — Update `src/backend/main.py`
  - Call `init_db()` on startup
  - Register auth router
- [ ] **Step 4.6** — Update frontend `Login.vue`
  - On login success: store JWT in localStorage, redirect to `/`
  - On 401 response anywhere: redirect to `/login`
  - Router guard: redirect to `/login` if no token
- [ ] **Step 4.7** — Write `tests/backend/api/test_research.py`
  - Test unauthenticated request returns 401
  - Test authenticated run saves to DB and appears in history
- [ ] **Step 4.8** — Update `docs/PROGRESS.md`

## Key Files
- `src/backend/database.py`
- `src/backend/models.py`
- `src/backend/api/auth.py`
- `src/backend/api/research.py` (updated)

## Libraries
- `python-jose[cryptography]` — JWT encode/decode
- `passlib[bcrypt]` — password hashing
- `sqlalchemy` — ORM + session management