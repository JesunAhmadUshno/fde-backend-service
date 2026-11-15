import { Fragment, useMemo, useState } from "react";
import data from "./data.json";

const REPO = "https://github.com/JesunAhmadUshno/fde-backend-service";

function ArchitectureDiagram() {
  return (
    <svg
      className="diagram"
      viewBox="0 0 1200 600"
      role="img"
      aria-label="Architecture diagram of fde-backend-service: an API client calls the FastAPI application; inside it, request logging middleware, five routers, a JWT auth and role layer, and two services; the app reads and writes PostgreSQL, dispatches signed webhooks to owner endpoints, and calls the Open-Meteo APIs."
    >
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" className="d-fill" />
        </marker>
      </defs>

      <rect x="16" y="252" width="150" height="96" className="d-box" />
      <text x="91" y="294" className="d-title d-center">API client</text>
      <text x="91" y="320" className="d-note d-center">HTTPS, JSON</text>

      <line x1="166" y1="300" x2="226" y2="300" className="d-line" markerEnd="url(#arrow)" />
      <text x="196" y="284" className="d-note d-center">requests</text>

      <rect x="230" y="40" width="440" height="520" className="d-box-outer" />
      <text x="254" y="76" className="d-title">FastAPI application</text>
      <text x="254" y="100" className="d-note">app/main.py, factory pattern, async throughout</text>

      <rect x="254" y="122" width="392" height="46" className="d-box" />
      <text x="450" y="151" className="d-label d-center">Request logging middleware</text>

      <text x="254" y="200" className="d-note">Routers, app/routers/</text>
      <g>
        <rect x="254" y="212" width="120" height="52" className="d-box" />
        <text x="314" y="244" className="d-label d-center">auth</text>
        <rect x="386" y="212" width="120" height="52" className="d-box" />
        <text x="446" y="244" className="d-label d-center">referrals</text>
        <rect x="518" y="212" width="128" height="52" className="d-box" />
        <text x="582" y="244" className="d-label d-center">webhooks</text>
        <rect x="254" y="276" width="186" height="52" className="d-box" />
        <text x="347" y="308" className="d-label d-center">integrations</text>
        <rect x="452" y="276" width="194" height="52" className="d-box" />
        <text x="549" y="308" className="d-label d-center">admin</text>
      </g>
      <text x="254" y="356" className="d-note">Appointments are nested under referrals</text>

      <rect x="254" y="376" width="392" height="76" className="d-box" />
      <text x="450" y="404" className="d-label d-center">JWT auth and role layer</text>
      <text x="450" y="428" className="d-note d-center">
        argon2 hashing, rotating refresh tokens, owner or admin checks
      </text>

      <rect x="254" y="472" width="190" height="64" className="d-box" />
      <text x="349" y="498" className="d-label d-center">Webhook service</text>
      <text x="349" y="520" className="d-note d-center">signer and deliverer</text>
      <rect x="456" y="472" width="190" height="64" className="d-box" />
      <text x="551" y="498" className="d-label d-center">Weather client</text>
      <text x="551" y="520" className="d-note d-center">injectable HTTP client</text>

      <rect x="770" y="40" width="414" height="150" className="d-box" />
      <text x="794" y="76" className="d-title">PostgreSQL</text>
      <text x="794" y="102" className="d-note">async SQLAlchemy, portable column types</text>
      <text x="794" y="130" className="d-label">users, referrals, appointments</text>
      <text x="794" y="156" className="d-label">webhook endpoints, delivery log</text>

      <line x1="670" y1="100" x2="764" y2="100" className="d-line" markerEnd="url(#arrow)" />
      <text x="717" y="84" className="d-note d-center">reads, writes</text>
      <line x1="764" y1="150" x2="676" y2="150" className="d-line" markerEnd="url(#arrow)" />
      <text x="717" y="176" className="d-note d-center">GET /health runs SELECT 1</text>

      <rect x="770" y="252" width="414" height="150" className="d-box" />
      <text x="794" y="288" className="d-title">Owner webhook endpoints</text>
      <text x="794" y="314" className="d-note">
        {data.webhookEvents.join(", ")}
      </text>
      <text x="794" y="342" className="d-label">X-FDE-Signature: sha256 HMAC of the body</text>
      <text x="794" y="368" className="d-label">Up to 3 attempts, exponential backoff</text>

      <line x1="670" y1="330" x2="764" y2="330" className="d-line" markerEnd="url(#arrow)" />
      <text x="717" y="314" className="d-note d-center">signed deliveries</text>
      <path d="M 977 252 L 977 196" className="d-line" markerEnd="url(#arrow)" />
      <text x="991" y="230" className="d-note">every attempt logged</text>

      <rect x="770" y="452" width="414" height="108" className="d-box" />
      <text x="794" y="488" className="d-title">Open-Meteo APIs</text>
      <text x="794" y="514" className="d-note">No key required, results cached briefly</text>
      <text x="794" y="540" className="d-label">GET /integrations/clinic-weather</text>

      <line x1="670" y1="504" x2="764" y2="504" className="d-line" markerEnd="url(#arrow)" />
      <text x="717" y="488" className="d-note d-center">current weather</text>
    </svg>
  );
}

