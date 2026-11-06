# PACE

PACE is a personal fitness log with a multi-user FastAPI backend and a responsive Next.js App Router frontend. Activities, strength sessions, health measurements, training plans, and analytics are stored in PostgreSQL; dashboards and records are calculated from the signed-in user's saved data.

## Requirements

The current implementation has been exercised with Node 24 and Python 3.14. PostgreSQL integration testing requires Docker Desktop or a dedicated test database.
The PostgreSQL integration test is opt-in and uses a unique temporary schema inside the URL you provide; use a dedicated test database only. It verifies the Alembic revision, UUID-backed activity/strength/health/plan persistence, and plan-session cascade behavior. It could not run here because Docker Desktop is unavailable:

## Local setup (Windows PowerShell)

From the repository root:
The E2E suite covers registration/login/logout, activity CRUD, multi-set strength logging, plans and completion, health entry, analytics, CSV export, protected routes, and cross-user activity denial. It uses installed Google Chrome and a temporary SQLite database outside the repo. There is no separate component-test suite yet.

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
docker compose up -d postgres
```

Edit `backend/.env` and replace the example `JWT_SECRET` before starting the API. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create and activate a backend environment, install dependencies, and migrate the database:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
```

Create the first account interactively (the password is read without echoing):

```powershell
python -m app.cli
```

Start the API in that terminal:

```powershell
python -m uvicorn app.main:app --reload
```

The API is at `http://localhost:8000`; OpenAPI docs are at `http://localhost:8000/docs`.

In a second terminal, install and start the frontend:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. New accounts can also be created at `/register` while `ALLOW_REGISTRATION=true`.

## Configuration

Docker Compose reads the root `.env` for `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. The API reads `backend/.env`:

| Variable               | Purpose                                                                                      | Local default                                                                |
| ---------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `DATABASE_URL`         | SQLAlchemy connection string                                                                 | `postgresql+psycopg://pace:local-development-only@localhost:5432/pace`       |
| `APP_ENV`              | Runtime environment (`development` or `production`)                                          | `development`                                                                |
| `JWT_SECRET`           | Signs session tokens; startup requires a deployment-specific value of at least 32 characters | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_MINUTES` | Cookie/token lifetime                                                                        | `10080`                                                                      |
| `ALLOW_REGISTRATION`   | Enables public account creation                                                              | `false` in code; `true` in the local development example                     |
| `SECURE_COOKIE`        | Requires HTTPS for the session cookie                                                        | `false` locally; required when `APP_ENV=production`                          |
| `FRONTEND_ORIGIN`      | Exact CORS origin                                                                            | `http://localhost:3000`                                                      |

The frontend API base defaults to `http://localhost:8000/api/v1`; override it with `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if needed. Never put secrets in frontend environment variables.

## Security note

The frontend uses Next.js 15.5.29, React/ReactDOM 18.3.1, and Zod 4.6.7. A fresh `npm audit` after the upgrade reports 8 remaining advisories (0 critical, 1 high, 7 moderate), including a high PostCSS finding in Next's nested PostCSS 8.4.31 and moderate transitive ESLint/Next findings. The checked-in Next 15 release keeps React 18; the automatic npm fix points to Next 16, which would require a separate framework migration. Do not expose this build publicly until the remaining audit findings are resolved or assessed against a supported patched Next 15 release.

## Migrations and tests

Run migrations from `backend/`:

```powershell
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "describe schema change"
```

Run backend tests:

```powershell
python -m pytest -q
```

The API tests use an isolated in-memory SQLite database. The production/local application connection remains PostgreSQL. Build the frontend with:

```powershell
Set-Location frontend
npm run build
```

Run the browser flows using installed Google Chrome:

```powershell
npm run test:e2e
```

Playwright starts the API with a uniquely named temporary SQLite database under the OS temp directory, runs migrations there, and uses separate ports and a separate Next output directory. It does not use the configured application database. The PostgreSQL integration test is opt-in and uses a unique temporary schema inside the URL you provide; use a dedicated test database only:

```powershell
$env:PACE_TEST_POSTGRES_URL = "postgresql+psycopg://pace:<test-password>@localhost:5432/pace"
Set-Location backend
python -m pytest -q -m postgres
```

## Product scope

Implemented: account registration/login/logout with HTTP-only JWT cookies; user-scoped activity CRUD, search and type filtering; live dashboard totals; strength workouts with multiple exercises/sets and volume calculations; manually entered wellness metrics and trends; training plans and planned sessions; week/month calendar views with requested IANA timezone; activity and strength analytics endpoints, including elapsed average running pace from recorded distance and duration; supported personal records; CSV/JSON activity exports.

Not yet implemented: GPS capture and route samples, moving pace/speed/cadence/segment analytics, GPX/FIT/TCX or external-platform imports, 1 km/5 km/10 km/half-marathon records without suitable route samples, plan templates or adherence reporting, activity tags, a PWA service worker, password reset/email verification, and frontend component tests. No GPS, sample statistics, moving pace, or unsupported race records are fabricated.

See [docs/architecture.md](docs/architecture.md) and [docs/api.md](docs/api.md) for design and endpoint details.
