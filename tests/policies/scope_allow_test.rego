package mcp.authz

test_scope_allow {
  allow with input as {
    "user": "testuser",
    "roles": [],
    "scopes": ["testtool:testaction"],
    "resource": {"tool": "testtool", "action": "testaction"},
    "labels": {}
  }
  allow == true
}
