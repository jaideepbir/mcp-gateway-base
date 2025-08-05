# Dependencies and Inventory

Version: 0.2  
Status: Draft

This document enumerates all dependencies (containers, packages, modules) across the project and provides a complete inventory of components for both local and cloud (GCP) deployments.

## 1. Containers and Services

- mcp-gateway
  - Image: docker/mcp-gateway:latest (per Docker MCP Gateway docs)
  - Purpose: Front-door for Model Context Protocol tools; JWT validation; OPA integration; request routing; history logging.
  - Ports: 8080 (internal), exposed via ${GATEWAY_PORT}
  - Dependencies: OPA, DB, OAuth2 provider (JWKS), network egress to JWKS/IdP, Secret storage for env in cloud

- opa
  - Image: openpolicyagent/opa:latest (pin to a known version in production)
  - Purpose: Policy Decision Point for RBAC/ABAC
  - Ports: 8181
  - Volumes: ./services/opa/policies:/policies:ro (dev) or policy bundles from GCS (cloud)
  - Optional: Decision logs to stdout or OTEL

- db
  - Image: postgres:15 (dev/prod) or sqlite (dev-only alternative)
  - Purpose: Tool-call history, audit logs
  - Ports: 5432
  - Volumes: db-data:/var/lib/postgresql/data
  - Init: ./services/storage/init.sql
  - Cloud: Cloud SQL Postgres, private IP, serverless VPC access/connector

- auth-server (dev optional)
  - Image: built from ./services/auth-server (FastAPI or similar) or replaced by external IdP
  - Purpose: OAuth2 token issuance for local development
  - Ports: 9000
  - Output: JWKS, tokens with roles/scopes

- observability (optional)
  - otel-collector, loki, promtail, grafana
  - Purpose: Telemetry, central logging, dashboards
  - Cloud: Cloud Logging/Monitoring; OTEL exporter to GCP

- proxy/ingress (cloud)
  - GKE Ingress + HTTPS Load Balancer with managed certs, or Cloud Run HTTPS endpoints

## 2. Application Dependencies (by service)

2.1 mcp-gateway
- Provided as container; configured via environment variables
- Expected capabilities:
  - JWT validation using JWKS URI
  - OPA decision request to http://opa:8181/v1/data/mcp/authz/allow
  - Persistence to HISTORY_DB_DSN (Postgres or SQLite)
  - Structured logging, health endpoints
- Cloud specifics:
  - Secrets via Secret Manager (injected as env or mounted files)
  - For GKE: Workload Identity for SA; for Cloud Run: service account attached
  - Connectivity to Cloud SQL via private IP or Cloud SQL Auth Proxy

