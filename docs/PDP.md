# Project Development Plan (PDP)

Version: 0.2  
Status: Draft

This plan defines a step-by-step, test-first workflow to build the MCP Gateway stack for local and cloud deployment (GCP via Terraform). Each step has verifiable outcomes before proceeding.

Guiding Principles
- Iterative: add one component at a time, validate, then progress.
- Test-first: health checks, unit/policy tests, and integration tests per step.
- Observability: logs/metrics at each stage to aid debugging.
- Security: OAuth2 + JWT verification and OPA deny-by-default authorization.
- Cloud-ready: IaC (Terraform) for GCP (networking, IAM, storage, SQL, runtime).

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
- M5: Hardening, rate limiting, observability.
- M6: GCP IaC provisioning and first cloud deployment (GKE or Cloud Run).
- M7: CI/CD with Terraform plan/apply, container build/push, smoke/integration tests.

---

## Step 0 — Repo Initialization and Docs

Tasks
- Create docs (PRD, Dependencies & Inventory, Architecture, Quickstart, PDP, Task Tracker CSV).
- Initialize Git and link remote.
- Add .editorconfig, .gitignore (docker, python, terraform).
- Add LICENSE and CODEOWNERS (optional).

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
- Create minimal folder structure under services/ (opa/policies, storage, auth-server placeholder).
- Add Makefile for local tasks (up/down/logs/test/policy-test/db-migrate).

Verification
- docker compose config validates
- docker compose up -d starts opa and db
- OPA health 200; DB init tables created

Tests
- Health checks:
  - curl -f http://localhost:8181/health
  - psql select from tool_calls/audit_events (exist even if empty)

Conventional Commit
- chore(compose): add baseline compose stack with opa and db

---

## Step 2 — OPA Policy Baseline

Tasks
- Add services/opa/policies/mcp/authz.rego with default deny.
- Add minimal allow rules for admin and specific tool:action scopes.
- Define input contract and include labels and env.
- Add tests in tests/policies/*.rego covering:
  - admin allow
  - user with proper scope allow
  - missing scope deny
  - label “sensitive” requires admin

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
- Integration: verify OPA decisions via direct OPA POST as surrogate if gateway doesn’t expose dry-run.

Conventional Commit
- feat(gateway): integrate gateway with opa and health endpoint

---

## Step 4 — OAuth2 / JWT Verification

Tasks
- Configure gateway with:
  - OAUTH_ISSUER, OAUTH_AUDIENCE, OAUTH_JWKS_URI
- Document token acquisition for chosen provider (external or dev).
- Update Quickstart with example curl calls.

Verification
- Valid token → 200 OK on protected endpoint (or allowed decision)
- Expired/wrong aud/wrong iss → 401/403

Tests
- Integration:
  - Valid token → proceed to OPA decision
  - Invalid/expired → reject
- Negative tests in CI with mocked tokens (if supported)

Conventional Commit
- feat(auth): enable oauth2 jwt verification in gateway

---

## Step 5 — Authorization via OPA (RBAC/ABAC)

Tasks
- Wire gateway request context to OPA input schema:
  - user.sub, roles, scopes; resource.tool, resource.action; resource.labels; env.
- Expand Rego for role-to-scope and attribute checks.
- Add more policy tests:
  - admin override allow
  - user with missing scope deny
  - label-based checks; environment-specific rules

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
- Add simple DB migration process (plain SQL or Alembic).

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
- Add otel-collector or logging stack (loki/promtail + grafana) in compose.
- Configure GATEWAY_LOG_LEVEL and JSON logs.
- Optional: add rate limiting env (RATE_LIMIT_RPS) and tests.

Verification
- Logs visible and structured
- Metrics endpoint accessible (if supported)

Tests
- Lightweight load test; verify rate limiting behavior

Conventional Commit
- feat(obs): add observability stack and optional rate limiting

---

## Step 8 — Cloud Foundations (GCP) via Terraform

Tasks
- Bootstrap infra/terraform structure:
  - envs/dev|staging|prod and modules/ (network, sql, gke/cloudrun, artifact_registry, iam, secrets, storage, opa_bundle)
- Implement network module:
  - VPC, subnets, Cloud Router, Cloud NAT; outputs for subnet self-links.
- Implement storage module:
  - GCS buckets for logs/exports, optional OPA policy bundles; lifecycle policies.
- Implement artifact registry module for container images.
- Implement IAM module:
  - Project-level roles (least privilege), service accounts (deploy, runtime), Workload Identity pool for GKE.
- Implement secrets module:
  - Secret Manager entries (DB creds, OAuth secrets, JWKS URI if needed).
- Implement SQL module:
  - Cloud SQL Postgres with private IP, database and user; connection name output.
- Implement runtime module:
  - GKE Autopilot (preferred) with WI enabled OR Cloud Run service.
  - If GKE: enable Ingress + managed TLS.
  - If Cloud Run: setup VPC connector for private SQL.
- Providers, backend, variables, outputs in envs/dev.
- Add Makefile targets (tf-init, tf-plan, tf-apply) with environment selection.

Verification
- terraform init/plan/apply completes in dev environment.
- Outputs show endpoints, connection names, SA emails.
- GCS buckets created, AR repo available, Cloud SQL running.

Tests
- tflint/tfsec (optional)
- Smoke test: ping endpoints; confirm Cloud SQL connection; Secret access via SA.

Conventional Commit
- feat(infra): add Terraform modules and dev environment for GCP

---

## Step 9 — Container Build & Deploy to GCP

Tasks
- Build/push images to Artifact Registry (gateway image may be upstream; OPA official).
- If custom sidecars/wrappers exist, create Dockerfiles and GitHub Actions workflow to build/push on main.
- Deploy manifests to GKE (Helm/Kustomize) or deploy services to Cloud Run.
- Configure connectivity to Cloud SQL (proxy or private IP).
- Configure Secret Manager access via WI.
- Configure Ingress/Load Balancer and Managed TLS.

Verification
- Services running in dev cluster/environment.
- Health endpoints green; OPA reachable; DB connects.

Tests
- Cloud smoke tests: health, token path, authz path, history write.
- Policy bundle pull (if using OPA bundles from GCS).

Conventional Commit
- feat(deploy): deploy MCP Gateway stack to GCP dev

---

## Step 10 — CI/CD and Promotion

Tasks
- GitHub Actions:
  - lint, policy tests, compose integration tests.
  - terraform plan (require manual approval), apply on approved.
  - build/push images; deploy manifests to GKE/Cloud Run.
  - post-deploy smoke tests; notify on failures.
- Add environments with protection rules for staging/prod.
- Add release tagging and changelog generation.

Verification
- CI pipeline green; tagged releases publish artifacts.
- Promotion gates enforce approvals.

Conventional Commit
- ci: add terraform and deployment workflows

---

## Step 11 — Hardening and SRE

Tasks
- Pin image tags and enable image scanning.
- Resource limits/requests; HPA (if GKE).
- Pod Security Standards; network policies.
- Centralized logging and dashboards (Cloud Logging/Monitoring or Grafana).
- Backup strategy for Cloud SQL; bucket lifecycle policies.
- Runbook and on-call alerts for SLOs.

Verification
- Security checks documented and implemented.
- Dashboards and alerts active.

Conventional Commit
- chore(security): harden infra and runtime

---

## Exit Criteria

- All milestones complete.
- Quickstart enables a new engineer to run locally.
- Terraform deploys to GCP dev with smoke tests.
- Policies and tests cover core RBAC/ABAC and negative cases.
- Docs and diagrams up to date with final architecture.
