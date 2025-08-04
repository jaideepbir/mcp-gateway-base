# QUICKSTART

Version: 0.1  
Status: Draft

This Quickstart brings up a local stack of MCP Gateway + OPA + Postgres (and optional dev OAuth2 server) using Docker Compose. It verifies JWTs, evaluates OPA policies, and persists tool-call history.

Prereqs
- macOS/Linux/Windows with Docker Engine 24+ and Docker Compose v2+
- make, bash, curl, jq
- Optional: psql (Postgres client), opa (CLI)

Project Layout (excerpt)
- compose/docker-compose.yml
- services/opa/policies/mcp/authz.rego
- services/storage/init.sql
- docs/ (this file, PRD, architecture, dependencies)
- tests/ (policy tests, integration, health)

1) Clone and configure
git clone https://github.com/jaideepbir/mcp-gateway-base.git mcp-gateway
cd mcp-gateway
cp compose/.env.example compose/.env
# Edit compose/.env to set:
# - GATEWAY_PORT=8080
# - OAUTH_ISSUER, OAUTH_AUDIENCE, OAUTH_JWKS_URI
# - POSTGRES_* and HISTORY_DB_DSN
# If you do not have an external IdP, you can keep placeholders and later enable the dev auth-server.

2) Start the core stack
docker compose -f compose/docker-compose.yml up -d
docker compose ps

Core services:
- mcp-gateway: http://localhost:${GATEWAY_PORT:-8080}
- opa: http://localhost:8181
- db: localhost:5432 (Postgres)

3) Health checks
# Gateway health (should be 200)
curl -i http://localhost:${GATEWAY_PORT:-8080}/health

# OPA health
curl -i http://localhost:8181/health

# DB connectivity (optional; requires psql)
psql "postgresql://mcp:changeme@localhost:5432/mcp" -c '\dt' || true

4) Configure OAuth2 (external or dev)
Option A: External IdP
- Ensure compose/.env has valid:
  OAUTH_ISSUER=https://<issuer>
  OAUTH_AUDIENCE=<audience>
  OAUTH_JWKS_URI=https://<issuer>/.well-known/jwks.json
- Obtain an access token from your provider and export it:
  export ACCESS_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

Option B: Dev local auth-server (optional)
- Enable auth-server service in compose (if provided in this repo).
- Set:
  OAUTH_ISSUER=http://auth-server:9000
  OAUTH_AUDIENCE=mcp-gateway
  OAUTH_JWKS_URI=http://auth-server:9000/jwks.json
- Recreate stack:
  docker compose down && docker compose up -d
- Obtain a token from the dev auth-server instructions and export it as ACCESS_TOKEN.

5) Validate OPA policy decisions
# Example: OPA raw decision (replace inputs to match your token claims)
curl -s -X POST "http://localhost:8181/v1/data/mcp/authz/allow" \
  -H "Content-Type: application/json" \
  -d '{
        "input": {
          "method": "POST",
          "path": "/tools/excel/invoke",
          "user": {
            "sub": "user-123",
            "roles": ["user"],
            "scopes": ["tool:excel:read"]
          },
          "resource": { "tool": "excel", "action": "read" },
          "env": "dev"
        }
      }'

# Expected: {"result": true} when policy allows.

6) Invoke MCP Gateway (example)
# Replace endpoint and payload with valid MCP Gateway route as documented.
# The real endpoint and request shape depend on the Docker MCP Gateway API.
curl -s -X POST "http://localhost:${GATEWAY_PORT:-8080}/tools/excel/invoke" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"args": {"path": "data/public/sample.csv"}}' | jq .

Notes:
- If policy denies, expect 403 and an audit event to be written.
- On allow, gateway forwards to the tool and persists a tool_call record.

7) Logs and troubleshooting
# Show all logs
docker compose logs -f

# Show OPA decision logs (if enabled)
docker compose logs opa

# Inspect DB tables
psql "postgresql://mcp:changeme@localhost:5432/mcp" -c "select * from tool_calls order by created_at desc limit 5;" || true

8) Policy development loop
- Edit services/opa/policies/mcp/authz.rego
- Add/modify tests in tests/policies/*.rego
- Run tests (requires opa CLI locally):
  opa test services/opa/policies/mcp/ tests/policies/

- Reload policies by restarting OPA or using bundles. For local dev with mounted policies:
  docker compose restart opa

9) Teardown
docker compose down -v

Appendix A: Example environment (compose/.env.example)
COMPOSE_PROJECT_NAME=mcp-gateway
ENV=dev
TZ=UTC
GATEWAY_PORT=8080
GATEWAY_LOG_LEVEL=info
GATEWAY_ALLOWED_ORIGINS=*
OAUTH_ISSUER=https://example-issuer
OAUTH_AUDIENCE=mcp-gateway
OAUTH_JWKS_URI=https://example-issuer/.well-known/jwks.json
OAUTH_REQUIRED_SCOPES=mcp:read,mcp:write
RBAC_DEFAULT_ROLE=user
RBAC_ADMIN_GROUP=admin
RATE_LIMIT_RPS=20
HISTORY_DB_DSN=postgresql://mcp:changeme@db:5432/mcp?sslmode=disable
OPA_LOG_LEVEL=info
OPA_DECISION_PATH=/mcp/authz/allow
POSTGRES_DB=mcp
POSTGRES_USER=mcp
POSTGRES_PASSWORD=changeme
POSTGRES_HOST=db
POSTGRES_PORT=5432
OTEL_EXPORTER_OTLP_ENDPOINT=
LOG_FORMAT=json

Appendix B: SQL init (services/storage/init.sql)
See PRD and SQL snippet; this file is mounted into the DB container by compose.

Appendix C: Known issues
- If Gateway returns 401/403, verify ACCESS_TOKEN, JWT iss/aud, and JWKS URI.
- If OPA is unreachable, check compose networking and opa logs.
- For SQLite, update HISTORY_DB_DSN accordingly and ensure a writable volume.