2.2 opa
- No application dependencies; pure Rego
- Rego policies under services/opa/policies/mcp/*.rego (dev)
- Policy bundles optionally stored in GCS bucket (cloud)
- Tooling:
  - opa CLI (for local testing)

2.3 auth-server (dev-only)
- If implemented with FastAPI (Python 3.11+):
  - fastapi
  - uvicorn[standard]
  - python-jose[cryptography]
  - pydantic
  - httpx (optional)

2.4 storage (DB migrations and client)
- If using alembic (Python) for migrations:
  - alembic
  - psycopg2-binary
- Plain SQL migrations:
  - No runtime deps; psql client for ops

2.5 tests
- Python-based test runner (if chosen):
  - pytest
  - requests/httpx
  - pytest-asyncio (if needed)
- OPA policy tests:
  - opa (CLI)
- Load tests (optional):
  - k6 or artillery

2.6 observability (optional)
- OpenTelemetry:
  - otel-collector (container) or native OTEL in services if supported
- Logging stack:
  - grafana/loki
  - grafana/promtail
  - grafana/grafana
- Cloud alternative: Cloud Logging/Monitoring dashboards

## 3. System Tools

- Docker Engine 24+ and Docker Compose v2+
- make, bash, curl, jq
- psql (Postgres client) or sqlite3 (if using SQLite dev)
- opa (CLI) for policy testing
- terraform >= 1.6.x
- gcloud CLI (Google Cloud SDK)
- tflint, tfsec (optional)
- yq (optional for CI templating)

## 4. Cloud (GCP) Inventory

- VPC with subnets per environment (dev, staging, prod)
- Cloud Router + Cloud NAT for outbound egress
- Artifact Registry for Docker images
- Cloud SQL (Postgres) with private IP
- Secret Manager for OAuth secrets, DB credentials, JWKS override (if any)
- GCS buckets:
  - logs/exports (optional)
  - opa-policy-bundles (optional)
- Container runtime:
  - GKE Autopilot (Workload Identity, Ingress, managed TLS)
  - or Cloud Run (service-level IAM, VPC connector for private SQL)
- IAM:
  - Project-level roles (least privilege)
  - Service accounts (deploy, runtime)
  - Workload Identity pool and bindings for GKE
- Cloud Logging/Monitoring:
  - Dashboards and alerts
  - Sinks to bucket/BigQuery (optional)

## 5. Inventory of Directories

- compose/
  - docker-compose.yml
  - .env.example
- services/
  - gateway/ (optional overlays/config if needed)
  - opa/
    - policies/
      - mcp/
        - authz.rego
    - data/ (optional)
  - auth-server/
    - Dockerfile
    - requirements.txt
    - app/
      - main.py
  - storage/
    - init.sql
    - migrations/
- data/
  - protected/
  - public/
  - uploads/
- docs/
  - PRD.md
  - dependencies-and-inventory.md
  - architecture-diagram.md
  - QUICKSTART.md
  - PDP.md
  - task-tracker.csv
- tests/
  - integration/
  - policies/
  - health/
- infra/
  - terraform/
    - envs/
      - dev/ (providers.tf, main.tf, variables.tf, outputs.tf, backend.tf)
      - staging/
      - prod/
    - modules/
      - network/
      - gke/ or cloudrun/
      - sql/
      - artifact_registry/
      - iam/
      - secrets/
      - storage/
      - opa_bundle/
- Makefile
- README.md

## 6. Environment Variables (Summary)

- Gateway:
  - GATEWAY_PORT, GATEWAY_LOG_LEVEL, GATEWAY_ALLOWED_ORIGINS
  - OAUTH_ISSUER, OAUTH_AUDIENCE, OAUTH_JWKS_URI, OAUTH_REQUIRED_SCOPES
  - RBAC_DEFAULT_ROLE, RBAC_ADMIN_GROUP
  - OPA_URL
  - HISTORY_DB_DSN
- OPA:
  - OPA_LOG_LEVEL, OPA_BUNDLE_URL, OPA_DECISION_PATH
- Auth (dev):
  - AUTH_ISSUER_URL, AUTH_CLIENT_ID, AUTH_CLIENT_SECRET, AUTH_REDIRECT_URI
  - AUTH_JWT_SIGNING_ALG, AUTH_JWKS_PATH
- DB:
  - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
- Observability:
  - OTEL_EXPORTER_OTLP_ENDPOINT, LOG_FORMAT
- Terraform inputs:
  - TF_VAR_project_id, TF_VAR_region, TF_VAR_env, TF_VAR_network_cidr, TF_VAR_subnet_cidrs
  - TF_VAR_sql_instance_tier, TF_VAR_workload_identity_pool, TF_VAR_opa_policy_bucket, TF_VAR_artifact_registry_repo

## 7. Notes

- Pin image tags for production stability.
- External IdP can replace dev auth-server; update OAUTH_* vars accordingly.
- SQLite is acceptable for dev; use Cloud SQL for cloud environments.
- In cloud, avoid storing secrets in Compose/Manifests; use Secret Manager with IAM-bound access.
- Prefer OPA policy bundles from GCS in cloud for controlled rollout and versioning.
