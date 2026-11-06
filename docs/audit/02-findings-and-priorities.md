# PACE Audit Findings and Priorities

Audit date: 2026-11-05. Findings below are based on source inspection, fresh npm audit/advisory checks, and the baseline tests recorded in `01-current-state.md`.

## Critical

### C1. Vulnerable Next.js and Zod dependency set

- **Description:** Initial state used Next.js 14.2.35 and Zod 3.25.76, within current critical/high advisory ranges. This finding is partially mitigated by upgrading Next.js/`eslint-config-next` to 15.5.29 and Zod to 4.6.7 while retaining React 18.3.1.
- **Evidence:** `frontend/package.json` pins the 14.x/3.x ranges and `frontend/package-lock.json` resolves those affected versions.
- **Impact:** A public/self-hosted deployment is exposed to framework and validation-library vulnerabilities. The Windows-hosted Next advisory is directly relevant to this development/host OS.
- **Recommended fix:** Keep current versions and resolve the remaining transitive PostCSS 8.4.31 high advisory and seven moderate findings in a compatible Next 15 patch release, or document why no compatible patch exists before deployment. `npm audit` is still not clean.
- **Risk:** Next 15 is a framework major; App Router/build behavior must be revalidated. Zod 4 has breaking API/type changes, although current source contains no Zod imports.
- **Approval:** Not required for the completed Next 15/Zod 4 upgrade; do not move to Next 16/React 19 without a new documented compatibility/security reason.
- **Final status:** Next.js/`eslint-config-next` 15.5.29 and Zod 4.6.7 are installed; React/ReactDOM remain 18.3.1. Final npm audit is 0 critical, 1 high, 7 moderate. The high finding is PostCSS 8.4.31 nested under Next 15.5.29. The automatic clean target is Next 16.4.5; a scoped PostCSS override was tested but did not change lockfile resolution and was removed. Residual risk remains; not production-ready.

## High

### H1. Predictable JWT signing secret is accepted

- **Description:** `Settings.jwt_secret` defaults to the literal `change-this-secret-before-deploying`; startup does not reject the default or a short value.
- **Evidence:** `backend/app/core/config.py`; `backend/app/core/security.py` signs all user tokens with that setting.
- **Impact:** If deployed without a correctly configured secret, an attacker who knows the source default can mint a valid token for any UUID user.
- **Recommended fix:** Require a high-entropy secret at startup, validate a minimum length, remove the known fallback, and document a generation command. Keep a test-only explicit secret in test configuration.
- **Risk:** Existing deployments relying on the default would invalidate tokens after restart; user records are unaffected and users can sign in again.
- **Approval:** No; no DB migration is required.
- **Final status:** Fixed. JWT secret is mandatory, min 32 characters, and rejects known placeholders/whitespace; tests cover missing, placeholder, mixed-case generated-style values. Production configuration rejects `SECURE_COOKIE=false`. Example settings and README were updated.

### H2. Public auth endpoints have no rate limiting

- **Description:** Registration and login have no rate limiting. Registration is disabled by the code default but explicitly enabled in the local development example.
- **Evidence:** `backend/app/api/v1/auth.py`, `backend/app/core/config.py`.
- **Impact:** Credential stuffing, account-creation abuse, and scrypt CPU exhaustion can degrade a public instance.
- **Recommended fix:** Add configurable rate limits for registration and login, keyed by client identity with a trusted-proxy policy. Avoid an in-process-only limiter if deploying multiple workers.
- **Risk:** Requires choosing/deploying a shared rate-limit store or proxy policy; no such service currently exists.
- **Approval:** Ask before adding Redis or a new dependency. A short-term single-process throttle is not a production substitute.
- **Final status:** Partially mitigated. Public registration now defaults off. No login/register rate limiter was added because there is no shared store/proxy contract; brute-force and scrypt exhaustion risk remains for deployments that enable public access.

### H3. PostgreSQL integration coverage is present but unverified here

