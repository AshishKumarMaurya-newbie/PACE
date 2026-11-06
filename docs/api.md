# API

Base path: `/api/v1`. Interactive OpenAPI documentation is available at `/docs` while the API is running. Protected endpoints require the `pace_access` HTTP-only cookie returned by registration or login. Request validation errors use FastAPI's structured `422` response; authorization failures return `401`; missing or non-owned records return `404`.

## Authentication

| Method | Path             | Purpose                                                      |
| ------ | ---------------- | ------------------------------------------------------------ |
| POST   | `/auth/register` | Create an account and sign in (when registration is enabled) |
| POST   | `/auth/login`    | Sign in                                                      |
| POST   | `/auth/logout`   | Clear the session cookie                                     |
| GET    | `/auth/me`       | Get the current user                                         |

## Activities and overview

| Method           | Path                                         | Purpose                                                                                                          |
| ---------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| GET/POST         | `/activities`                                | List (filter with `activity_type`, `search`, `offset`, `limit`) or create                                        |
| GET/PATCH/DELETE | `/activities/{id}`                           | Read, update, or delete an owned activity                                                                        |
| GET              | `/dashboard/summary`                         | User-specific lifetime, week, month, and recent activity totals                                                  |
| GET              | `/analytics/overview`                        | Activity distribution, aggregate totals, and elapsed average run pace when supported by logged distance/duration |
| GET              | `/analytics/trends?period=week\|month\|year` | Distance, duration, elevation, frequency, and elapsed-run-pace buckets; supports optional `activity_type`        |
| GET              | `/analytics/strength`                        | Monthly logged strength-set volume and count                                                                     |

Activity types are `run`, `walk`, `ride`, `hike`, `swim`, `strength`, `yoga`, `sport`, and `other`. Distance is meters and duration is seconds. Input timestamps must contain a timezone.

## Strength, training, and health

| Method           | Path                                                                        | Purpose                                                                                                                             |
| ---------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| GET/POST         | `/strength/workouts`                                                        | List or create workouts with exercises and multiple sets                                                                            |
| GET/PATCH/DELETE | `/strength/workouts/{id}`                                                   | Read, edit, or delete an owned workout                                                                                              |
| GET/POST         | `/training/plans`                                                           | List or create training plans                                                                                                       |
| POST             | `/training/plans/{id}/workouts`                                             | Schedule a planned session                                                                                                          |
| POST             | `/training/workouts/{id}/complete`                                          | Mark an owned planned session complete                                                                                              |
| GET              | `/training/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD&timezone=Area/Location` | Get completed activities, strength workouts, and planned sessions in a date range; `timezone` is an IANA zone and defaults to `UTC` |
| GET/POST         | `/health/metrics`                                                           | List (optional `metric_type`) or record a manual measurement                                                                        |
| GET              | `/records`                                                                  | Compute available run-distance and strength records                                                                                 |

## Export

`GET /export/activities?format=json` returns the signed-in user's activity records as JSON. Use `format=csv` for a spreadsheet-compatible download. CSV formula-leading text values are escaped.

Public registration is disabled by default and returns `403` unless `ALLOW_REGISTRATION=true`. `JWT_SECRET` is required (minimum 32 characters); production startup also requires `APP_ENV=production` with `SECURE_COOKIE=true`. Login tokens are not revoked server-side on logout; deleting the cookie only removes the browser's copy.
