INSERT INTO ralph_stories (
  project_id,
  story_id,
  title,
  description,
  acceptance_criteria,
  status,
  priority,
  preferred_model
) VALUES (
  1,
  'RIVET-TEST-001',
  'Database Health Check Endpoint',
  'Create a simple /health endpoint that checks database connectivity and returns status. This validates Ralph can implement features end-to-end.',
  '{"criteria": ["Endpoint responds at GET /health", "Returns JSON with database status", "Returns 200 if DB connected, 503 if not", "Commits code with message: feat(RIVET-TEST-001): Add health check endpoint"]}',
  'todo',
  -1,
  'claude-sonnet-4-20250514'
);
