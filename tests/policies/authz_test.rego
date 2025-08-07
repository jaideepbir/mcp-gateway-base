package mcp.authz_test

import data.mcp.authz.allow

# Admins always allowed
test_admin_allowed {
  input := {
    "user": "admin",
    "scopes": [],
    "resource": {"tool": "excel", "action": "read"}
  }
  allow with input as input
}

# Correct scope allows: "<tool>:<action>"
test_scope_allows {
  input := {
    "user": "demo",
    "scopes": ["excel:read", "opa:eval"],
    "resource": {"tool": "excel", "action": "read"}
  }
  allow with input as input
}

# Missing scope denies for non-admin
test_missing_scope_denies {
  input := {
    "user": "demo",
    "scopes": ["excel:write"],
    "resource": {"tool": "excel", "action": "read"}
  }
  not allow with input as input
}

# Different tool/action denies
test_wrong_scope_denies {
  input := {
    "user": "demo",
    "scopes": ["opa:eval"],
    "resource": {"tool": "excel", "action": "read"}
  }
  not allow with input as input
}

# No scopes for non-admin denies
test_no_scopes_denies {
  input := {
    "user": "user1",
    "scopes": [],
    "resource": {"tool": "excel", "action": "read"}
  }
  not allow with input as input
}
