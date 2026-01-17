# Ralph - Autonomous Coding Agent

Ralph is an autonomous coding agent that executes development tasks (stories) using the Claude API with tool use capabilities.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
export DATABASE_URL="postgresql://..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run Ralph
ralph execute --max 5
```

## CLI Commands

```bash
# Version and health
ralph version
ralph health

# Story management
ralph story list
ralph story list --status todo
ralph story status RALPH-001
ralph story add "Implement feature X" --priority 1

# Execution
ralph execute                    # Run up to 5 stories
ralph execute --max 10           # Run up to 10 stories
ralph execute --prefix TASK-     # Only TASK-* stories
ralph execute --story RALPH-001  # Specific story

# API Server
ralph server                     # Start on port 8765
ralph server --port 8080         # Custom port
```

## API Endpoints

Start the server: `ralph server`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/version` | Get version |
| `GET` | `/api/v1/stories` | List stories |
| `POST` | `/api/v1/stories` | Create story |
| `GET` | `/api/v1/stories/{id}` | Get story |
| `PATCH` | `/api/v1/stories/{id}` | Update story |
| `DELETE` | `/api/v1/stories/{id}` | Delete story |
| `POST` | `/api/v1/execute` | Start execution |
| `GET` | `/api/v1/executions` | List executions |
| `GET` | `/api/v1/executions/{id}` | Get execution |

## Python API

```python
from src.ralph_api import RalphAPI

# Initialize
ralph = RalphAPI(project_root="/path/to/project")

# Get pending stories
stories = ralph.get_pending_stories(max_stories=5)

# Execute a story
success, result = ralph.execute_story(
    story_id="RALPH-001",
    title="Implement feature X",
    description="Add new feature...",
    acceptance_criteria="['criteria1', 'criteria2']",
    priority=1
)
```

## Database Schema

Ralph uses PostgreSQL with the following tables:
- `ralph_projects` - Project configurations
- `ralph_stories` - Story queue with status tracking
- `ralph_iterations` - Execution history
- `ralph_executions` - Run metrics

Run migrations: `psql $DATABASE_URL < migrations/001_ralph_schema.sql`

## How Ralph Works

1. **Fetches stories** from the `ralph_stories` database table
2. **Executes each story** using Claude API with tool use:
   - `read_file` - Read project files
   - `write_file` - Create/overwrite files
   - `edit_file` - Make targeted edits
   - `run_command` - Execute shell commands
   - `complete_story` - Mark completion with commit
3. **Commits changes** to git with descriptive messages
4. **Updates status** in database (done/failed)
5. **Repeats** until all stories are processed

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |

## This Tool Can

- Execute coding tasks autonomously
- Read and modify source code files
- Run shell commands (tests, builds, git)
- Track progress via database stories
- Generate git commits with proper messages
- Expose REST API for integration
- Handle retries with exponential backoff
- Track costs and token usage

## Limitations

- Requires PostgreSQL database
- Requires Anthropic API key
- One story at a time (serial execution)
- 15-minute timeout per story
- No interactive prompts during execution

## Integration with Other AI Agents

Ralph exposes an HTTP API that other AI agents can call:

```bash
# Health check
curl http://localhost:8765/api/v1/health

# Queue a story
curl -X POST http://localhost:8765/api/v1/stories \
  -H "Content-Type: application/json" \
  -d '{"story_id": "TASK-001", "title": "Fix bug", "description": "...", "acceptance_criteria": ["test passes"], "priority": 1}'

# Start execution
curl -X POST http://localhost:8765/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"max_stories": 1, "story_id": "TASK-001"}'

# Check execution status
curl http://localhost:8765/api/v1/executions/{execution_id}
```

## MCP Tool Registration

See `MCP_MANIFEST.json` for MCP-compatible tool definitions.
