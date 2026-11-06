# Architecture

PACE is a modular monolith with a separate Next.js web client and FastAPI REST API. PostgreSQL is the application database; SQLAlchemy 2.0 models and Alembic revisions define the schema. Redis, Celery, and external fitness integrations are intentionally absent until background processing or imports are needed.

## Boundaries

- `frontend/app` owns App Router pages and layouts. The protected `(app)` route group checks `/auth/me`; login and registration remain public.
- `frontend/lib/api.ts` is the centralized credentialed API client and typed data boundary.
- `backend/app/api/v1` owns HTTP routing and request/response behavior.
- `backend/app/schemas` validates API input and shapes responses.
- `backend/app/models` owns persistence. `services` and `repositories` can be introduced when domain workflows outgrow the route-level queries.
- `backend/app/core` owns configuration and password/token security; `backend/app/db` owns SQLAlchemy metadata and sessions.
- `backend/migrations` contains Alembic configuration and versioned schema changes.

## Data ownership

Every user-owned table carries a `user_id` foreign key. Every read, update, and delete query scopes by the authenticated user's UUID; another user's record is reported as not found. Strength exercises and sets cascade from their owning workout, and planned sessions cascade from their plan. Distances use meters, exercise weights use kilograms, durations use seconds, and accepted timestamps must have a timezone and are normalized to UTC.

## Authentication

Passwords are stored as salted scrypt hashes. `JWT_SECRET` is required, at least 32 characters, and known placeholders are rejected. Login creates a signed JWT in an HTTP-only, SameSite=Lax cookie. Local development uses a non-Secure cookie; `APP_ENV=production` requires `SECURE_COOKIE=true`. Registration is disabled by the code default and must be explicitly enabled with `ALLOW_REGISTRATION`; backend authorization remains mandatory even when the frontend redirects unauthenticated users. Tokens are not revoked server-side on logout and expire after the configured lifetime.

## Calculations

Dashboard totals and analytics are database-backed and filtered to the signed-in user. Current/lifetime totals exclude future-dated sessions; calendar queries use half-open UTC bounds derived from an explicit IANA timezone. Average running pace is elapsed duration divided by recorded run distance and is not moving pace. Strength set volume is `weight_kg × repetitions`; bodyweight sets are retained but are not assigned an invented load. Personal records currently include longest logged run and strength set weight/volume records. Race-distance times are omitted because an activity total cannot establish a segment time.

## Persistence and local development

Compose runs only PostgreSQL. Start the API and frontend independently for a fast local development loop. Tests override the database session with SQLite and recreate a clean schema per test; Alembic revisions are additionally checked against a temporary SQLite database. PostgreSQL remains the configured runtime database.
Compose runs only PostgreSQL. Start the API and frontend independently for a fast local development loop. Unit/API tests override the database session with SQLite and recreate a clean schema per test. Playwright starts an API against a uniquely named temporary SQLite database outside the repo. An opt-in PostgreSQL test migrates and exercises a unique schema in a dedicated database specified by `PACE_TEST_POSTGRES_URL`; this was not run during the audit because Docker Desktop was unavailable. PostgreSQL remains the configured runtime database.

## Deferred design

GPS and heart-rate samples should live in separate time-series/sample tables rather than bloating activity rows. Import providers should implement an adapter boundary with external IDs and a unique `(provider, external_id)` key. Plans can gain weekly templates and generated sessions without changing the existing plan/session ownership model. Native/mobile recording is preferred over claiming reliable browser background tracking.
