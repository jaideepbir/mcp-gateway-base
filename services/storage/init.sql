CREATE TABLE IF NOT EXISTS tool_calls (
  id uuid PRIMARY KEY,
  user_sub text,
  tool text,
  action text,
  input_json jsonb,
  output_json jsonb,
  decision text,
  reason text,
  created_at timestamptz DEFAULT now(),
  trace_id text
);

CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY,
  user_sub text,
  event_type text,
  details_json jsonb,
  created_at timestamptz DEFAULT now()
);
