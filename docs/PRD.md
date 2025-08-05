# MCP Gateway Project PRD

Version: 0.2  
Owner: Platform Engineering  
Status: Draft

## 0. Plan

Goals
- Build a production-ready reference implementation that deploys Docker’s MCP Gateway as the front-door for Model Context Protocol tools, with OAuth2.0 + JWT auth, OPA-based policy enforcement, role-based access control (admin, user), structured logging, and auditable tool-call history.
- Mirror the structure and operational patterns from the existing mcp-server-oauth2.0 project, but replace the custom MCP server with Docker’s maintained MCP Gateway as the core.
- Provide complete project documentation: dependencies, inventory, environment variables, auth, OPA policy, scaffolding/functions, data models/storage, testing, and logging/observability.
- Cloud-ready deployment on GCP using Terraform (IaC), including foundational networking, service accounts/roles, secrets, storage bucket(s), managed Postgres (Cloud SQL), and container runtime (GKE or Cloud Run + ancillary services).

Non-Goals
- Re-implement MCP Gateway functionality (we will configure and extend via composition and policies).
- Build a full UI; focus is on platform/gateway/policy and integration.

Success Criteria
- docker compose up brings up mcp-gateway, OPA, auth server (or external identity provider), storage (db), and optional sidecars locally.
- IaC provisions GCP infra (VPC, subnets, NAT, Cloud SQL, Artifact Registry, GKE or Cloud Run, Secret Manager, Cloud Storage bucket, IAM).
- CI can deploy to a GCP environment from main (manual approval gate).
- AuthN via OAuth2.0 Code flow; JWTs verified at gateway; roles and scopes propagated to OPA.
- OPA policies enforce per-tool, per-resource, per-tenant RBAC decisions.
- Tool call history persisted; structured logs emitted and aggregated.
- Health checks and integration tests pass in CI and on-cloud.

Milestones
- M1: Baseline compose stack (gateway + OPA + mock auth + db) with health checks.
- M2: OAuth2.0 + JWT end-to-end with roles and OPA allow/deny for sample tools.
- M3: Persistence for tool-call history + basic analytics and audit logs.
- M4: Hardened deployment, docs complete, test suite and policies validated.
- M5: Cloud foundations in GCP via Terraform; container build/push; deploy to GKE/Cloud Run; secrets/IAM/networking; smoke tests.

References
- Docker MCP Gateway: https://docs.docker.com/ai/mcp-gateway/
- OPA: https://www.openpolicyagent.org/
- Terraform GCP: https://registry.terraform.io/providers/hashicorp/google/latest
- GCP best practices: VPC, private service access, Cloud NAT, Cloud SQL private IP
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

Cloud (GCP)
- Terraform >= 1.6.x
- Google Cloud SDK (gcloud), authenticated service account with least privilege
- GCP services: VPC, Cloud NAT, Cloud Router, Artifact Registry, Cloud SQL (Postgres), Secret Manager, Cloud Storage, GKE or Cloud Run, Cloud Logging/Monitoring, Cloud IAM

Auth and Security
- OAuth2.0 / OIDC Provider (Auth0/Okta/Keycloak/Custom auth-server)
- JWKS endpoint reachable by the gateway and OPA
- TLS certificates (GCP-managed via Cloud Load Balancing/Managed Certs or cert-manager on GKE)
- OPA policy bundle storage (optional in GCS)

Dev Tooling
- Make, bash, curl, jq
- pytest or unittest for Python-based tests (if used)
- k6 or artillery for load tests (optional)
- opa (CLI) for policy test bundle/validation
- terraform, tflint, tfsec (optional)

---

## 2. Inventory

