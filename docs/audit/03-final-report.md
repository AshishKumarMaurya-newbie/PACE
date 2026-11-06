# PACE Final Audit Report

Audit date: 2026-11-05

## Executive assessment

PACE is a functional early MVP with clear frontend/backend separation, multi-user ownership filters, and a single Alembic schema. The audit added meaningful security, authorization, timezone, pace, and browser-flow coverage without resetting or migrating the configured application database.

**Production readiness: Not ready for public deployment.** The critical Next.js advisory was removed by upgrading to the patched Next 15 line while retaining React 18, but `npm audit` still reports 8 findings: 1 high and 7 moderate. Authentication has no login/registration rate limiter and logout does not revoke a copied JWT. PostgreSQL integration code exists but could not be run because Docker Desktop is unavailable.

## Findings and fixes

- Upgraded `next` and `eslint-config-next` to the 15.5 line and Zod to 4.6.7; resolved versions are Next.js 15.5.29, `eslint-config-next` 15.5.29, React/ReactDOM 18.3.1, and Zod 4.6.7. React 18 was retained after checking the Next peer range.
- Fresh npm audit changed from 12 findings (1 critical, 5 high, 6 moderate) to 8 (0 critical, 1 high, 7 moderate). The remaining high issue is nested `postcss@8.4.31` under Next; the direct PostCSS is 8.5.32. npm's automatic clean target is Next 16.4.5, which was not taken because it would require a separate framework/React-major migration. An override was tried, did not change lock resolution, and was removed.
- Removed the weak built-in JWT secret. Startup now requires at least 32 characters, rejects known placeholders, and allows mixed-case secrets produced by the documented generator. Production configuration rejects `SECURE_COOKIE=false`.
- Registration now defaults off in code; the development example opts in explicitly.
- Added cross-user API checks covering activity get/update/delete, strength get/update/delete, health, plan ownership and completion, calendar, analytics, records, and export. Added a browser check that verifies a second user receives 404 for another user's activity.
- Corrected dashboard UTC week/month boundaries and excluded future-dated activity/workout records from current/lifetime totals and activity trends. Calendar endpoints now derive half-open UTC bounds from a requested IANA timezone; the UI groups session timestamps by the same local timezone.
- Added elapsed average running pace from recorded run duration and distance, plus period pace buckets and frontend activity/metric selectors. It is explicitly not moving pace and does not infer segment times.
- Hardened CSV formula escaping for formula-leading values after whitespace/control characters.
- Added isolated Playwright flows and an opt-in PostgreSQL integration test. E2E uses a unique temporary SQLite database under the OS temp directory, separate ports, and a separate Next output directory.
- Updated README, API/architecture docs, and the prioritized findings report. Corrected the Settings text that incorrectly implied cookies are always `Secure`.

## Files changed

- Dependency/configuration: `frontend/package.json`, `frontend/package-lock.json`, `frontend/next.config.mjs`, `.gitignore`, `backend/app/core/config.py`, `backend/.env.example`, `README.md`.
- Backend behavior: `backend/app/api/v1/dashboard.py`, `backend/app/api/v1/analytics.py`, `backend/app/api/v1/training.py`, `backend/app/api/v1/records.py`, `backend/app/api/v1/export.py`.
- Tests: `backend/tests/conftest.py`, `backend/tests/test_activities.py`, `backend/tests/test_training_data.py`, `backend/tests/test_security_config.py`, `backend/tests/test_postgres_integration.py`, `backend/pytest.ini`, `frontend/playwright.config.ts`, `frontend/tests/e2e/core-flows.spec.ts`, `frontend/tests/e2e/global-teardown.ts`.
- Frontend: `frontend/app/(app)/calendar/page.tsx`, `frontend/app/(app)/analytics/page.tsx`, `frontend/app/(app)/settings/page.tsx`.
- Audit documentation: `docs/audit/01-current-state.md`, `docs/audit/02-findings-and-priorities.md`, `docs/audit/03-final-report.md`, `docs/architecture.md`, `docs/api.md`.

No existing application database or migration revision was deleted or altered. No schema migration was needed for the implemented fixes.

## Verification results

| Check                                                                   | Result                                                                |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Fresh `npm audit`                                                       | 8 findings: 0 critical, 1 high, 7 moderate                            |
| `npm ls next react react-dom zod eslint-config-next`                    | Next/eslint-config-next 15.5.29; React/ReactDOM 18.3.1; Zod 4.6.7     |
| `npm run test:backend`                                                  | 15 passed, 1 skipped, 1 Starlette/httpx deprecation warning           |
| `npm run test:e2e`                                                      | 2 passed in system Chrome                                             |
| `npm run lint`                                                          | Passed; Next reports `next lint` is deprecated                        |
| `npx tsc --noEmit`                                                      | Passed                                                                |
| `npm run build`                                                         | Passed; all 16 routes generated                                       |
| `get_errors` workspace diagnostics                                      | No errors                                                             |
| `alembic upgrade head` + `alembic check` on a fresh temporary SQLite DB | Passed; no model drift                                                |
| PostgreSQL integration test                                             | Skipped; Docker daemon unavailable and `PACE_TEST_POSTGRES_URL` unset |

