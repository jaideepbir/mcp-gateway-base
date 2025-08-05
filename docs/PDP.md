# Project Development Plan (PDP)

Version: 0.1  
Status: Draft

This plan defines a step-by-step, test-first workflow to build the MCP Gateway stack. Each step produces verifiable outcomes before proceeding.

Guiding Principles
- Iterative: add one component at a time, validate, then progress.
- Test-first: health checks, unit/policy tests, and integration tests per step.
- Observability: logs/metrics at each stage to aid debugging.
- Security: OAuth2 + JWT verification and OPA deny-by-default authorization.

Deliverables per Step
- Code/config changes
- Health checks and tests
- Documentation updates (Quickstart, Dependencies, Architecture, PRD)
- Git commits (conventional)

Milestones
- M1: Baseline compose (gateway + OPA + DB) alive with health checks.
- M2: OAuth2 JWT verification flow working end-to-end.
- M3: OPA authorization policies enforcing RBAC/ABAC with tests.
- M4: Tool-call history persistence and audit logging.
- M5: Hardening, rate limiting, and observability.

---

## Step 0 — Repo Initialization and Docs

Tasks
- Create docs (PRD, Dependencies & Inventory, Architecture, Quickstart, PDP).
- Initialize Git and link remote.

Verification
- README/docs present.
- git status clean, upstream set.

Conventional Commit
- docs: scaffold project docs and PDP

---

## Step 1 — Compose Skeleton and Folders

Tasks
- Create compose/docker-compose.yml with services:
  - mcp-gateway (image per Docker docs)
  - opa (openpolicyagent/opa:latest)
  - db (postgres:15) with services/storage/init.sql
- Create compose/.env.example with required variables.
- Create minimal folder structure under services/ (opa/policies, storage, auth-server placeholder)

Verification
- docker compose config validates
- docker compose up -d starts opa and db
- OPA health 200; DB init tables created

Tests
- Health checks:
  - curl -f http://localhost:8181/health
  - psql select from tool_calls/audit_events (should exist even if empty)

Conventional Commit
- chore(compose): add baseline compose stack with opa and db

---

## Step 2 — OPA Policy Baseline

Tasks
- Add services/opa/policies/mcp/authz.rego with default deny.
- Add minimal allow rules for admin and specific tool:action scopes.
- Add tests in tests/policies/*.rego covering:
  - admin allow
  - user with proper scope allow
  - missing scope deny

Verification
- opa test services/opa/policies/mcp/ tests/policies/ returns success
- OPA policy loaded into container via mounted volume

Conventional Commit
- feat(policy): add baseline mcp authz policy with tests

---

## Step 3 — Gateway Basic Integration

Tasks
- Configure mcp-gateway service in compose with:
  - OPA_URL=http://opa:8181
  - HISTORY_DB_DSN
  - GATEWAY_PORT
- Ensure gateway exposes /health and connects to OPA.

Verification
- curl -f http://localhost:${GATEWAY_PORT}/health
- Check logs for successful OPA connectivity

Tests
- Integration: mock request path hitting OPA (if gateway offers a dry-run or protected route)
- If unavailable, verify OPA decisions via direct OPA POST as a surrogate

Conventional Commit
- feat(gateway): integrate gateway with opa and health endpoint

---

## Step 4 — OAuth2 / JWT Verification

Tasks
- Configure gateway with:
  - OAUTH_ISSUER, OAUTH_AUDIENCE, OAUTH_JWKS_URI
- Choose provider:
  - External IdP (preferred) OR
  - Dev local auth-server (if enabled later)
- Update Quickstart with token acquisition.

Verification
- Valid token → 200 OK on a protected endpoint (or allowed decision)
- Expired/wrong aud/wrong iss → 401/403

Tests
- Integration:
  - Valid token → proceed to OPA decision
  - Invalid/expired → reject
- Negative tests in CI with mocked tokens (if tooling supports)

Conventional Commit
- feat(auth): enable oauth2 jwt verification in gateway

---

## Step 5 — Authorization via OPA (RBAC/ABAC)

Tasks
- Wire gateway’s request context to OPA input schema:
  - user.sub, roles (from claims/groups), scopes
  - resource.tool, resource.action
- Expand Rego for role-to-scope and attribute checks.
- Add more policy tests for:
  - admin override allow
  - user with missing scope deny
  - data label checks (if applicable)

Verification
- Requests with matching tool:action scope → 200
- Otherwise → 403 with audit log

Tests
- Policy tests via opa CLI
- Integration tests hitting gateway with different JWTs

Conventional Commit
- feat(authz): enforce RBAC/ABAC via OPA with expanded tests

---

## Step 6 — Tool-call History and Audit Logging

Tasks
- Implement DB schema (services/storage/init.sql).
- Ensure gateway writes:
  - tool_calls: user_sub, tool, action, input/output json, decision, reason, trace_id, ts
  - audit_events: authn, authz outcomes
- Add SQL migrations folder if needed.

Verification
- On allow/deny, rows appear with correct fields.
- Structured logs emitted with correlation ids.

Tests
- Integration: invoke allowed/denied calls and assert DB rows
- Query with psql to confirm row counts

Conventional Commit
- feat(storage): persist tool-call history and audit events

---

## Step 7 — Observability and Rate Limiting (Optional)

Tasks
- Add otel-collector or logging stack (loki/promtail + grafana).
- Configure GATEWAY_LOG_LEVEL and json logs.
- Optional: add rate limiting env (RATE_LIMIT_RPS) and tests.

Verification
- Logs visible and structured
- Metrics endpoint accessible (if supported)

Tests
- Lightweight load test; verify rate limiting behavior

Conventional Commit
- feat(obs): add observability stack and optional rate limiting

---

## Step 8 — Hardening and CI

Tasks
- CI workflow:
  - docker compose up -d
  - run policy tests
  - run integration tests
- Secrets handling, pinned image tags, resource constraints
- TLS/ingress proxy config for production

Verification
- CI green
- Security checks documented

Conventional Commit
- ci: add policy and integration testing workflow
- chore(security): harden images and configs

---

## Exit Criteria

- All milestones complete.
- Quickstart enables a new engineer to run the stack and validate policies.
- Policies and tests cover core RBAC paths and negative cases.
- Docs and diagrams up to date with final architecture.
