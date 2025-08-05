# MCP Gateway Project PRD

Version: 0.1  
Owner: Platform Engineering  
Status: Draft

## 0. Plan

Goals
- Build a production-ready reference implementation that deploys Docker’s MCP Gateway as the front-door for Model Context Protocol tools, with OAuth2.0 + JWT auth, OPA-based policy enforcement, role-based access control (admin, user), structured logging, and auditable tool-call history.
- Mirror the structure and operational patterns from the existing mcp-server-oauth2.0 project, but replace the custom MCP server with Docker’s maintained MCP Gateway as the core.
- Provide complete project documentation: dependencies, inventory, environment variables, auth, OPA policy, scaffolding/functions, data models/storage, testing, and logging/observability.

Non-Goals
- Re-implement MCP Gateway functionality (we will configure and extend via composition and policies).
- UI/portal beyond minimal health/status endpoints; optional downstream apps may integrate later.

Success Criteria
- docker compose up brings up mcp-gateway, OPA, auth server (or external identity provider), storage (db), and optional sidecars.
- AuthN via OAuth2.0 Code flow; JWTs verified at gateway; roles and scopes propagated to OPA.
- OPA policies enforce per-tool, per-resource, per-tenant RBAC decisions.
- Tool call history persisted; structured logs emitted and aggregated.
- Health checks and integration tests pass in CI.

Milestones
- M1: Baseline compose stack (gateway + OPA + mock auth + db) with health checks.
- M2: OAuth2.0 + JWT end-to-end with roles and OPA allow/deny for sample tools.
- M3: Persistence for tool-call history + basic analytics and audit logs.
- M4: Hardened deployment, docs complete, test suite and policies validated.

References
- Docker MCP Gateway: https://docs.docker.com/ai/mcp-gateway/
- Prior art (structure/terminology): projects/mcp-server-oauth2.0

---

## 1. Dependencies

Runtime
- Docker Engine 24+ and Docker Compose v2+
- MCP Gateway container image (per Docker docs)
- OPA image (openpolicyagent/opa:latest or pinned)
- Python 3.11+ (if we include sample service/tooling) OR Node.js LTS (optional)
- PostgreSQL 15+ or SQLite (for local dev) for audit and tool-call history
- Redis (optional) for rate limiting, sessions or pub/sub

Auth and Security
- OAuth2.0 / OIDC Provider (Auth0/Okta/Keycloak/Custom auth-server)
- JWKS endpoint reachable by the gateway and OPA
- TLS certificates (reverse proxy layer, production)

Dev Tooling
- Make, bash, curl, jq
- pytest or unittest for Python-based tests (if used)
- k6 or artillery for load tests (optional)
- opa (CLI) for policy test bundle/validation

---

## 2. Inventory

Directory Structure (proposed)
- projects/mcp-gateway/
  - compose/
    - docker-compose.yml
    - .env (local only; example in repo as .env.example)
  - docs/
    - PRD.md (this doc)
    - dependencies-and-inventory.md
    - architecture-diagram.md
    - QUICKSTART.md
  - services/
    - auth-server/ (optional if using external IdP)
      - Dockerfile
      - requirements.txt
      - app/
        - main.py (OAuth2 flows, JWKS, token issuance)
    - opa/
      - policies/
        - mcp/
          - authz.rego
      - data/ (optional static data for policies)
    - storage/
      - migrations/ (SQL)
      - init.sql
    - gateway/ (optional overlays/config for mcp-gateway, if supported by env/config files)
  - data/
    - protected/
    - public/
    - uploads/
  - tests/
    - integration/
    - policies/
    - health/
  - Makefile
  - README.md

Containers
- mcp-gateway: Main entry to MCP tools. Verifies JWT, enforces scopes, forwards to tools, emits logs.
- opa: Policy decision point (PDP) evaluating requests with JWT claims, resource, action context.
- auth-server (dev only): Local OAuth2.0 provider for end-to-end testing if no external IdP available.
- db: Postgres (prod) or sqlite volume (dev) for audit logs, tool-call history.
- observability (optional): Loki/Promtail or OpenTelemetry Collector and Tempo/Grafana stack.
- proxy (optional): Nginx/Caddy/Traefik in front of gateway for TLS, rate-limits.

Apps/Services
- Gateway (Docker MCP Gateway)
- OPA policy engine
- Auth server (optional dev)
- Tool backends (either internal containers or remote MCP tool providers)
- Storage for history/logs

---

## 3. Environment Variables

Global (compose/.env.example)
- COMPOSE_PROJECT_NAME=mcp-gateway
- ENV=dev|staging|prod
- TZ=UTC