## Remaining security and reliability issues

- **High:** PostCSS 8.4.31 remains nested under Next 15.5.29 and is within a high-severity advisory range. Do not expose publicly until resolved or formally accepted after reviewing the exact advisory and execution exposure.
- **Moderate:** npm reports seven other findings in transitive ESLint/Next/minimatch packages. Preserve the audit output and re-evaluate after a compatible patched Next 15 dependency graph is available.
- Login and registration have no rate limiting. Registration is disabled by default, but an enabled public endpoint can still be abused; scrypt work makes login/register CPU-sensitive. A shared limiter needs a trusted proxy policy or a shared store; Redis was not introduced without approval.
- Logout only clears the browser cookie. A copied JWT remains usable until expiry (default seven days). Tests confirm expiration is enforced and demonstrate the lack of revocation. A revocation/session table or refresh-token design needs a separate lifecycle decision and migration.
- PostgreSQL-specific UUID, timezone, constraint, migration, and cascade behavior remains unverified here. The optional integration test only ran in skip mode. Run it against a dedicated PostgreSQL test database before deployment; it creates and drops only a generated schema.
- Database-level constraints do not currently guarantee that `planned_workouts.user_id` matches the owner of its referenced `training_plans` row. Route checks prevent normal API misuse; adding a composite constraint needs a data consistency check and migration plan.
- Analytics still reads complete histories into Python for trend/record calculations. Future paging or SQL aggregation should be justified by observed data volume and validated on PostgreSQL.
- There is no separate component-test suite; Playwright currently covers one main workflow and cross-user activity denial, not every UI state or failure mode.

## Product capability assessment

| Capability                                         | Current state                                                                                            | Data/API/UI additions needed                                                                     | Dependencies                                             | Complexity / priority |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------- | --------------------- |
| Elapsed run pace                                   | Implemented from stored run distance and duration; period trend available                                | Keep label explicit; add pace-quality rules if desired                                           | None                                                     | Low / done            |
| Moving pace and GPS route                          | Not implemented; no sample model                                                                         | Activity sample/route tables, ingestion/recording API, map and sample-aware analytics            | Map tiles/provider or native recorder                    | High / later          |
| Speed                                              | Derivable from distance/duration, but no dedicated UI metric                                             | Add cycling speed aggregate and trend, explicitly elapsed average                                | None                                                     | Low / medium          |
| Weekly/monthly mileage, longest run, run frequency | Mileage/frequency by API filter; longest run record exists                                               | Frontend filters/summary presentation can improve                                                | None                                                     | Low / medium          |
| Pace progression                                   | Elapsed pace bucket available in API/UI                                                                  | Add separate chart presentation and user-tested unit formatting                                  | None                                                     | Low / medium          |
| Elevation progression                              | Elevation is stored and period-aggregated; chart selectable                                              | Add a focused elevation comparison view                                                          | None                                                     | Low / medium          |
| Heart-rate trend/zones                             | Per-activity average heart rate is stored; samples/zones absent                                          | Trend from activity averages; zones need time-series samples and a declared model                | None for average trend; sample storage for zones         | Medium / later        |
| Training load/consistency                          | Activity count available; no load or adherence model                                                     | Define a training-load formula, planned-vs-completed statuses, streak/consistency view           | Domain agreement; likely no service dependency initially | Medium / later        |
| Exercise library                                   | Free-text exercise names only                                                                            | Optional normalized exercise catalog with category/equipment/muscle group; retain custom entries | None                                                     | Medium / optional     |
| Plan templates/adherence                           | Plan creation, scheduling, completion exist; no edit/delete, weekly templates, skipped/rescheduled state | Plan/session lifecycle APIs and UI; migration only if status/recurrence model requires it        | None                                                     | Medium / medium       |
| Health metrics                                     | Manual records and trends exist; units remain caller-supplied                                            | Optional unit registry/validation and edit policy; no medical claims                             | None                                                     | Low / medium          |
| Activity tags                                      | Absent                                                                                                   | User-owned tag and association tables plus filters                                               | None                                                     | Low / low             |
| GPX/FIT/TCX/Strava                                 | Absent                                                                                                   | Import adapters, external IDs/dedup constraints, parsing, OAuth and sync status UI               | Format parsers/provider APIs                             | High / later          |
| Password reset/email verification                  | Absent                                                                                                   | Verification/reset token lifecycle, email delivery, screens and token revocation strategy        | Email provider                                           | Medium-high / later   |
| PWA                                                | No service worker/offline support                                                                        | Manifest, icons, caching policy, install/offline behavior tests                                  | None                                                     | Medium / later        |

## Production readiness

The app builds and its core flows pass local tests, but it is **not production-ready** until the remaining high npm advisory is resolved or accepted, auth rate limiting and token lifecycle are addressed for the deployment threat model, and the PostgreSQL integration suite passes against a dedicated database. No claim is made that an unrun PostgreSQL test passed.
