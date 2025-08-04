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

allow {
  is_admin
}

allow {
  tool_action_allowed
}
