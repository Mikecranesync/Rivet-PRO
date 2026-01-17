# Ralph - Autonomous Coding Agent

Ralph is an autonomous coding agent that executes development tasks using Claude API with tool use capabilities. It reads stories from a PostgreSQL database, implements them autonomously, and commits the changes.

## Features

- **Autonomous Execution**: Reads and implements coding tasks without human intervention
- **Tool Use**: Uses Claude API tools to read/write files, run commands, and commit changes
- **Database-Driven**: Stories are queued in PostgreSQL for reliable tracking
- **REST API**: HTTP endpoints for integration with other systems
- **CLI Interface**: Command-line tools for manual operation
- **Cost Tracking**: Monitors token usage and API costs
- **Retry Logic**: Exponential backoff for resilient execution

## Installation

```bash
# Clone the repository
git clone https://github.com/Mikecranesync/Rivet-PRO.git
cd Ralph-Standalone

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

Create a `.env` file with:

```env
DATABASE_URL=postgresql://user:pass@host:5432/database
ANTHROPIC_API_KEY=sk-ant-...
```

## Database Setup

Run the migration to create the required tables:

```bash
psql $DATABASE_URL < migrations/001_ralph_schema.sql
```

## Usage

### CLI

```bash
# Check health
./bin/ralph health

# List pending stories
./bin/ralph story list --status todo

# Add a story
./bin/ralph story add "Implement feature X" --priority 1

# Execute stories
./bin/ralph execute --max 5

# Start API server
./bin/ralph server --port 8765
```

### API

Start the server:
```bash
./bin/ralph-server
```

Then use the endpoints:
```bash
# Health check
curl http://localhost:8765/api/v1/health

# List stories
curl http://localhost:8765/api/v1/stories

# Create story
curl -X POST http://localhost:8765/api/v1/stories \
  -H "Content-Type: application/json" \
  -d '{"story_id": "TASK-001", "title": "Fix bug", "description": "...", "acceptance_criteria": ["test passes"], "priority": 1}'

# Execute
curl -X POST http://localhost:8765/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"max_stories": 1}'
```

### Python

```python
from src.ralph_api import RalphAPI

ralph = RalphAPI(project_root="/path/to/project")

# Get pending stories
stories = ralph.get_pending_stories(max_stories=5)

# Execute a story
success, result = ralph.execute_story(
    story_id="TASK-001",
    title="Implement feature",
    description="...",
    acceptance_criteria="['test passes']",
    priority=1
)
```

## Project Structure

```
Ralph-Standalone/
├── bin/
│   ├── ralph           # CLI entry point
│   └── ralph-server    # API server entry point
├── src/
│   ├── __init__.py
│   ├── ralph_api.py    # Direct API client
│   ├── ralph_local.py  # CLI-based executor
│   ├── ralph_gateway.py# HTTP API gateway
│   └── core/
│       └── orchestrator.py
├── migrations/
│   └── 001_ralph_schema.sql
├── CLAUDE.md           # AI documentation
├── MCP_MANIFEST.json   # MCP tool definitions
├── pyproject.toml
├── requirements.txt
├── VERSION
└── README.md
```

## How It Works

1. **Story Queue**: Stories are stored in `ralph_stories` table with status, priority, and acceptance criteria
2. **Execution**: Ralph fetches the highest-priority `todo` story and marks it `in_progress`
3. **Implementation**: Uses Claude API with tool use to:
   - Read existing code files
   - Write new files or edit existing ones
   - Run commands (tests, builds)
   - Create git commits
4. **Completion**: Updates story status to `done` or `failed`
5. **Repeat**: Continues to next story until queue is empty or limit reached

## Available Tools

Ralph has access to these tools during execution:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Create or overwrite files |
| `edit_file` | Make targeted edits |
| `run_command` | Execute shell commands |
| `complete_story` | Mark story complete with commit |

## API Documentation

When running the server, visit:
- Swagger UI: http://localhost:8765/docs
- ReDoc: http://localhost:8765/redoc

## Version

Current version: 1.0.0

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT License - see LICENSE file for details.