Directory Structure (proposed additions marked with +)
- projects/mcp-gateway/
  - compose/
    - docker-compose.yml
    - .env (local only; example in repo as .env.example)
  - docs/
    - PRD.md
    - dependencies-and-inventory.md
    - architecture-diagram.md
    - QUICKSTART.md
    - PDP.md
    - task-tracker.csv
  - services/
    - auth-server/ (optional if using external IdP)
      - Dockerfile
      - requirements.txt
      - app/
        - main.py
    - opa/
      - policies/
        - mcp/
          - authz.rego
      - data/ (optional static data for policies)
    - storage/
      - migrations/ (SQL)
      - init.sql
    - gateway/ (optional overlays/config for mcp-gateway)
  - data/
    - protected/
    - public/
    - uploads/
  - tests/
    - integration/
    - policies/
    - health/
  - + infra/
    - + terraform/
      - + envs/
        - + dev/
          - main.tf
          - variables.tf
          - outputs.tf
          - backend.tf (optional)
          - providers.tf
        - + staging/
        - + prod/
      - + modules/
        - + network/ (vpc, subnets, nat, router)
        - + gke/ or cloudrun/
        - + sql/ (cloud sql postgres)
        - + artifact_registry/
        - + iam/
        - + secrets/ (secret manager)
        - + storage/ (gcs buckets for logs/policies)
        - + opa_bundle/ (optional: GCS policy bundle)
  - Makefile
  - README.md

Containers
- mcp-gateway: Main entry to MCP tools. Verifies JWT, enforces scopes, forwards to tools, emits logs.
- opa: Policy decision point (PDP) evaluating requests with JWT claims, resource, action context.
- auth-server (dev only): Local OAuth2.0 provider for end-to-end testing if no external IdP available.
- db: Postgres (prod) or sqlite volume (dev) for audit logs, tool-call history.
- observability (optional): Loki/Promtail or OpenTelemetry Collector and Tempo/Grafana stack.
- proxy/ingress (cloud): GCLB/Ingress for GKE; HTTPS Load Balancer with managed certs.

Cloud Resources (GCP)
- VPC with subnets per environment
- Cloud Router + Cloud NAT for egress
- Artifact Registry (Docker images)
- Cloud SQL Postgres with private IP + serverless VPC access
- GKE Autopilot cluster or Cloud Run services
- Secret Manager (JWKS URIs, DB credentials, OAuth client secrets)
- IAM service accounts with least privilege; Workload Identity for pods
- GCS buckets: logs/exports, OPA policy bundles (optional)
- Cloud Logging/Monitoring dashboards and alerts

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
- OPA_URL=http://opa:8181

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

Cloud (Terraform variables examples)
- TF_VAR_project_id
- TF_VAR_region
- TF_VAR_env
- TF_VAR_network_cidr
- TF_VAR_subnet_cidrs
- TF_VAR_sql_instance_tier
- TF_VAR_workload_identity_pool
- TF_VAR_opa_policy_bucket
- TF_VAR_artifact_registry_repo

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
- Cloud secrets: Use GCP Secret Manager; never commit secrets; bind via Workload Identity/KMS.

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
      "action": "<action>",
      "labels": ["public","sensitive"]
    },
    "env": "dev",
    "network": {"ip": "10.0.0.5"}
  }

Decision
- Default deny; allow when:
  - Valid JWT verified by gateway
  - Role/scope policy allows resource.action
  - Optional ABAC: data labels + user clearance; time-based, tenant-based
  - Network-aware decisions (optional)

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

label_requires_admin {
  "sensitive" in input.resource.labels
}

allow {
  is_admin
}

allow {
  tool_action_allowed
  not label_requires_admin
}

Testing Policies
- Use opa test tests/policies to cover allow/deny cases for roles, scopes, labels, and environment.

Policy Distribution (Cloud)
- Option 1: Mount policies in container (dev)
- Option 2: OPA bundle in GCS; OPA pulls via bundle URL and IAM creds

---

## 6. Scaffolding & Functions

Compose Services (high level)
- mcp-gateway: JWT validation, OPA client, history writer, health endpoints, metrics
- opa: policy runtime with mounted policies or bundles
- auth-server (dev optional): token issuance with roles/scopes
- db: Postgres with init.sql
- observability: loki/promtail or otel-collector (optional)

Cloud Deployment Options
- GKE Autopilot:
  - Deploy mcp-gateway, opa, sidecars via Helm or Kustomize
  - Workload Identity for pod SA to access Secret Manager/GCS
  - Ingress with GCLB and managed TLS
  - Cloud SQL Auth Proxy or private IP connector for DB
