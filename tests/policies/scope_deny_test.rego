package mcp.authz

test_scope_deny {
  allow with input as {
    "user": "testuser",
    "roles": [],
    "scopes": [],
    "resource": {"tool": "testtool", "action": "testaction"},
    "labels": {}
  }
  allow == false
}
