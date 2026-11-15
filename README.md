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

**Status on 2026-11-15: live on BlackBoxV3, a personal fleet server,
publicly reachable through a temporary Cloudflare quick tunnel. This
is not a cloud-provider deployment.**

The service was deployed on BlackBoxV3 (Ubuntu 26.04.1, Tailscale
100.111.94.8) on 2026-11-15, after BlackBoxV2 stayed unreachable for
the whole day (record at the end of this section). The claims ceiling
is unchanged: a portfolio backend on a personal fleet server, never
"production" or "customer-facing".

Run route. BlackBoxV3 has no Docker and no passwordless sudo, so the
Compose stack could not be used there. The stack runs natively in
user space instead:

- PostgreSQL 16.2 from the binaries bundled with the `pgserver`
  Python package, data directory `~/fde-pgdata` on the host,
  listening on 127.0.0.1 port 5433.
- The app under uvicorn in a Python 3.12 virtual environment (uv
  managed), bound to 127.0.0.1 port 8100.
- The `.env` was generated on the server from `.env.example` with
  server-generated secrets and has never left the host.
- `~/fde-start.sh` on the host restarts all three processes (database,
  app, tunnel) after a reboot; nothing auto-starts on its own.

Public address (temporary):
https://precision-supervision-arts-sticker.trycloudflare.com

The address is a Cloudflare quick tunnel URL. It is temporary: it
changes whenever the tunnel process restarts, and it dies with the
host. A named tunnel on a stable subdomain was checked first and is
not achievable with the Cloudflare API token available here: the
token returned an empty zone list on 2026-11-15, so it has no zone or
DNS permission. The quick tunnel needs no account change and is
labelled temporary everywhere it appears.

Verified on 2026-11-15, from the host unless stated otherwise:

- `GET /health` returned HTTP 200 with body
  `{"status": "ok", "database": "ok"}`.
- Authenticated round trip against the live service: seed admin login
  200 and `GET /auth/me` showed role `admin`; the refresh endpoint
  issued a new token pair (rotation; refresh tokens are stateless
  JWTs, so a previous refresh token stays valid until its own expiry
  and there is no server-side revocation list); a registered user
  (201) logged in, created a referral (201), read it back (200, alias
  matched), and added a nested appointment (201).
- Denials, all against the live service: a second user reading the
  first user's referral got 403 and saw an empty referral list; a
  non-admin calling `GET /admin/users` got 403; an unauthenticated
  referral list call got 401.
- Through the public tunnel URL: `GET /health` returned 200 with the
  same body, admin login returned 200, and `GET /admin/users`
  returned 200 listing the 4 accounts created during the round trips.
- One verification limit, stated plainly: requests to the tunnel URL
  from the Muse sandbox VM were answered 403 by Cloudflare (that
  VM's egress is a datacenter proxy). The public route was verified
  from the host's own network through the Cloudflare edge, including
  the authenticated calls above.

BlackBoxV2 remains the intended Compose target and its deployment is
still pending that host's return. Verified on 2026-11-15 between
11:24 and 11:34 EST, over repeated attempts: the Tailscale route
works (a control connection to BlackBoxV3 over the identical route
answered), but BlackBoxV2's userspace does not answer on any port, so
nothing was deployed, started, or modified there. The deploy there is
a single step once the host is back: clone this repo, create `.env`
from `.env.example` with fresh secrets generated on the server, run
`docker compose up -d --build`, then verify `/health` over the
tailnet. The stack itself is already proven by CI, which builds the
Compose stack and smoke-tests the health endpoint on every push.

## License

Apache-2.0.