- Cloud Run:
  - Separate services for gateway and opa
  - VPC connector for Cloud SQL private IP
  - IAM-based access to Secret Manager and GCS

CLI/Make Commands
- make up/down/logs/test/policy-test/db-migrate
- make tf-init/tf-plan/tf-apply (env selectable)

---

## 7. Data Models, Data Storage, RBAC and Data Flow

Storage Options
- Dev: SQLite file for simplicity
- Prod: Cloud SQL Postgres with private IP; optionally read replicas

Schema (minimal)
- tool_calls (see SQL in appendices)
- audit_events
- users (optional mirror)

RBAC
- Role assignment from IdP and/or OPA data
- Scopes in JWT; OPA enforces role + scope + resource + labels

Data Flow
1) Client obtains access token from IdP  
2) Client calls MCP Gateway with Bearer token  
3) Gateway validates JWT (JWKS)  
4) Gateway builds OPA input and queries OPA  
5) OPA returns allow/deny (+ reason)  
6) Gateway forwards to tool or denies; writes history/audit  
7) Logs/metrics exported; in cloud, centralized via Cloud Logging/Otel

---

## 8. Testing (Health Checks, Test Cases, Policies)

Health Checks
- Local: /health and /ready; OPA /health; DB connectivity
- Cloud: Probes on deployments; SLO monitors; uptime checks

Test Matrix
- AuthN: valid, expired, wrong aud/iss, bad signature
- AuthZ: role/scope/label variants; deny-by-default
- E2E: allow and deny paths with persistence and logs
- Performance: rate limit and latency
- Cloud: smoke tests post-deploy; policy bundle fetch; Secret Manager access; Cloud SQL connectivity

CI/CD
- Policy tests via opa
- Integration tests via docker compose and/or ephemeral clusters
- Terraform plan + apply with approvals
- Build, push images to Artifact Registry; deploy to GKE/Cloud Run

---

## 9. Tool Call History and Logging

Structured Logging
- JSON logs: timestamp, level, service, trace_id, user_sub (redacted), tool, action, decision, latency, error fields

Tracing
- OTEL setup; propagate trace_id across services

Retention and Privacy
- PII minimized; redact tokens and sensitive fields
- Log retention via GCP sinks and bucket lifecycle policies

Analytics
- Optional exports to GCS parquet and BigQuery for analytics
- Grafana dashboards or Cloud Monitoring custom dashboards

---

## 10. Cloud & Terraform Scope

Terraform Modules (custom or community)
- network: VPC, subnets, router, NAT
- gke or cloudrun: cluster or services with IAM bindings
- sql: Cloud SQL Postgres, user/DB, private IP
- artifact_registry: Docker repo
- iam: SAs for workloads with least-privilege IAM roles
- secrets: Secret Manager entries (DB creds, OAuth secrets)
- storage: GCS buckets (logs, opa bundles, exports)
- opa_bundle: optional uploader/build pipeline for policies

Security/IAM
- Workload Identity to avoid long-lived keys
- Secret access via least-privilege roles (Secret Manager Secret Accessor)
- Cloud SQL IAM auth proxy or private IP credentials
- Artifact Registry reader for deployments

Deployment Flow
- Build images → push to Artifact Registry
- Terraform apply infra/env
- Deploy manifests to GKE or Cloud Run (GitHub Actions)
- Smoke test and policy verification
- Promotion from dev to staging/prod via approvals

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

B. Migration Init (services/storage/init.sql)
CREATE TABLE IF NOT EXISTS tool_calls (...);
CREATE TABLE IF NOT EXISTS audit_events (...);

C. Terraform High-Level Example (infra/terraform/envs/dev)
- providers.tf: google and google-beta providers with region/project
- main.tf: call modules (network, sql, artifact_registry, gke/cloudrun, secrets, storage)
- variables.tf: project_id, region, env, cidrs, tiers, buckets
- outputs.tf: endpoint URLs, connection names, SA emails

---

End of PRD.