function FlowBox({ x, y, w, title, note, note2 }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height="104" className="d-box" />
      <text x={x + w / 2} y={y + 42} className="d-label d-center">
        {title}
      </text>
      <text x={x + w / 2} y={y + 66} className="d-note d-center">
        {note}
      </text>
      {note2 && (
        <text x={x + w / 2} y={y + 86} className="d-note d-center">
          {note2}
        </text>
      )}
    </g>
  );
}

function AuthFlowDiagram() {
  return (
    <svg
      className="diagram"
      viewBox="0 0 1200 330"
      role="img"
      aria-label="Authenticated request flow: a client logs in, the service verifies the argon2 password hash and issues an access and refresh token pair, the client sends the access token as a bearer header, the auth layer loads the user or returns 401, the owner or admin check returns 403 for another owner's record, and the handler then runs."
    >
      <defs>
        <marker
          id="arrow-auth"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" className="d-fill" />
        </marker>
      </defs>
      <FlowBox x="16" y="30" w="250" title="1. Log in" note="POST /auth/login" note2="email and password" />
      <FlowBox x="330" y="30" w="250" title="2. Verify" note="argon2 hash check" note2="against the users table" />
      <FlowBox x="644" y="30" w="250" title="3. Token pair issued" note="access JWT, 30 minutes" note2="refresh token, 7 days, rotating" />
      <FlowBox x="958" y="30" w="226" title="4. Send the token" note="Authorization header" note2="Bearer access token" />
      <path d="M 1071 134 L 1071 196 L 894 196" className="d-line" markerEnd="url(#arrow-auth)" />
      <FlowBox x="644" y="196" w="250" title="5. Load the user" note="get_current_user dependency" note2="missing or invalid token: 401" />
      <path d="M 644 248 L 580 248" className="d-line" markerEnd="url(#arrow-auth)" />
      <FlowBox x="330" y="196" w="250" title="6. Owner or admin check" note="another owner's record: 403" note2="admin routes: admin role or 403" />
      <path d="M 330 248 L 266 248" className="d-line" markerEnd="url(#arrow-auth)" />
      <FlowBox x="16" y="196" w="250" title="7. Handler runs" note="CRUD, webhooks, weather" note2="response 200, 201 or 204" />
      <line x1="266" y1="82" x2="324" y2="82" className="d-line" markerEnd="url(#arrow-auth)" />
      <line x1="580" y1="82" x2="638" y2="82" className="d-line" markerEnd="url(#arrow-auth)" />
      <line x1="894" y1="82" x2="952" y2="82" className="d-line" markerEnd="url(#arrow-auth)" />
    </svg>
  );
}

