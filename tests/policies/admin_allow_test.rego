package mcp.authz

test_admin_allow {
  allow with input as {
    "user": "admin",
    "roles": ["admin"],
    "scopes": [],
    "resource": {"tool": "testtool", "action": "testaction"},
    "labels": {}
  }
  allow == true
}
