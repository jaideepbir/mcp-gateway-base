# Architecture Diagram

Version: 0.1  
Status: Draft

This document presents the target architecture for the MCP Gateway deployment using Docker’s MCP Gateway and OPA for policy enforcement. It mirrors the conceptual approach from the oauth2.0 project but replaces the custom MCP server with Docker’s MCP Gateway.

## High-Level Overview

- Client obtains OAuth2 access token from an OAuth2 provider (can be dev local auth-server or external IdP).
- Client calls MCP Gateway with Bearer token.
- MCP Gateway validates JWT via JWKS and enriches request context.
- MCP Gateway queries OPA for authorization decision (RBAC/ABAC).
- If allowed, gateway forwards to MCP tools (local or remote providers).
- Gateway writes tool-call history and audit events to DB.
- Observability stack ingests logs/metrics/traces.

## Mermaid Diagram (Copy/Paste into Mermaid viewer)

```mermaid
flowchart LR
  subgraph Client
    A[User / App]
  end

  subgraph Auth[OAuth2 Provider]
    I[Authorize / Token]
    J[.well-known/jwks.json]
  end

  subgraph Stack[Docker Compose Stack]
    subgraph GW[MCP Gateway]
      B[JWT Verify (JWKS)]
      C[Context Enrichment]
      D[OPA Query]
      E[Forward to Tool]
      F[History Writer]
    end

    subgraph OPA[Open Policy Agent]
      G[Rego Policies<br/>mcp/authz.rego]
    end

    subgraph DB[(Database)]
      H[(tool_calls, audit_events)]
    end

    subgraph Tools[MCP Tools]
      T1[Tool A]
      T2[Tool B]
    end

    subgraph Obs[Observability (optional)]
      L[OTEL Collector]
      M[Loki/Promtail]
      N[Grafana]
    end
  end

  A -->|Auth Code / CC| I
  I -->|Access Token| A
  B -.-> J
  A -->|Bearer Token| B
  B --> C --> D --> G
  G -->|allow/deny| D
  D -->|allow| E --> T1
  E --> T2
  E --> F --> H
  B -->|metrics/logs| L
  F -->|logs| M --> N
```

## Component Responsibility

- MCP Gateway: JWT verification, OPA authorization, routing to tools, history logging, health checks.
- OPA: Centralized authorization decisions; deny-by-default; fine-grained policies with roles/scopes/labels.
- DB: Persistent store for audit and tool-call history; supports analytics and audits.
- OAuth2 Provider: Issues and signs tokens; exposes JWKS for verification.
- Observability: Collects logs/metrics/traces for monitoring and analytics.

## Data Flows

1) OAuth2 access token issuance (Auth Code/PKCE or Client Credentials).  
2) Request to MCP Gateway with Bearer token.  
3) Gateway verifies JWT and constructs OPA input.  
4) OPA returns allow/deny; gateway enforces decision.  
5) Allowed: call tool, record tool_call entry; Denied: record audit event.  
6) Logs and metrics exported to observability stack.

## Security Notes

- Enforce TLS at the proxy/ingress in production.
- Validate iss, aud, exp, nbf, alg; use JWKS.
- Deny-by-default policy with explicit allows.
- Redact tokens and PII from logs.