function WebhookFlowDiagram({ events }) {
  return (
    <svg
      className="diagram"
      viewBox="0 0 1200 330"
      role="img"
      aria-label="Webhook delivery flow: a referral or appointment event creates one delivery row per subscribed endpoint, each delivery is signed with HMAC-SHA256, posted to the owner endpoint, retried up to three attempts with exponential backoff on failure, and every attempt is written to the delivery log."
    >
      <defs>
        <marker
          id="arrow-hook"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" className="d-fill" />
        </marker>
      </defs>
      <FlowBox x="16" y="30" w="250" title="1. Event fires" note={events[0]} note2={events.slice(1).join(", ")} />
      <FlowBox x="330" y="30" w="250" title="2. Delivery rows" note="one per subscribed endpoint" note2="stored in PostgreSQL" />
      <FlowBox x="644" y="30" w="250" title="3. Sign the body" note="HMAC-SHA256 with the secret" note2="X-FDE-Signature: sha256 digest" />
      <FlowBox x="958" y="30" w="226" title="4. POST, attempt 1" note="to the owner endpoint" note2="5 second timeout" />
      <path d="M 1071 134 L 1071 196 L 894 196" className="d-line" markerEnd="url(#arrow-hook)" />
      <FlowBox x="644" y="196" w="250" title="5. On failure, retry" note="attempts 2 and 3" note2="exponential backoff" />
      <path d="M 644 248 L 580 248" className="d-line" markerEnd="url(#arrow-hook)" />
      <FlowBox x="330" y="196" w="250" title="6. Log every attempt" note="status and attempt count" note2="success or final failure" />
      <path d="M 330 248 L 266 248" className="d-line" markerEnd="url(#arrow-hook)" />
      <FlowBox x="16" y="196" w="250" title="7. Read the log back" note="GET /webhooks/deliveries" note2="own endpoints, admins: all" />
      <line x1="266" y1="82" x2="324" y2="82" className="d-line" markerEnd="url(#arrow-hook)" />
      <line x1="580" y1="82" x2="638" y2="82" className="d-line" markerEnd="url(#arrow-hook)" />
      <line x1="894" y1="82" x2="952" y2="82" className="d-line" markerEnd="url(#arrow-hook)" />
    </svg>
  );
}

const ACCESS_GROUPS = [
  ["all", "All access"],
  ["none", "Public"],
  ["user", "Signed in"],
  ["owner or admin", "Owner or admin"],
  ["admin", "Admin only"],
];

function accessGroup(auth) {
  if (auth === "none") return "none";
  if (auth === "admin") return "admin";
  if (auth === "owner or admin") return "owner or admin";
  return "user";
}

const ROLE_ROWS = [
  ["Register, log in, refresh a token", "yes", "yes", "yes"],
  ["Create referrals and appointments", "no", "yes", "yes"],
  ["Read referrals and appointments", "no", "own records", "all records"],
  ["Change or delete a referral", "no", "own records", "all records"],
  ["Register webhook endpoints", "no", "yes", "yes"],
  ["Read the webhook delivery log", "no", "own endpoints", "all endpoints"],
  ["Clinic weather integration", "no", "yes", "yes"],
  ["List accounts, set a user role", "no", "no", "yes"],
];

const CI_NOTES = {
  test: "pytest suite against a PostgreSQL 16 service container",
  docker: "Compose stack builds, /health smoke test, then teardown",
};