MCP Gateway
- GATEWAY_PORT=8080
- GATEWAY_LOG_LEVEL=info|debug
- GATEWAY_ALLOWED_ORIGINS=*
- OAUTH_ISSUER=https://<issuer> (IdP or local auth-server)
- OAUTH_AUDIENCE=<audience>
- OAUTH_JWKS_URI=https://<issuer>/.well-known/jwks.json
- OAUTH_REQUIRED_SCOPES=mcp:read,mcp:write
- RBAC_DEFAULT_ROLE=user
- RBAC_ADMIN_GROUP=admin
- RATE_LIMIT_RPS=20 (optional)
- HISTORY_DB_DSN=postgresql://user:pass@db:5432/mcp?sslmode=disable or sqlite:///data/history.db

OPA
- OPA_LOG_LEVEL=info
- OPA_BUNDLE_URL= (optional) or mount policies
- OPA_DECISION_PATH=/mcp/authz/allow

Auth-Server (dev)
- AUTH_ISSUER_URL=http://auth-server:9000
- AUTH_CLIENT_ID=<client_id>
- AUTH_CLIENT_SECRET=<secret>
- AUTH_REDIRECT_URI=http://localhost:5173/callback (example)
- AUTH_JWT_SIGNING_ALG=RS256
- AUTH_JWKS_PATH=/jwks.json

Database
- POSTGRES_DB=mcp
- POSTGRES_USER=mcp
- POSTGRES_PASSWORD=changeme
- POSTGRES_HOST=db
- POSTGRES_PORT=5432

Observability
- OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
- LOG_FORMAT=json

---

## 4. Auth (OAuth2.0 with JWT) and Roles

Flows
- Authorization Code with PKCE for user-facing clients.
- Client Credentials for server-to-server tools (optional).

JWT Verification
- Gateway validates JWT signature using jwks_uri.
- Enforce exp, nbf, aud, iss claims; extract sub, email, groups/roles, scopes.

Roles and Scopes
- Roles: admin, user (extensible to readonly, auditor).
- Scopes: mcp:read, mcp:write, mcp:admin, tool:<name>:<action>.
- Role to scope mapping configured statically and/or via OPA data.

Propagation
- Gateway attaches evaluated role/scope context into request attributes for OPA input.
- Downstream services may receive X-User-Id, X-Roles, X-Scopes headers (internal only).

Admin Capabilities
- Manage tool registry, rotate keys, view audit and policy decisions, override emergency deny.
- Access to admin-only metrics and diagnostics.

User Capabilities
- Invoke allowed tools within assigned scopes; view own history.

Threat Model
- JWT replay: short token lifetime + nonce/PKCE + TLS.
- Token leakage: no tokens in logs; redact; secure storage.
- Privilege escalation: OPA deny by default; explicit allow; separation of duties.

---

## 5. OPA as a Container to Enforce Policies

Policy Model (Rego)
- Package: mcp.authz
- Input shape:
  {
    "method": "POST",
    "path": "/tools/<tool>/invoke",
    "user": {
      "sub": "...",
      "roles": ["user","admin"],
      "scopes": ["mcp:read","tool:excel:read"]
    },
    "resource": {
      "tool": "<tool_name>",
      "action": "<action>"
    },
    "env": "dev"
  }

Decision
- Default deny; allow when:
  - Valid JWT verified by gateway
  - Role/scope policy allows resource.action
  - Optional ABAC: data sensitivity labels + user clearance
- Fine-grained:
  - Per-tool, per-action, per-dataset label
  - Time-based, tenant-based, environment-based rules

Example Rego (snippet)
/* services/opa/policies/mcp/authz.rego */
package mcp.authz

default allow = false

is_admin {
  "admin" in input.user.roles
}

scope_allowed(scope) {
  scope in input.user.scopes
}

tool_action_allowed {
  required := sprintf("tool:%s:%s", [input.resource.tool, input.resource.action])
  scope_allowed(required)
}

allow {
  is_admin
}

allow {
  tool_action_allowed
}

Testing Policies
- Use opa test tests/policies to cover allow/deny cases for roles, scopes, and labels.

---

## 6. Scaffolding & Functions

Compose Services (high level)
- mcp-gateway:
  - image: per docs (e.g., docker/mcp-gateway:latest)
  - ports: "${GATEWAY_PORT}:8080"
  - env: OAUTH_ISSUER, OAUTH_AUDIENCE, OAUTH_JWKS_URI, HISTORY_DB_DSN, OPA_URL=http://opa:8181
- opa:
  - image: openpolicyagent/opa:latest
  - volumes: ./services/opa/policies:/policies
  - command: ["run", "--server", "--set=decision_logs.console=true", "/policies"]
  - healthcheck: http GET /health
- auth-server (dev optional):
  - sample OAuth2 provider (FastAPI) issuing JWT with roles/scopes
- db:
  - postgres with init.sql creating tables: tool_calls, audit_events, users (optional mirror)
- observability:
  - loki/promtail or otel-collector

Gateway Functions
- JWT validation middleware
- Request context enrichment (user, roles, scopes)
- OPA query client (POST to /v1/data/mcp/authz/allow with input)
- Decision cache with TTL (optional)
- History writer (async) to DB
- Health endpoints: /health, /ready
- Metrics: /metrics (prometheus format if available)

