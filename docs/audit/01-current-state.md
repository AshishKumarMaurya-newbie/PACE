# PACE Current-State Audit

Audit date: 2026-11-05

This document is the Phase 1 snapshot captured before application changes. Package versions and issue statuses were subsequently updated; see `03-final-report.md` for the verified post-fix state.

## Architecture and repository

PACE is a small modular monolith with a Next.js App Router frontend, a FastAPI API, SQLAlchemy models, and one Alembic initial-schema migration. The repo contains 73 source/config/documentation files, plus ignored build/dependency/runtime outputs. `backend/app/services` and `backend/app/repositories` are empty; route handlers currently own persistence queries and domain calculations. This is straightforward for the present size, but does not yet match the intended service/repository separation in practice.

The frontend has a centralized credentialed fetch client in `frontend/lib/api.ts`, a shared client-side application shell, and 16 routed pages. Most protected pages are client components that render a loading shell and call `/auth/me`; the backend remains the actual authorization boundary. There is no middleware/server-side session check. UI controls are mostly API-connected, but strength edit/delete, plan edit/delete/details, plan adherence, and frontend tests are absent.

## Actual technology versions

| Area                           | Installed/resolved version                                  |
| ------------------------------ | ----------------------------------------------------------- |
| Node.js                        | 24.20.0                                                     |
| Next.js / `eslint-config-next` | 14.2.35 / 14.2.35                                           |
| React / ReactDOM               | 18.3.1 / 18.3.1                                             |
| Zod                            | 3.25.76                                                     |
| TypeScript                     | 5.x (manifest range `^5.4.0`)                               |
| FastAPI / SQLAlchemy           | 0.141.1 / 2.0.52 in the audit environment                   |
| Python                         | 3.14.7                                                      |
| PostgreSQL image               | `postgres:17-alpine` in Compose (not started in this audit) |

`frontend/package-lock.json` is present and `npm ls` confirms the installed versions above. The backend uses version ranges in `requirements.txt`; there is no Python lockfile, so a clean install is not byte-for-byte reproducible.

## Implemented functionality

- Account registration/login/logout and current-user API; salted `hashlib.scrypt` password hashes; signed HS256 JWT in an HTTP-only `SameSite=Lax` cookie.
- Activity CRUD, search/type filter, offset/limit API pagination, dashboard totals, and activity export to JSON/CSV.
- Strength workout CRUD API with free-text exercises and multiple sets; bodyweight sets may have null weight; volume is weight times reps.
- Manual user-owned health measurements; plan creation, planned-session creation/completion, and week/month calendar UI.
- Analytics overview, weekly/monthly/yearly activity aggregates, and monthly strength-set aggregate endpoints; longest recorded run and selected weighted strength records.
- One migration creates `users`, `activities`, `health_metrics`, strength tables, plans, and planned sessions, with UUIDs, foreign keys, and several user/time indexes.

## Missing or partial capabilities

- No GPS/sample tables, pace/speed/cadence or moving-time analytics, GPX/FIT/TCX/Strava integration, import deduplication, or race-segment records.
- Analytics UI only charts distance; backend strength trends are not shown there. Activity distribution excludes strength workouts. No custom date-range selection.
- History UI has search/type filtering but no pagination controls, calendar/list toggle, or date filtering. A `/training/[id]` page is absent.
- Strength history UI has no edit/delete workflow although the API supports them. Exercises are free text; there is no exercise library.
- Plans cannot be edited/deactivated/deleted in the UI/API; no weekly schedule templates, skipped/rescheduled state, adherence, or planned-versus-completed comparison.
- Health measures are append-only and use arbitrary metric/unit strings; no update/delete API. This preserves history but permits inconsistent units for one metric.
- No frontend unit/component/E2E test suite, PWA service worker, password reset, email verification, or deployment container for the web/API.

## Security audit snapshot

Fresh `npm audit` reports **12 advisories: 1 critical, 5 high, 6 moderate**. Direct vulnerable packages are Next.js 14.2.35, `eslint-config-next` 14.2.35, and Zod 3.25.76; affected transitives include `glob`, `minimatch`, `postcss`, and `@typescript-eslint` packages. The advisory tool also identified critical Next.js advisories including unauthenticated Windows-hosted RCE and image-optimizer RCE; the current major is not a suitable public deployment target.

Verified candidate package metadata: Next.js 15.5.28 and `eslint-config-next` 15.5.28 exist; Next 15.5.28 accepts React/ReactDOM `^18.2.0` and Node >=18.18.0. Zod 4.6.7 exists. The current advisory scan reports no known CVEs for those candidate coordinates. A post-install npm audit is still required because the lockfile/transitive graph must be checked after upgrade.

Authentication code findings: the JWT secret has a known weak default and does not fail startup when unset; `SECURE_COOKIE` defaults false; public registration defaults enabled; login/register have no rate limiting. JWT expiration is configured and PyJWT validates `exp`, but logout only deletes the browser cookie, so a copied token remains valid until expiry (default seven days). SameSite=Lax and exact-origin CORS reduce cross-site request risk, but there is no explicit CSRF token/Origin check. Passwords require 10 characters and are scrypt-hashed, but whitespace-only names are accepted after trimming.

Route inspection shows user filters on current activities, strength, health, plan, planned-workout, calendar, export, and analytics queries. Existing tests prove isolation only for activity reads and selected list endpoints; they do not prove cross-user access denial for every detail/update/delete/export/analytics route. Planned workouts have independent `user_id` and `plan_id` foreign keys, so the database does not guarantee those owners match (the create route does check the plan owner).

## Database and migration state

All tests use an in-memory SQLite engine. No PostgreSQL integration test exists. Docker Compose defines only PostgreSQL, but the Docker Desktop daemon was unavailable during this audit. No database was reset, migrated, or otherwise modified for this inspection. The initial migration has no predecessor; it creates the schema but provides no evidence of a safe upgrade path from a prior deployed schema. Application validation enforces many numeric bounds, but the database has no corresponding `CHECK` constraints for duration, repetitions, rest, or strength weights.

Date/time risks found by inspection: `dashboard.summary` starts the week by subtracting weekdays from the current instant, retaining today's time-of-day and omitting Monday activity before that time. The calendar compares timestamp columns to `date` values and relies on database/session timezone casting; the client also groups timestamp strings by their UTC date rather than the user's local date. Activity trends have a lower time bound but no upper bound, and aggregate all matching rows into Python memory.

## Baseline checks

- `npm run test:backend`: **5 passed**, 1 Starlette/httpx deprecation warning.
- `npm run lint`: passed with no ESLint warnings/errors.
- `npx tsc --noEmit`: passed.
- The application was already running on ports 3000/8000. A fresh production build was not run during this inspection because Next dev and production build share `.next`; running both concurrently had previously corrupted the dev bundle. A production build is a required post-fix check after stopping/restarting dev cleanly.
- Docker server: unavailable (`dockerDesktopLinuxEngine` pipe not found), preventing PostgreSQL integration verification.

## Documentation accuracy

The README accurately lists major deferred GPS/import/PWA features and the SQLite test setup. It overstates the calendar as returning all completed sessions in the API table (the actual response does include activities, strength workouts, and planned workouts, but this was undocumented), and describes the cookie as “secure” in the Settings page although `Secure` is false by default. `docs/architecture.md` says every accepted timestamp is normalized to UTC, but calendar query/date display boundaries are not consistently UTC/local aware. `docs/api.md` omits `strength_workouts` in the calendar response and omits the undocumented details of current auth-cookie defaults and lack of token revocation.
