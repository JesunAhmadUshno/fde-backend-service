# fde-backend-service

A small multi-user backend service built with FastAPI, PostgreSQL, and
async SQLAlchemy. It is a portfolio backend product: a reviewer can run
it, register, log in, and exercise every feature end to end.

The domain is a **community clinic appointment and referral queue**
(synthetic data only, no real patient information). A workflow like
this is exactly where missed webhooks and wrong permissions have real
costs, which is why those two mechanisms are built and tested properly
here.

**Claims ceiling:** a runnable, tested backend service deployed on a
personal fleet server. It is not a production system and has no real
users or customers.

Project site: https://jesunahmadushno.github.io/fde-backend-service/

## What it demonstrates

- **Authentication:** registration with argon2-hashed passwords, login
  issuing a short-lived JWT access token plus a refresh token, and a
  refresh endpoint with rotation.
- **Authorization:** two roles (`user`, `admin`). Referrals and webhook
  endpoints belong to their owner; other users get 403; admins can read
  across owners and manage roles. Denials are covered by tests.
- **CRUD:** full create, read, update, delete on referrals, with
  appointments nested under them, filtering on the list endpoint, and
  Pydantic v2 validation on every payload.
- **Webhooks:** owners register endpoints for `referral.created`,
  `referral.updated`, and `appointment.created`. Deliveries are signed
  with HMAC-SHA256 (`X-FDE-Signature: sha256=<digest>`), retried up to
  3 times with exponential backoff, and every attempt is written to a
  delivery log that can be read back through the API.
- **Third-party integration:** `GET /integrations/clinic-weather`
  fetches current weather for a clinic city from the Open-Meteo APIs
  (no key required) and caches results briefly.
- **Operations:** structured JSON logging, a `/health` endpoint that
  checks the database, Docker Compose for the whole stack, and CI that
  runs the test suite against a real PostgreSQL service container.

## Architecture in brief

- `app/main.py` builds the app (factory pattern), owns the lifespan
  (schema creation, optional seed admin), request logging middleware,
  and the health endpoint.
- `app/routers/` holds the HTTP surface: `auth`, `referrals`
  (appointments nested), `webhooks`, `integrations`, `admin`.
- `app/services/` holds the webhook signer/deliverer and the weather
  client. Both take an injectable HTTP client, which is how the tests
  replace the network with a mock transport.
- `app/models.py` uses portable column types, so the same schema runs
  on PostgreSQL in deployment and in CI, and on SQLite for a quick
  local test run.
- Everything is async: async SQLAlchemy sessions, `httpx.AsyncClient`
  for outbound calls, async route handlers throughout.

## Run it

### With Docker Compose (the full stack)

```bash
cp .env.example .env   # then replace the placeholder secrets
docker compose up -d --build
curl http://localhost:8100/health
```

The API is on port 8100 by default (`APP_PORT`), interactive docs at
`http://localhost:8100/docs`. PostgreSQL stays inside the Compose
network; its data lives in the named volume `fde-backend-db-data`.

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` before first startup
to seed an admin account.

### Locally without Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
DATABASE_URL=postgresql+asyncpg://fde:fde_password@localhost:5432/fde \
  .venv/bin/uvicorn app.main:app --port 8100
```

You need a PostgreSQL reachable at `DATABASE_URL`. Tables are created
at startup.

## API surface

| Method and path | Auth | Purpose |
| --- | --- | --- |
| GET /health | none | Service and database health |
| POST /auth/register | none | Create an account (role `user`) |
| POST /auth/login | none | Get access and refresh tokens |
| POST /auth/refresh | refresh token | Rotate a token pair |
| GET /auth/me | user | Current account |
| POST /referrals | user | Create a referral |
| GET /referrals | user | List own referrals (admins: all); `status_filter`, `priority` filters |
| GET /referrals/{id} | owner or admin | Read one referral |
| PATCH /referrals/{id} | owner or admin | Update a referral |
| DELETE /referrals/{id} | owner or admin | Delete a referral |
| POST /referrals/{id}/appointments | owner or admin | Book an appointment |
| GET /referrals/{id}/appointments | owner or admin | List appointments |
| GET /appointments/{id} | owner or admin | Read one appointment |
| PATCH /appointments/{id} | owner or admin | Update an appointment |
| DELETE /appointments/{id} | owner or admin | Delete an appointment |
| POST /webhooks | user | Register an endpoint; returns the signing secret once |
| GET /webhooks | user | List own endpoints (secret never shown) |
| DELETE /webhooks/{id} | owner or admin | Remove an endpoint |
| GET /webhooks/deliveries | user | The delivery log (own endpoints; admins: all) |
| GET /integrations/clinic-weather?city=Toronto | user | Current weather from Open-Meteo, cached |
| GET /admin/users | admin | List all accounts |
| PATCH /admin/users/{id}/role | admin | Set a user's role |

### Verifying a webhook signature

Recompute the HMAC over the exact request body with the endpoint
secret and compare with the `X-FDE-Signature` header:

```python
import hashlib, hmac
expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-FDE-Signature"])
```

## Tests

```bash
.venv/bin/python -m pytest -q
```

The suite (32 tests) covers registration and login, token refresh and
type confusion, authorization denials (cross-owner reads, writes,
admin routes), the full CRUD cycles, webhook signing and verification,
delivery success, retry-then-fail behaviour with the attempt count in
the log, and the weather integration with the upstream API mocked. CI
runs the same suite against PostgreSQL 16.

## Deployment

**Status on 2026-11-15: deployment blocked, host unreachable. No
deployment is claimed.**

The intended target is BlackBoxV2 (Ubuntu, Tailscale 100.83.221.65),
running the Compose stack in this repo under the project name
`fde-backend` (containers `fde-backend-app` and `fde-backend-db`, the
app bound to the tailnet address on port 8100).

What was verified on 2026-11-15 between 11:24 and 11:34 EST, over
repeated attempts:

- The Tailscale tunnel route works: a control connection to
  BlackBoxV3 over the identical route answered with its SSH banner.
- BlackBoxV2 accepts TCP connections at the tailnet layer (ports 22,
  80, 443, 3000, 8080, 9000 all connect), but no service on the host
  answers: SSH sends no banner within 45 seconds and the connection
  is closed, and HTTP probes receive no response.
- Conclusion: the host's userspace is not reachable (the machine
  appears to be off, asleep, or hung; which of these cannot be
  distinguished remotely). SSH access is impossible, so Docker could
  not be inspected and nothing was deployed, started, or modified on
  the host.

The deploy is a single step once the host is back: clone this repo on
BlackBoxV2, create `.env` from `.env.example` with fresh secrets
generated on the server, run `docker compose up -d --build`, then
verify `/health` over the tailnet and record an authenticated round
trip here. The stack itself is already proven by CI, which builds the
Compose stack and smoke-tests the health endpoint on every push.

## License

Apache-2.0.
