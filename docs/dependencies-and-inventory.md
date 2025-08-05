# Dependencies and Inventory

Version: 0.1  
Status: Draft

This document enumerates all dependencies (containers, packages, modules) across the project and provides a complete inventory of components.

## 1. Containers and Services

- mcp-gateway
  - Image: docker/mcp-gateway:latest (per Docker MCP Gateway docs)
  - Purpose: Front-door for Model Context Protocol tools; JWT validation; OPA integration; request routing; history logging.
  - Ports: 8080 (internal), exposed via ${GATEWAY_PORT}
  - Dependencies: OPA, DB, OAuth2 provider (JWKS)

- opa
  - Image: openpolicyagent/opa:latest (pin to a known version in production)
  - Purpose: Policy Decision Point for RBAC/ABAC
  - Ports: 8181
  - Volumes: ./services/opa/policies:/policies:ro

- db
  - Image: postgres:15 (dev/prod) or sqlite (dev-only alternative)
  - Purpose: Tool-call history, audit logs
  - Ports: 5432
  - Volumes: db-data:/var/lib/postgresql/data
  - Init: ./services/storage/init.sql

- auth-server (dev optional)
  - Image: built from ./services/auth-server (FastAPI or similar) or replaced by external IdP
  - Purpose: OAuth2 token issuance for local development
  - Ports: 9000
  - Output: JWKS, tokens with roles/scopes

- observability (optional)
  - otel-collector, loki, promtail, grafana
  - Purpose: Telemetry, central logging, dashboards

- proxy (optional)
  - nginx/traefik/caddy
  - Purpose: TLS termination, rate limiting, headers

## 2. Application Dependencies (by service)

2.1 mcp-gateway
- Provided as container; configured via environment variables
- Expected capabilities:
  - JWT validation using JWKS URI
  - OPA decision request to http://opa:8181/v1/data/mcp/authz/allow
  - Persistence to HISTORY_DB_DSN (Postgres or SQLite)
  - Structured logging, health endpoints
- No local code packages unless we write overlays/wrappers.

2.2 opa
- No application dependencies; pure Rego
- Rego policies under services/opa/policies/mcp/*.rego
- Policy tests under tests/policies/*.rego
- Tooling:
  - opa CLI (for local testing)

2.3 auth-server (dev-only)
- If implemented with FastAPI (Python 3.11+):
  - fastapi
  - uvicorn[standard]
  - python-jose[cryptography] (JWT signing/verification)
  - pydantic
  - httpx (optional)
- Or any minimal OAuth2-compliant server implementation

2.4 storage (DB migrations and client)
- If using alembic (Python) for migrations:
  - alembic
  - psycopg2-binary
- If using plain SQL migrations:
  - No runtime deps; psql client for ops

2.5 tests
- Python-based test runner (if chosen):
  - pytest
  - requests/httpx
  - pytest-asyncio (if needed)
- OPA policy tests:
  - opa (CLI)

2.6 observability (optional)
- OpenTelemetry:
  - otel-collector (container)
- Logging stack:
  - grafana/loki
  - grafana/promtail
  - grafana/grafana

## 3. System Tools

- Docker Engine 24+ and Docker Compose v2+
- make, bash, curl, jq
- psql (Postgres client) or sqlite3 (if using SQLite dev)
- opa (CLI) for policy testing

## 4. Inventory of Directories

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
- tests/
  - integration/
  - policies/
  - health/
- Makefile
- README.md

## 5. Environment Variables (Summary)

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

## 6. Notes

- Pin image tags for production stability.
- External IdP can replace dev auth-server; update OAUTH_* vars accordingly.
- SQLite is acceptable for dev; use Postgres for any multi-user/testing environment.
