# ADR-004: Authentication Strategy

**Date:** 2026-06-15
**Status:** Accepted
**Author:** Mohan Krishna Kosetti

---

## Problem

The app needs authentication so research runs are scoped to a user and the history
page shows only that user's runs. The question is how much auth complexity to build
for a demo-stage internal tool — and which mechanism to use.

---

## Options Considered

### Option 1: OAuth2 / External Identity Provider (Azure AD, Google, Supabase Auth)
- **Approach:** Delegate authentication to an external provider. Users sign in via
  OAuth2 Authorization Code flow. The backend validates the ID token from the provider.
- **Pros:** No password storage, battle-tested security, supports SSO.
- **Cons:** Requires tenant/app registration on the provider side, callback URLs,
  CORS configuration, and refresh token handling. Heavy setup for a demo with 1–2
  evaluators. Azure AD B2C has no meaningful free tier for this use case.

### Option 2: Full registration + custom JWT
- **Approach:** `POST /auth/register` creates users, `POST /auth/login` issues JWTs,
  bcrypt-hashed passwords in SQLite, `get_current_user()` dependency on every route.
- **Pros:** Production-grade, supports any number of users, no external dependencies.
- **Cons:** Needs register UI, email validation, password reset — all out of scope for
  a demo. Over-engineered when the audience is known and small.

### Option 3: FastAPI simple JWT + seeded demo user (chosen)
- **Approach:** One `DEMO_EMAIL` / `DEMO_PASSWORD` pair in `.env`. On startup,
  `init_db()` seeds the user row in SQLite if it doesn't already exist (idempotent —
  safe across restarts). `POST /auth/login` verifies the bcrypt hash and issues a
  signed 24-hour JWT. Every protected route uses `Depends(get_current_user)` which
  decodes the token and returns the `User` row.
- **Pros:** Zero UI friction — evaluators log in immediately with known credentials.
  Real JWT infrastructure, identical to what a production system uses. No external
  service dependency.
- **Cons:** Single user only. Password lives in `.env` (acceptable for local demo;
  must be rotated before any real deployment).

### Option 4: No auth / HTTP Basic Auth
- **Approach:** Remove auth entirely, or use FastAPI's `HTTPBasic`.
- **Pros:** Simplest possible.
- **Cons:** No per-user history scoping. HTTP Basic sends credentials unencrypted on
  every request. Doesn't demonstrate the auth story the problem statement requires.

---

## Decision

**Option 3 — FastAPI simple JWT with a seeded demo user.**

---

## How It Works (Current Mechanism)

```
User visits app
    │
    ▼ (no token in localStorage)
Router guard (router.ts beforeEach)
    │ redirects to /login
    ▼
Login.vue → POST /auth/login { email, password }
    │
    ▼
auth.py: query User by email → bcrypt.checkpw(plain, hashed)
    │ match
    ▼
jose.jwt.encode({ sub: user_id, exp: now+24h }, SECRET_KEY)
    │
    ▼
{ access_token: "eyJ..." } → stored in localStorage
    │
    ▼
Router guard redirects to /
    │
    ▼
Every protected fetch: Authorization: Bearer <token>
    │
SSE endpoint (EventSource can't set headers):
    token passed as ?token=<jwt> query param
    │
    ▼
get_current_user() / get_current_user_from_query():
    jose.jwt.decode(token, SECRET_KEY) → user_id
    db.get(User, user_id) → User row
    │
    ▼
Route handler executes, scoped to current_user.id
```

**Password hashing:** `bcrypt` library directly (not passlib) — passlib's bcrypt
backend raises a `ValueError` on newer Python versions due to a wrap-bug detection
issue. Direct `bcrypt.hashpw` / `bcrypt.checkpw` is simpler and stable.

**Token storage:** `localStorage` (acceptable for a demo; production should use
`httpOnly` cookies to prevent XSS token theft).

**Demo user persistence:** seeded once by `init_db()` on first startup. The row
lives in `./data/market_research.db` and survives all subsequent restarts. Only
deleted if the SQLite file is manually removed.

---

## Rationale

FastAPI's JWT pattern is the standard building block for custom auth in Python APIs.
The seeded demo user approach removes all friction for evaluators while keeping the
JWT infrastructure real and production-compatible. The upgrade path to full multi-user
auth is deliberately minimal.

Key constraints at decision time:
- Demo audience: 1–2 evaluators, known credentials are fine
- Timeline: Phase 4 must not block Phase 5 (Azure deployment)
- No external service budget: Azure AD B2C / Supabase ruled out

---

## Future Scope — Extending to Production Auth

| What to change | How |
|---|---|
| Add self-service registration | Expose `POST /auth/register`, remove seed logic from `init_db()` |
| Multi-user | Already supported — `ResearchRun.user_id` FK is in place |
| Token refresh | Add `POST /auth/refresh`, issue short-lived access + long-lived refresh tokens |
| Secure token storage | Move from `localStorage` to `httpOnly` cookie; add CSRF protection |
| Switch to OAuth2 / SSO | Replace `POST /auth/login` with OAuth2 Authorization Code flow; keep `get_current_user()` dependency unchanged — only the token source changes |
| Password reset | Add `POST /auth/forgot-password` + email link flow |
| Role-based access | Add `role` column to `User`; extend `get_current_user()` to check role |

The `get_current_user()` FastAPI dependency is the single integration point — all
route handlers receive a `User` object and are agnostic to how the token was issued.
Swapping the auth mechanism (custom JWT → OAuth2 → API keys) only changes the
dependency implementation, not the route handlers.

---

## Consequences

- `src/backend/api/auth.py` — `POST /auth/login` only; `get_current_user()` dependency
- `src/backend/database.py` — `init_db()` seeds demo user on first startup (idempotent)
- `src/backend/api/research.py` — all routes protected; SSE uses query-param token
- `.env` — `DEMO_EMAIL` and `DEMO_PASSWORD` added
- Frontend `Login.vue` — stores JWT in localStorage on success, redirects to `/`
- `router.ts` — guard enforced: unauthenticated → `/login`, already logged in → `/`
- `App.vue` — navbar updates reactively via `router.afterEach`; hides nav links when logged out
- `api.ts` — `apiFetch` wrapper auto-redirects to `/login` on any 401 response

---

## References

- FastAPI OAuth2 + JWT: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- `python-jose`: JWT encode/decode
- `bcrypt` (direct): password hashing (passlib avoided — see mechanism notes above)