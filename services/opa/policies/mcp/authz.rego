package mcp.authz

default allow := false

# Admins always allowed
allow if {
  input.user == "admin"
}

# Allow if any scope matches "<tool>:<action>"
allow if {
  some i
  input.scopes[i] == sprintf("%s:%s", [input.resource.tool, input.resource.action])
}