- **Description:** Standard API tests use SQLite. An opt-in PostgreSQL test now runs Alembic and CRUD/cascade assertions inside an isolated generated schema when `PACE_TEST_POSTGRES_URL` is set.
- **Evidence:** `backend/tests/test_postgres_integration.py`, `backend/pytest.ini`, `docker-compose.yml`.
- **Impact:** SQLite's date coercion and type behavior mask PostgreSQL-specific defects; clean install and migration compatibility are unverified.
- **Recommended fix:** Run the opt-in test in CI or against a dedicated test database. It creates/drops only a UUID-named schema and does not reset a database.
- **Risk:** Docker Desktop is unavailable here; the PostgreSQL test was skipped and PostgreSQL behavior remains unverified.
- **Approval:** No code/data reset of any existing database is authorized.
- **Final status:** Optional integration test added; skipped in this environment because Docker Desktop is unavailable and `PACE_TEST_POSTGRES_URL` is unset. No existing database was migrated or reset.

## Medium

### M1. Time-boundary calculations are inconsistent

- **Description:** Fixed during this audit: dashboard now starts weeks at UTC midnight and excludes future activity; calendar uses an explicit IANA timezone and half-open UTC bounds.
- **Evidence:** `backend/app/api/v1/dashboard.py`, `backend/app/api/v1/training.py`, `frontend/app/(app)/calendar/page.tsx`.
- **Impact:** Monday morning totals can be omitted, and events near midnight may show on the wrong calendar day depending on PostgreSQL session timezone and user timezone.
- **Recommended fix:** Retain the current policy and extend tests to month/leap-year boundaries and PostgreSQL runtime behavior.
- **Risk:** Prior summary totals can change; no stored data was modified.
- **Approval:** No; preserve timestamps and only correct query/display semantics.
- **Final status:** Fixed for dashboard/week/month, current/lifetime future filtering, and calendar local-date bounds. Regression tests cover Monday 00:01 UTC, future activity exclusion, and Los Angeles DST-date selection; PostgreSQL execution remains unverified.

### M2. Analytics query unbounded rows into Python

- **Description:** Activity trends load all matching activity rows after a lower bound and aggregate in Python; strength trends and records load all strength set/run rows. Activity/dashboard trends now exclude future timestamps but remain unbounded in row count.
- **Evidence:** `backend/app/api/v1/analytics.py`, `backend/app/api/v1/records.py`.
- **Impact:** Memory/query cost grows with account history, and future activities can inflate current-period metrics.
- **Recommended fix:** Aggregate in SQL or page/bound data for long histories; retain the tested UTC bounds.
- **Risk:** SQL date-trunc expressions differ across SQLite/PostgreSQL; PostgreSQL integration tests are needed for that approach.
- **Approval:** No.
- **Final status:** Future timestamps are excluded from dashboard and activity trends. Aggregation still loads historical rows/sets into Python without pagination/SQL grouping; this remains a scalability concern, not yet benchmarked.

### M3. Tenant ownership is not enforced for every relationship at DB level

- **Description:** Planned workout `user_id` and `plan_id` have independent foreign keys; no composite constraint guarantees that the plan belongs to that same user.
- **Evidence:** `backend/app/models/training.py`, initial migration, `backend/app/api/v1/training.py`.
- **Impact:** Current route checks prevent ordinary cross-tenant association, but out-of-band writes or future code defects can create inconsistent ownership relationships.
- **Recommended fix:** Add a non-destructive composite ownership constraint/FK in a new migration after validating existing rows; strengthen cross-user tests for every route.
- **Risk:** A constraint migration will fail if existing data is inconsistent. Inspect/repair only after a backed-up, user-approved data plan; never reset data.
- **Approval:** Approval required before any existing-data repair or destructive migration.
- **Final status:** Not changed. Route checks enforce the relationship in ordinary requests; database-level same-owner association constraint still requires a reviewed migration and data-consistency check.

### M4. Auth token remains usable after logout