export default function App() {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [method, setMethod] = useState("all");
  const [openKey, setOpenKey] = useState(null);

  const methods = useMemo(
    () => ["all", ...new Set(data.endpoints.map((e) => e.method))],
    []
  );
  const visible = useMemo(
    () =>
      data.endpoints.filter((e) => {
        if (group !== "all" && accessGroup(e.auth) !== group) return false;
        if (method !== "all" && e.method !== method) return false;
        if (
          query &&
          !`${e.method} ${e.path} ${e.purpose}`.toLowerCase().includes(query.toLowerCase())
        )
          return false;
        return true;
      }),
    [query, group, method]
  );
  const authTests = data.tests.perFile.find((f) => f.file.includes("authorization"));

  return (
    <>
      <header className="nav">
        <div className="container nav-in">
          <a className="wordmark" href="#top" aria-label="fde-backend-service, back to top">
            fde-backend-service
          </a>
          <nav className="nav-links" aria-label="Page sections">
            <a href="#architecture">Architecture</a>
            <a href="#flows">Flows</a>
            <a href="#endpoints">Endpoints</a>
            <a href="#access">Access</a>
            <a href="#tests">Tests</a>
            <a href="#deployment">Deployment</a>
            <a href={REPO}>Repository</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="container">
            <h1>A backend, drawn to scale</h1>
            <p className="lead">
              FastAPI and PostgreSQL, JWT auth, two roles, signed webhooks, one delivery
              log.
            </p>
            <p className="actions">
              <a className="btn btn-primary" href="#endpoints">
                Read the endpoint register
              </a>
              <a className="btn" href={REPO}>
                Open the repository
              </a>
            </p>
            <dl className="figures">
              <div>
                <dt>Endpoints in the register</dt>
                <dd className="num">{data.endpoints.length}</dd>
              </div>
              <div>
                <dt>Tests in the suite</dt>
                <dd className="num">{data.tests.total}</dd>
              </div>
              <div>
                <dt>Webhook events signed</dt>
                <dd className="num">{data.webhookEvents.length}</dd>
              </div>
              <div>
                <dt>CI jobs on every push</dt>
                <dd className="num">{data.ciJobs.length}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="section" id="architecture">
          <div className="container">
            <h2>The system on one sheet</h2>
            <figure className="fig">
              <ArchitectureDiagram />
              <figcaption>
                Every box is a component in the repository. Tests replace the two
                outbound HTTP clients with mock transports.
              </figcaption>
            </figure>
            <dl className="spec">
              <div>
                <dt>Startup</dt>
                <dd>
                  The lifespan creates the schema and seeds an admin when ADMIN_EMAIL
                  and ADMIN_PASSWORD are set.
                </dd>
              </div>
              <div>
                <dt>One schema, two databases</dt>
                <dd>
                  Portable column types run the same models on PostgreSQL in deployment
                  and CI, and on SQLite locally.
                </dd>
              </div>
              <div>
                <dt>Health</dt>
                <dd>GET /health runs SELECT 1 and reports the database as ok or degraded.</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="section" id="flows">
          <div className="container">
            <h2>Two flows, step by step</h2>
            <p className="section-line">
              The authenticated round trip and a webhook delivery, drawn from
              app/deps.py, app/routers/, and app/services/webhooks.py.
            </p>
            <figure className="fig">
              <AuthFlowDiagram />
              <figcaption>
                The authenticated round trip. Token lifetimes are the defaults in
                app/config.py; /auth/refresh rotates the pair, and a wrong-type token
                is rejected and tested.
              </figcaption>
            </figure>
            <figure className="fig">
              <WebhookFlowDiagram events={data.webhookEvents} />
              <figcaption>
                Webhook delivery with retries: 3 attempts, 5 second timeout, both
                settings in app/config.py. Every attempt lands in the delivery log,
                read back through the API.
              </figcaption>
            </figure>
          </div>
        </section>

        <section className="section band" id="endpoints">
          <div className="container">
            <h2>Endpoint register</h2>
            <p className="section-line">
              The full HTTP surface, derived from the OpenAPI schema the app serves
              and checked against README.md.
            </p>
            <div className="filters">
              <label className="field">
                <span>Search the register</span>
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="webhooks, referrals, Toronto"
                />
              </label>
              <label className="field">
                <span>Access</span>
                <select value={group} onChange={(e) => setGroup(e.target.value)}>
                  {ACCESS_GROUPS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field">
                <span id="method-label">Method</span>
                <div className="chips" role="group" aria-labelledby="method-label">
                  {methods.map((m) => (
                    <button
                      key={m}
                      type="button"
                      className={method === m ? "chip chip-on" : "chip"}
                      aria-pressed={method === m}
                      onClick={() => setMethod(m)}
                    >
                      {m === "all" ? "All" : m}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <p className="count" role="status">
              Showing {visible.length} of {data.endpoints.length} endpoints
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Method</th>
                    <th scope="col">Path</th>
                    <th scope="col">Access</th>
                    <th scope="col">Purpose</th>
                    <th scope="col">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((e) => {
                    const key = `${e.method} ${e.path}`;
                    const open = openKey === key;
                    return (
                      <Fragment key={key}>
                        <tr>
                          <td className="mono">{e.method}</td>
                          <td className="mono">{e.path}</td>
                          <td>{e.auth}</td>
                          <td>{e.purpose}</td>
                          <td>
                            <button
                              type="button"
                              className="row-toggle"
                              aria-expanded={open}
                              aria-label={`${open ? "Hide" : "Show"} schema for ${e.method} ${e.path}`}
                              onClick={() => setOpenKey(open ? null : key)}
                            >
                              {open ? "−" : "+"}
                            </button>
                          </td>
                        </tr>
                        {open && (
                          <tr className="detail-row">
                            <td colSpan="5">
                              <dl className="detail">
                                <div>
                                  <dt>Operation</dt>
                                  <dd>
                                    {e.summary} (tag: {e.tags.join(", ") || "none"})
                                  </dd>
                                </div>
                                <div>
                                  <dt>Parameters</dt>
                                  <dd>
                                    {e.parameters.length
                                      ? e.parameters
                                          .map(
                                            (p) =>
                                              `${p.name} (${p.where}${p.required ? ", required" : ""})`
                                          )
                                          .join(", ")
                                      : "None declared. The request body carries the payload where the operation takes one."}
                                  </dd>
                                </div>
                                <div>
                                  <dt>Response codes in the schema</dt>
                                  <dd>{e.responses.join(", ")}</dd>
                                </div>
                                <div>
                                  <dt>Bearer security in the schema</dt>
                                  <dd>{e.secured ? "Required (HTTPBearer)" : "Not required"}</dd>
                                </div>
                              </dl>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {visible.length === 0 && (
              <p className="empty">No endpoint matches that filter. Clear the search to see the full register.</p>
            )}
          </div>
        </section>

        <section className="section" id="access">
          <div className="container">
            <h2>Who can do what</h2>
            <p className="section-line">
              Two roles, enforced per route. Another owner&apos;s record returns a
              403, and the denials are covered by{" "}
              {authTests ? authTests.count : 0} tests in tests/test_authorization.py.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Capability</th>
                    <th scope="col">Anonymous</th>
                    <th scope="col">User</th>
                    <th scope="col">Admin</th>
                  </tr>
                </thead>
                <tbody>
                  {ROLE_ROWS.map(([capability, anon, user, admin]) => (
                    <tr key={capability}>
                      <th scope="row">{capability}</th>
                      <td>{anon}</td>
                      <td>{user}</td>
                      <td>{admin}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="section band" id="tests">
          <div className="container">
            <h2>Test evidence</h2>
            <p className="section-line">
              {data.tests.total} tests, counted from tests/ at build time. The build
              fails if the count and the README disagree.
            </p>
            <div className="two-col">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">File</th>
                      <th scope="col">Tests</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tests.perFile.map((f) => (
                      <tr key={f.file}>
                        <td className="mono">{f.file}</td>
                        <td className="num">{f.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <dl className="spec">
                {data.ciJobs.map((job) => (
                  <div key={job}>
                    <dt>CI job: {job}</dt>
                    <dd>{CI_NOTES[job] || "Runs on every push and pull request."}</dd>
                  </div>
                ))}
                <div>
                  <dt>What the suite covers</dt>
                  <dd>
                    Registration, login, token refresh and type confusion, cross-owner
                    denials, CRUD, webhook signing and retry, and the mocked weather
                    integration.
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        <section className="section" id="deployment">
          <div className="container">
            <h2>Deployment status</h2>
            <p className="status-line">
              Status on {data.deployment.date}: {data.deployment.status}
            </p>
            <dl className="spec">
              <div>
                <dt>Intended target</dt>
                <dd>
                  BlackBoxV2 (Tailscale 100.83.221.65), the Compose stack as fde-backend,
                  app on port 8100.
                </dd>
              </div>
              <div>
                <dt>What was verified</dt>
                <dd>
                  On 2026-11-15, 11:24 to 11:34 EST, BlackBoxV3 answered over the same
                  route; BlackBoxV2 replied to nothing. Nothing was deployed, started,
                  or modified.
                </dd>
              </div>
              <div>
                <dt>The one step left</dt>
                <dd>
                  Clone, create .env with server-generated secrets, docker compose up,
                  verify /health over the tailnet. CI already proves the stack.
                </dd>
              </div>
            </dl>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <p className="foot-mark">fde-backend-service</p>
          <p>
            A portfolio backend on a personal fleet server. Not a production system; the
            clinic data is synthetic.
          </p>
          <p className="foot-links">
            <a href={REPO}>Repository</a>
            <a href={`${REPO}/blob/main/README.md`}>README and full record</a>
            <a href={`${REPO}/actions/workflows/ci.yml`}>CI runs</a>
          </p>
          <p>
            Generated at build time from site/src/openapi.json, README.md, tests/,
            app/schemas.py, and ci.yml. The build fails if the record drifts.
          </p>
        </div>
      </footer>
    </>
  );
}
