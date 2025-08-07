# OPA Bundle Plan (T-130)

Status: Proposed (dev uses mounted policies; bundle disabled by default)

## Overview
Dev uses a local OPA container mounting policies from the repo:
- Mounted path: services/opa/policies/
- Primary package: mcp.authz (services/opa/policies/mcp/authz.rego)

For cloud, switch to OPA Bundle mode to distribute signed/immutable policy bundles via HTTP/GCS.

## Dev Setup (Mounted Policies)
- OPA loads rego files from the mounted volume.
- Decision logs: enabled to console via services/opa/config.yaml.
- Tests run locally using opa test (see tests/policies).

## Bundle Mode (Cloud)
- Bundle contents (example):
  - roots: ["mcp"]
  - files:
    - mcp/authz.rego
    - (optional) data.json (static attributes)
- Distribution:
  - Preferred: GCS (gs://opa-bundles-dev/bundles/mcp/authz.tar.gz)
  - Alt: HTTPS endpoint (artifact storage, CDN)
- OPA config changes (enable in services/opa/config.yaml):
  bundles:
    example-bundle:
      service: gcs-bundles
      resource: bundles/mcp/authz.tar.gz
      persist: true
      polling:
        min_delay_seconds: 10
        max_delay_seconds: 30
      roots:
        - mcp
- Services config example (for GCS presigned endpoint or proxy):
  services:
    - name: gcs-bundles
      url: https://storage.googleapis.com/opa-bundles-dev
- Signing/Integrity (optional but recommended):
  - Use .manifest and bundle signing; verify signature in OPA (requires additional setup).
- Versioning:
  - Name bundles with semver or commit SHA.
  - Maintain backward compatibility for input contracts.

## OPA Input Contract (Gateway → OPA)
Request example (JSON):
{
  "user": "user_id_or_name",
  "scopes": ["excel:read", "opa:eval"],
  "resource": {
    "tool": "excel",
    "action": "read",
    "labels": ["public"],
    "env": "dev"
  }
}

Ensure parity across gateway code, Rego policy, and tests.

## Policies (Current Baseline)
- Deny by default.
- Admin allow (input.user == "admin").
- Scope allow when any scope matches "<tool>:<action>".

## Roadmap
- Add ABAC refinements (labels/env).
- Add data-driven allow lists via data.json.
- Introduce policy versioning and promotion (dev → staging → prod).

## Validation
- opa test projects/mcp-gateway/tests/policies (Phase 2 T-110).
- Observe decision logs in dev container (T-125).
- Manual query against POST /v1/data/mcp/authz/allow with sample inputs.