- **Description:** Logout deletes the cookie but there is no server-side revocation; a copied JWT remains valid for up to seven days.
- **Evidence:** `backend/app/api/v1/auth.py`, `backend/app/core/security.py`.
- **Impact:** A stolen token cannot be invalidated immediately.
- **Recommended fix:** Shorten access-token lifetime and introduce a refresh/revocation design only if the product needs immediate session invalidation; a per-user token version or persisted session table is an option.
- **Risk:** Requires a DB migration and token lifecycle changes; existing tokens must be handled deliberately.
- **Approval:** Ask before adding persistent sessions/refresh tokens. For this MVP, document residual risk and shorten lifetime only with explicit rollout planning.
- **Final status:** Verified, not changed. Tests prove expiration rejection and demonstrate that a copied JWT remains usable after logout until expiry (default seven days).

### M5. Important endpoints lack comprehensive authorization regression tests

- **Description:** New two-user regression coverage now exercises activity detail/update/delete, strength detail/update/delete, health, plan association/completion, calendar, analytics, records, and exports. It uses SQLite rather than PostgreSQL.
- **Evidence:** `backend/tests/test_activities.py`, `backend/tests/test_training_data.py`.
- **Impact:** A future unscoped query could leak another user's data unnoticed.
- **Recommended fix:** Preserve the cross-resource test and add equivalent checks to PostgreSQL integration once that service is available.
- **Risk:** Low; tests use isolated SQLite.
- **Approval:** No.
- **Final status:** Expanded. Tests now attempt cross-user activity get/patch/delete; strength get/patch/delete; health; plan ownership/scheduling/completion; calendar; analytics; records; and JSON export. Browser E2E also verifies another account sees 404 for a private activity.

### M6. Frontend claims/actions exceed implemented workflows

- **Description:** Strength API supports PATCH/DELETE but UI only creates/lists. Plans cannot be edited/deactivated/deleted; history lacks page controls. Playwright now covers the primary user workflow and tenant isolation; there is no separate component-test suite. Analytics now includes distance/elevation/elapsed pace controls.
- **Evidence:** Frontend route inventory and API implementations; no frontend test scripts/files found.
- **Impact:** The product cannot fully exercise documented API capabilities and regressions are not caught in browser flows.
- **Recommended fix:** Keep the E2E suite; implement strength edit/delete and plan lifecycle only as separate product work.
- **Risk:** E2E needs a controlled database and service lifecycle; Docker unavailability blocks PostgreSQL-based runs here.
- **Approval:** No for tests; product workflow expansion can be separately prioritized.
- **Final status:** Primary Playwright flow added and passed. Strength edit/delete and plan lifecycle remain missing; no component-test suite or history pagination.

## Low / Informational

### L1. Unused frontend dependencies and duplicated local state fetching

- **Description:** `zod`, React Hook Form/resolvers, TanStack Query, `date-fns`, and some UI imports have no current source usage; page components issue direct fetch requests.
- **Evidence:** Frontend imports and manifest.
- **Impact:** Larger dependency surface and inconsistent loading/error/cache behavior.
- **Recommended fix:** Use the existing validation/form libraries when adding schema-driven forms or remove unused packages only in a dedicated dependency review. Do not remove Zod as a shortcut for the active advisory.
- **Risk:** Lockfile churn and potential future API assumptions.
- **Approval:** No, but do not combine cleanup with the critical security patch.

### L2. Architecture docs describe future boundaries

- **Description:** The `services` and `repositories` directories are empty; route handlers own direct ORM queries. No circular imports were observed in the inspected dependency flow.
- **Evidence:** Directory inventory and route imports.
- **Impact:** Current repo is maintainable at its size, but complex analytics and transactions may make route modules harder to test as features grow.
- **Recommended fix:** Extract only domain logic that is reused or independently testable; no broad refactor is justified now.
- **Risk:** Unnecessary abstractions would add indirection.
- **Approval:** No.

### I1. Deferred features are genuinely absent

GPS, imported file formats, Strava synchronization, activity tags, training templates/adherence, medical claims, password reset, email verification, and PWA support are not implemented. GPS-derived pace/segments and fixed-distance PRs require samples or route data; aggregate activity distance/duration alone cannot establish segment times.