CLI/Make Commands
- make up, make down, make logs, make test, make policy-test, make db-migrate

---

## 7. Data Models, Data Storage, RBAC and Data Flow

Storage Options
- Dev: SQLite file for simplicity
- Prod: Postgres

Schema (minimal)
- tool_calls
  - id (uuid)
  - user_sub (text)
  - tool (text)
  - action (text)
  - input_json (jsonb)
  - output_json (jsonb)
  - decision (text) -- allow/deny
  - reason (text) -- policy/role detail
  - created_at (timestamptz)
  - trace_id (text)

- audit_events
  - id (uuid)
  - user_sub (text)
  - event_type (text) -- authn_success, authn_fail, policy_deny, policy_allow, error
  - details_json (jsonb)
  - created_at (timestamptz)

- users (optional mirror)
  - sub (pk)
  - email
  - roles (text[]) or separate user_roles table

RBAC
- Role assignment sourced from IdP (preferred) and/or mapping in OPA data.
- Scopes carried in JWT. OPA enforces combination of role + scope + resource.

Data Flow
1) Client obtains access token from IdP (Auth Code flow).  
2) Client calls MCP Gateway with Bearer token.  
3) Gateway validates JWT (JWKS).  
4) Gateway builds OPA input from request + claims, queries OPA.  
5) OPA returns allow/deny with optional reason.  
6) If allowed, gateway forwards to tool; captures result.  
7) Gateway logs tool-call record and audit event to DB.  
8) Observability stack ingests logs/metrics.

---

## 8. Testing (Health Checks, Test Cases, Policies)

Health Checks
- Gateway: /health (200 up), /ready (dependency checks: JWKS reachable, DB connect, OPA reachable)
- OPA: GET /health
- DB: liveness via psql or TCP check

Test Matrix
- AuthN:
  - Valid token, expired token, wrong audience, wrong issuer, invalid signature
- AuthZ:
  - user vs admin
  - missing scope, correct scope, wrong tool/action
  - data label constraints
- E2E:
  - token → gateway → OPA allow → tool → history persisted
  - token → gateway → OPA deny → 403, audit event written
- Performance:
  - Rate limiting behavior
  - OPA latency and decision cache effectiveness

Policy Tests
- opa test services/opa/policies/mcp/*.rego tests/policies/*.rego

CI
- Compose profile runs gateway+opa+db+auth-server
- Run unit + integration + policy tests
- Produce coverage and policy decision logs snapshots

---

## 9. Tool Call History and Logging

Structured Logging
- JSON logs with fields:
  - timestamp, level, service, trace_id, span_id
  - user_sub (redacted/hashed as policy dictates)
  - tool, action, decision, latency_ms
  - error_code, error_message (if any)

Correlation/Tracing
- Propagate trace_id across gateway → OPA → tool
- OTEL support if available; fallback to log correlation

Retention and Privacy
- PII minimized; redact tokens; configurable retention
- Access to audit tables restricted to admin

Export/Analytics
- Optional periodic export to parquet for analytics
- Grafana dashboards for allow/deny rates, top tools, error spikes

---

## Appendices

A. Example Compose Skeleton (illustrative)
version: "3.9"
services:
  mcp-gateway:
    image: docker/mcp-gateway:latest
    environment:
      - GATEWAY_LOG_LEVEL=${GATEWAY_LOG_LEVEL}
      - OAUTH_ISSUER=${OAUTH_ISSUER}
      - OAUTH_AUDIENCE=${OAUTH_AUDIENCE}
      - OAUTH_JWKS_URI=${OAUTH_JWKS_URI}
      - OPA_URL=http://opa:8181
      - HISTORY_DB_DSN=${HISTORY_DB_DSN}
    ports:
      - "${GATEWAY_PORT}:8080"
    depends_on:
      - opa
      - db

  opa:
    image: openpolicyagent/opa:latest
    command: ["run", "--server", "/policies"]
    volumes:
      - ./services/opa/policies:/policies:ro
    ports:
      - "8181:8181"

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./services/storage/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"

  auth-server:
    build: ./services/auth-server
    environment:
      - AUTH_ISSUER_URL=${AUTH_ISSUER_URL}
    ports:
      - "9000:9000"

volumes:
  db-data:

B. Example Policy Input (OPA)
{
  "method": "POST",
  "path": "/tools/excel/invoke",
  "user": {"sub": "abc", "roles": ["user"], "scopes": ["tool:excel:read"]},
  "resource": {"tool": "excel", "action": "read"},
  "env": "dev"
}

C. Migration Init (services/storage/init.sql)
CREATE TABLE IF NOT EXISTS tool_calls (
  id uuid PRIMARY KEY,
  user_sub text,
  tool text,
  action text,
  input_json jsonb,
  output_json jsonb,
  decision text,
  reason text,
  created_at timestamptz DEFAULT now(),
  trace_id text
);
CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY,
  user_sub text,
  event_type text,
  details_json jsonb,
  created_at timestamptz DEFAULT now()
);

---

End of PRD.
