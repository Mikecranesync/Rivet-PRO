# CLAUDE CODE CLI PROMPT - RALPH WITH DATABASE AUTO-DETECT
# Copy everything below and paste into Claude Code CLI on your VPS

---

Set up the Ralph autonomous story implementation system on this VPS. Ralph reads stories from PostgreSQL, uses Claude Code CLI to implement each story, commits the code, and sends Telegram notifications.

CRITICAL: Ralph must auto-detect which databases are available and use them with fallback support. The user may have Supabase, Neon, Railway, or local PostgreSQL. Find all of them, test connections, designate one as primary, and use others as fallbacks.

## INFRASTRUCTURE DETAILS

VPS IP: 72.60.175.144
n8n running on port 5678
Telegram bot: @rivet_local_dev_bot
Project: RIVET Pro (AI maintenance assistant for field technicians)

## TASK 1: CREATE DIRECTORY STRUCTURE

Create the following in /root/ralph/:

```
/root/ralph/
├── scripts/
│   ├── ralph_loop.sh          # Main loop script
│   ├── run_story.sh           # Implements single story
│   ├── notify_telegram.sh     # Sends Telegram messages
│   ├── check_status.sh        # Check Ralph status
│   ├── db_manager.sh          # Database connection manager
│   ├── detect_databases.sh    # Auto-detect available databases
│   └── sync_databases.sh      # Sync data between databases
├── config/
│   ├── .env.template          # Environment template
│   ├── databases.conf         # Detected database configs
│   └── primary.conf           # Current primary database
├── logs/
│   └── .gitkeep
└── README.md
```

## TASK 2: CREATE DATABASE DETECTION SCRIPT

Create /root/ralph/scripts/detect_databases.sh:

```bash
#!/bin/bash
# Auto-detect all available PostgreSQL databases
# Checks: Supabase, Neon, Railway, Local PostgreSQL
# Creates databases.conf with all working connections

CONFIG_DIR="/root/ralph/config"
DATABASES_CONF="$CONFIG_DIR/databases.conf"
PRIMARY_CONF="$CONFIG_DIR/primary.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "[$(date '+%H:%M:%S')] $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

# Initialize config file
echo "# Ralph Database Configuration" > "$DATABASES_CONF"
echo "# Auto-generated on $(date)" >> "$DATABASES_CONF"
echo "# Format: NAME|URL|PRIORITY|STATUS" >> "$DATABASES_CONF"
echo "" >> "$DATABASES_CONF"

FOUND_DBS=0
declare -a WORKING_DBS

test_connection() {
  local name=$1
  local url=$2
  local timeout=${3:-5}
  
  log "Testing $name..."
  
  # Test with psql, timeout after N seconds
  if timeout $timeout psql "$url" -c "SELECT 1;" > /dev/null 2>&1; then
    success "$name is accessible"
    return 0
  else
    fail "$name is not accessible"
    return 1
  fi
}

# Check for environment variables that might contain database URLs
log "Scanning for database connection strings..."

# Common environment variable names for different providers
ENV_PATTERNS=(
  "DATABASE_URL"
  "POSTGRES_URL"
  "SUPABASE_DB_URL"
  "SUPABASE_URL"
  "NEON_DATABASE_URL"
  "NEON_URL"
  "RAILWAY_DATABASE_URL"
  "PG_CONNECTION_STRING"
  "PGURL"
)

# Check current environment
for pattern in "${ENV_PATTERNS[@]}"; do
  url="${!pattern}"
  if [ -n "$url" ]; then
    log "Found \$$pattern"
    if test_connection "$pattern" "$url"; then
      # Detect provider from URL
      provider="unknown"
      if [[ "$url" == *"supabase"* ]]; then
        provider="supabase"
      elif [[ "$url" == *"neon"* ]]; then
        provider="neon"
      elif [[ "$url" == *"railway"* ]]; then
        provider="railway"
      elif [[ "$url" == *"localhost"* ]] || [[ "$url" == *"127.0.0.1"* ]]; then
        provider="local"
      fi
      
      WORKING_DBS+=("$provider|$pattern|$url")
      FOUND_DBS=$((FOUND_DBS + 1))
    fi
  fi
done

# Check common .env files
ENV_FILES=(
  "/root/.env"
  "/root/ralph/config/.env"
  "/root/rivet-pro/.env"
  "/root/Agent-Factory/.env"
  "$HOME/.env"
  "./.env"
)

for env_file in "${ENV_FILES[@]}"; do
  if [ -f "$env_file" ]; then
    log "Scanning $env_file..."
    while IFS='=' read -r key value; do
      # Skip comments and empty lines
      [[ "$key" =~ ^#.*$ ]] && continue
      [[ -z "$key" ]] && continue
      
      # Remove quotes from value
      value=$(echo "$value" | tr -d '"' | tr -d "'")
      
      # Check if it looks like a database URL
      if [[ "$value" == postgres://* ]] || [[ "$value" == postgresql://* ]]; then
        log "Found potential DB in $env_file: $key"
        
        # Check if we already have this URL
        already_found=false
        for db in "${WORKING_DBS[@]}"; do
          if [[ "$db" == *"$value"* ]]; then
            already_found=true
            break
          fi
        done
        
        if [ "$already_found" = false ]; then
          if test_connection "$key" "$value"; then
            provider="unknown"
            if [[ "$value" == *"supabase"* ]]; then
              provider="supabase"
            elif [[ "$value" == *"neon"* ]]; then
              provider="neon"
            elif [[ "$value" == *"railway"* ]]; then
              provider="railway"
            elif [[ "$value" == *"localhost"* ]] || [[ "$value" == *"127.0.0.1"* ]]; then
              provider="local"
            fi
            
            WORKING_DBS+=("$provider|$key|$value")
            FOUND_DBS=$((FOUND_DBS + 1))
          fi
        fi
      fi
    done < "$env_file"
  fi
done

# Check for local PostgreSQL
log "Checking for local PostgreSQL..."
if command -v pg_isready &> /dev/null; then
  if pg_isready -q 2>/dev/null; then
    success "Local PostgreSQL is running"
    
    # Try common local connection strings
    LOCAL_URLS=(
      "postgresql://postgres:postgres@localhost:5432/postgres"
      "postgresql://localhost:5432/postgres"
      "postgresql://postgres@localhost:5432/postgres"
    )
    
    for local_url in "${LOCAL_URLS[@]}"; do
      if test_connection "local_postgres" "$local_url" 2; then
        WORKING_DBS+=("local|LOCAL_POSTGRES|$local_url")
        FOUND_DBS=$((FOUND_DBS + 1))
        break
      fi
    done
  else
    warn "Local PostgreSQL not running"
  fi
fi

# Check Docker for PostgreSQL containers
if command -v docker &> /dev/null; then
  log "Checking Docker for PostgreSQL containers..."
  DOCKER_PG=$(docker ps --filter "ancestor=postgres" --format "{{.Names}}" 2>/dev/null)
  
  if [ -n "$DOCKER_PG" ]; then
    for container in $DOCKER_PG; do
      log "Found Docker PostgreSQL: $container"
      # Get container port
      port=$(docker port "$container" 5432 2>/dev/null | cut -d: -f2)
      if [ -n "$port" ]; then
        docker_url="postgresql://postgres:postgres@localhost:$port/postgres"
        if test_connection "docker_$container" "$docker_url" 2; then
          WORKING_DBS+=("docker|DOCKER_$container|$docker_url")
          FOUND_DBS=$((FOUND_DBS + 1))
        fi
      fi
    done
  fi
fi

echo ""
echo "========================================"
echo "DATABASE DETECTION COMPLETE"
echo "========================================"
echo ""

if [ $FOUND_DBS -eq 0 ]; then
  fail "No working databases found!"
  echo ""
  echo "Please set up at least one database connection."
  echo "Add to /root/ralph/config/.env:"
  echo "  DATABASE_URL=postgresql://user:pass@host:5432/dbname"
  exit 1
fi

echo "Found $FOUND_DBS working database(s):"
echo ""

# Write to config and select primary
PRIORITY=1
PRIMARY_SET=false

for db in "${WORKING_DBS[@]}"; do
  IFS='|' read -r provider varname url <<< "$db"
  
  # Mask password in display
  display_url=$(echo "$url" | sed 's/:[^@]*@/:****@/')
  
  echo "  $PRIORITY. [$provider] $varname"
  echo "     $display_url"
  echo ""
  
  # Write to config
  echo "${provider}|${varname}|${url}|${PRIORITY}|active" >> "$DATABASES_CONF"
  
  # First one is primary (prefer cloud over local)
  if [ "$PRIMARY_SET" = false ]; then
    if [[ "$provider" == "neon" ]] || [[ "$provider" == "supabase" ]] || [[ "$provider" == "railway" ]]; then
      echo "$provider|$varname|$url" > "$PRIMARY_CONF"
      PRIMARY_SET=true
      success "Primary database: $provider ($varname)"
    fi
  fi
  
  PRIORITY=$((PRIORITY + 1))
done

# If no cloud DB, use first available as primary
if [ "$PRIMARY_SET" = false ]; then
  IFS='|' read -r provider varname url <<< "${WORKING_DBS[0]}"
  echo "$provider|$varname|$url" > "$PRIMARY_CONF"
  success "Primary database: $provider ($varname)"
fi

echo ""
echo "Configuration saved to:"
echo "  $DATABASES_CONF"
echo "  $PRIMARY_CONF"
echo ""
echo "Run './scripts/db_manager.sh status' to check connections"
```

## TASK 3: CREATE DATABASE MANAGER SCRIPT

Create /root/ralph/scripts/db_manager.sh:

```bash
#!/bin/bash
# Database connection manager with fallback support
# Usage: 
#   source db_manager.sh
#   db_query "SELECT * FROM stories"
#   db_execute "UPDATE stories SET status='done' WHERE id=1"

CONFIG_DIR="/root/ralph/config"
DATABASES_CONF="$CONFIG_DIR/databases.conf"
PRIMARY_CONF="$CONFIG_DIR/primary.conf"

# Load primary database
load_primary() {
  if [ ! -f "$PRIMARY_CONF" ]; then
    echo "ERROR: No primary database configured. Run detect_databases.sh first."
    return 1
  fi
  
  IFS='|' read -r DB_PROVIDER DB_VARNAME DB_URL < "$PRIMARY_CONF"
  export DATABASE_URL="$DB_URL"
  export DB_PROVIDER
  export DB_VARNAME
}

# Get all database URLs as array
get_all_databases() {
  local -a dbs=()
  while IFS='|' read -r provider varname url priority status; do
    [[ "$provider" =~ ^#.*$ ]] && continue
    [[ -z "$provider" ]] && continue
    [[ "$status" == "active" ]] && dbs+=("$provider|$url")
  done < "$DATABASES_CONF"
  echo "${dbs[@]}"
}

# Test if a database is reachable
test_db() {
  local url=$1
  timeout 3 psql "$url" -c "SELECT 1;" > /dev/null 2>&1
}

# Execute query with fallback
db_query() {
  local query=$1
  local result=""
  
  # Try primary first
  load_primary
  if test_db "$DATABASE_URL"; then
    result=$(psql "$DATABASE_URL" -t -A -F $'\t' -c "$query" 2>/dev/null)
    if [ $? -eq 0 ]; then
      echo "$result"
      return 0
    fi
  fi
  
  # Primary failed, try fallbacks
  echo "WARNING: Primary database failed, trying fallbacks..." >&2
  
  while IFS='|' read -r provider varname url priority status; do
    [[ "$provider" =~ ^#.*$ ]] && continue
    [[ -z "$provider" ]] && continue
    [[ "$url" == "$DATABASE_URL" ]] && continue  # Skip primary
    
    if test_db "$url"; then
      result=$(psql "$url" -t -A -F $'\t' -c "$query" 2>/dev/null)
      if [ $? -eq 0 ]; then
        echo "SUCCESS: Using fallback $provider" >&2
        echo "$result"
        return 0
      fi
    fi
  done < "$DATABASES_CONF"
  
  echo "ERROR: All databases failed!" >&2
  return 1
}

# Execute write query with replication to all databases
db_execute() {
  local query=$1
  local replicate=${2:-true}  # Replicate to all DBs by default
  local success_count=0
  local fail_count=0
  
  # Try primary first
  load_primary
  if test_db "$DATABASE_URL"; then
    if psql "$DATABASE_URL" -c "$query" > /dev/null 2>&1; then
      ((success_count++))
    else
      ((fail_count++))
      echo "WARNING: Primary database write failed" >&2
    fi
  else
    ((fail_count++))
    echo "WARNING: Primary database unreachable" >&2
  fi
  
  # Replicate to other databases if requested
  if [ "$replicate" = true ]; then
    while IFS='|' read -r provider varname url priority status; do
      [[ "$provider" =~ ^#.*$ ]] && continue
      [[ -z "$provider" ]] && continue
      [[ "$url" == "$DATABASE_URL" ]] && continue  # Skip primary
      [[ "$status" != "active" ]] && continue
      
      if test_db "$url"; then
        if psql "$url" -c "$query" > /dev/null 2>&1; then
          ((success_count++))
        else
          ((fail_count++))
        fi
      else
        ((fail_count++))
      fi
    done < "$DATABASES_CONF"
  fi
  
  if [ $success_count -gt 0 ]; then
    echo "Write succeeded on $success_count database(s)" >&2
    return 0
  else
    echo "ERROR: Write failed on all databases!" >&2
    return 1
  fi
}

# Show status of all databases
db_status() {
  echo "========================================"
  echo "DATABASE STATUS"
  echo "========================================"
  echo ""
  
  load_primary
  echo "Primary: $DB_PROVIDER ($DB_VARNAME)"
  if test_db "$DATABASE_URL"; then
    echo "  Status: ✓ Connected"
  else
    echo "  Status: ✗ Unreachable"
  fi
  echo ""
  
  echo "All Databases:"
  while IFS='|' read -r provider varname url priority status; do
    [[ "$provider" =~ ^#.*$ ]] && continue
    [[ -z "$provider" ]] && continue
    
    display_url=$(echo "$url" | sed 's/:[^@]*@/:****@/')
    
    if test_db "$url"; then
      echo "  ✓ [$provider] $varname - Connected"
    else
      echo "  ✗ [$provider] $varname - Unreachable"
    fi
  done < "$DATABASES_CONF"
}

# Initialize schema on all databases
db_init_schema() {
  echo "Initializing Ralph schema on all databases..."
  
  local schema="
    CREATE TABLE IF NOT EXISTS ralph_projects (
      id SERIAL PRIMARY KEY,
      project_name VARCHAR(255) NOT NULL,
      max_iterations INTEGER DEFAULT 50,
      token_budget INTEGER DEFAULT 500000,
      telegram_chat_id VARCHAR(100),
      created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ralph_stories (
      id SERIAL PRIMARY KEY,
      project_id INTEGER REFERENCES ralph_projects(id),
      story_id VARCHAR(50) NOT NULL,
      title VARCHAR(255) NOT NULL,
      description TEXT,
      acceptance_criteria JSONB,
      status VARCHAR(20) DEFAULT 'todo',
      status_emoji VARCHAR(10) DEFAULT '⬜',
      priority INTEGER DEFAULT 0,
      commit_hash VARCHAR(100),
      error_message TEXT,
      retry_count INTEGER DEFAULT 0,
      started_at TIMESTAMP,
      completed_at TIMESTAMP,
      created_at TIMESTAMP DEFAULT NOW(),
      UNIQUE(project_id, story_id)
    );

    CREATE TABLE IF NOT EXISTS ralph_iterations (
      id SERIAL PRIMARY KEY,
      project_id INTEGER,
      story_id INTEGER,
      execution_id INTEGER,
      iteration_number INTEGER,
      status VARCHAR(20),
      commit_hash VARCHAR(100),
      tokens_used INTEGER,
      error_message TEXT,
      created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ralph_executions (
      id SERIAL PRIMARY KEY,
      project_id INTEGER,
      started_at TIMESTAMP DEFAULT NOW(),
      completed_at TIMESTAMP,
      total_iterations INTEGER DEFAULT 0,
      total_tokens INTEGER DEFAULT 0,
      stories_completed INTEGER DEFAULT 0,
      stories_failed INTEGER DEFAULT 0,
      status VARCHAR(20) DEFAULT 'running',
      stop_reason VARCHAR(100)
    );

    CREATE INDEX IF NOT EXISTS idx_stories_status ON ralph_stories(project_id, status);
  "
  
  db_execute "$schema" true
}

# Command line interface
case "${1:-}" in
  status)
    db_status
    ;;
  init)
    db_init_schema
    ;;
  query)
    db_query "$2"
    ;;
  exec)
    db_execute "$2"
    ;;
  *)
    # If sourced, just load functions
    if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
      load_primary
    else
      echo "Usage: db_manager.sh {status|init|query|exec}"
      echo "  status - Show all database connections"
      echo "  init   - Initialize schema on all databases"
      echo "  query  - Run SELECT query with fallback"
      echo "  exec   - Run write query with replication"
    fi
    ;;
esac
```

## TASK 4: CREATE SYNC SCRIPT

Create /root/ralph/scripts/sync_databases.sh:

```bash
#!/bin/bash
# Sync Ralph data between all configured databases
# Useful for recovery or keeping backups in sync

source /root/ralph/scripts/db_manager.sh

echo "========================================"
echo "DATABASE SYNC"
echo "========================================"

load_primary

echo "Primary: $DB_PROVIDER"
echo ""

# Export from primary
echo "Exporting from primary..."
EXPORT_FILE="/tmp/ralph_sync_$(date +%Y%m%d_%H%M%S).sql"

pg_dump "$DATABASE_URL" \
  --table=ralph_projects \
  --table=ralph_stories \
  --table=ralph_iterations \
  --table=ralph_executions \
  --data-only \
  --inserts \
  > "$EXPORT_FILE" 2>/dev/null

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to export from primary"
  exit 1
fi

echo "Exported to $EXPORT_FILE"
echo ""

# Import to all other databases
echo "Syncing to other databases..."

while IFS='|' read -r provider varname url priority status; do
  [[ "$provider" =~ ^#.*$ ]] && continue
  [[ -z "$provider" ]] && continue
  [[ "$url" == "$DATABASE_URL" ]] && continue
  [[ "$status" != "active" ]] && continue
  
  echo -n "  $provider: "
  
  if test_db "$url"; then
    # Clear existing data and import
    psql "$url" -c "TRUNCATE ralph_iterations, ralph_executions, ralph_stories, ralph_projects CASCADE;" > /dev/null 2>&1
    psql "$url" -f "$EXPORT_FILE" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
      echo "✓ Synced"
    else
      echo "✗ Import failed"
    fi
  else
    echo "✗ Unreachable"
  fi
done < "$DATABASES_CONF"

rm -f "$EXPORT_FILE"

echo ""
echo "Sync complete."
```

## TASK 5: CREATE TELEGRAM NOTIFICATION SCRIPT

Create /root/ralph/scripts/notify_telegram.sh:

```bash
#!/bin/bash
# Send message to Telegram
# Usage: ./notify_telegram.sh "Your message here"

# Try to load from config, fallback to environment
if [ -f /root/ralph/config/.env ]; then
  source /root/ralph/config/.env
fi

MESSAGE="$1"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "WARNING: Telegram not configured, skipping notification"
  exit 0
fi

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "text=${MESSAGE}" \
  -d "parse_mode=Markdown" \
  > /dev/null
```

## TASK 6: CREATE THE SINGLE STORY RUNNER

Create /root/ralph/scripts/run_story.sh:

```bash
#!/bin/bash
# Run Claude Code CLI on a single story
# Usage: ./run_story.sh "STORY_ID" "STORY_TITLE" "DESCRIPTION" "CRITERIA"

set -e

# Load config
if [ -f /root/ralph/config/.env ]; then
  source /root/ralph/config/.env
fi

STORY_ID="$1"
STORY_TITLE="$2"
DESCRIPTION="$3"
CRITERIA="$4"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/root/ralph/logs/${STORY_ID}_${TIMESTAMP}.log"

# Default project path
PROJECT_PATH="${PROJECT_PATH:-/root/rivet-pro}"

cd "$PROJECT_PATH"

# Build the prompt
PROMPT="You are implementing a feature for RIVET Pro, an AI-powered maintenance assistant for field technicians.

## Story: ${STORY_ID}
## Title: ${STORY_TITLE}

## Description
${DESCRIPTION}

## Acceptance Criteria
${CRITERIA}

## Context
- This is an n8n-based system on VPS 72.60.175.144:5678
- Database is PostgreSQL (auto-detected, with fallbacks)
- Telegram bot for user interface
- Keep code SIMPLE - field techs need FAST responses
- Use existing patterns in the codebase
- DO NOT over-engineer or refactor unrelated code

## Instructions
1. Implement this feature completely
2. Test that it works
3. Commit with message: feat(${STORY_ID}): ${STORY_TITLE}

When done, output a JSON summary:
{
  \"success\": true,
  \"commit_hash\": \"the-commit-hash\",
  \"files_changed\": [\"list\", \"of\", \"files\"],
  \"notes\": \"Brief description of what was implemented\"
}

If blocked:
{
  \"success\": false,
  \"error_message\": \"What went wrong\",
  \"notes\": \"What needs to happen to unblock\"
}"

echo "Starting implementation of ${STORY_ID} at $(date)" | tee "$LOG_FILE"

# Execute Claude Code with the prompt
OUTPUT=$(claude --print "$PROMPT" 2>&1) || true

echo "$OUTPUT" >> "$LOG_FILE"

# Try to extract JSON result from output
RESULT=$(echo "$OUTPUT" | grep -o '{.*}' | tail -1) || RESULT='{"success": false, "error_message": "Could not parse output"}'

echo "$RESULT"
```

## TASK 7: CREATE THE MAIN RALPH LOOP

Create /root/ralph/scripts/ralph_loop.sh:

```bash
#!/bin/bash
# Ralph Main Loop - Autonomous story implementation
# Usage: ./ralph_loop.sh [max_iterations]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load config
if [ -f /root/ralph/config/.env ]; then
  source /root/ralph/config/.env
fi

# Load database manager
source "$SCRIPT_DIR/db_manager.sh"

MAX="${1:-${MAX_ITERATIONS:-50}}"
PROJECT_ID="${PROJECT_ID:-1}"
ITERATION=0
COMPLETED=0
FAILED=0

# Status emoji mapping
emoji_todo="⬜"
emoji_progress="🟡"
emoji_done="✅"
emoji_failed="🔴"
emoji_blocked="❌"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

update_story_status() {
  local story_id=$1
  local new_status=$2
  local commit_hash=$3
  local error_msg=$4
  
  local emoji
  case $new_status in
    todo) emoji="$emoji_todo" ;;
    in_progress) emoji="$emoji_progress" ;;
    done) emoji="$emoji_done" ;;
    failed) emoji="$emoji_failed" ;;
    blocked) emoji="$emoji_blocked" ;;
  esac
  
  # Use db_execute for write with replication
  db_execute "
    UPDATE ralph_stories SET 
      status = '$new_status',
      status_emoji = '$emoji',
      commit_hash = $([ -n "$commit_hash" ] && echo "'$commit_hash'" || echo "NULL"),
      error_message = $([ -n "$error_msg" ] && echo "'${error_msg//\'/\'\'}'" || echo "NULL"),
      completed_at = CASE WHEN '$new_status' = 'done' THEN NOW() ELSE completed_at END,
      retry_count = CASE WHEN '$new_status' = 'failed' THEN retry_count + 1 ELSE retry_count END
    WHERE id = $story_id;
  "
}

get_next_story() {
  # Use db_query for read with fallback
  db_query "
    SELECT id, story_id, title, description, acceptance_criteria::text
    FROM ralph_stories 
    WHERE project_id = $PROJECT_ID 
      AND status = 'todo' 
      AND retry_count < 3
    ORDER BY priority ASC 
    LIMIT 1;
  "
}

# Check database connection first
log "Checking database connections..."
db_status

# Send start notification
"$SCRIPT_DIR/notify_telegram.sh" "🚀 *RALPH STARTING*
━━━━━━━━━━━━━━━━━━
Project: RIVET Pro
Database: $DB_PROVIDER
Max iterations: $MAX
Time: $(date '+%Y-%m-%d %H:%M')
━━━━━━━━━━━━━━━━━━"

log "Ralph starting. Primary DB: $DB_PROVIDER. Max iterations: $MAX"

while [ $ITERATION -lt $MAX ]; do
  ITERATION=$((ITERATION + 1))
  
  # Get next story
  STORY=$(get_next_story)
  
  if [ -z "$STORY" ]; then
    log "No more stories to process"
    "$SCRIPT_DIR/notify_telegram.sh" "✅ *All stories completed!*"
    break
  fi
  
  # Parse story fields (tab-separated)
  IFS=$'\t' read -r DB_ID STORY_ID TITLE DESCRIPTION CRITERIA <<< "$STORY"
  
  log "Iteration $ITERATION: Processing $STORY_ID - $TITLE"
  
  # Mark in progress (replicated to all DBs)
  update_story_status "$DB_ID" "in_progress" "" ""
  
  # Notify start
  "$SCRIPT_DIR/notify_telegram.sh" "🟡 *Iteration $ITERATION*
━━━━━━━━━━━━━━━━━━
Story: \`$STORY_ID\`
$TITLE
DB: $DB_PROVIDER
━━━━━━━━━━━━━━━━━━"
  
  # Run the story implementation
  START_TIME=$(date +%s)
  RESULT=$("$SCRIPT_DIR/run_story.sh" "$STORY_ID" "$TITLE" "$DESCRIPTION" "$CRITERIA") || RESULT='{"success": false, "error_message": "Script execution failed"}'
  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))
  
  # Parse result
  SUCCESS=$(echo "$RESULT" | jq -r '.success // false')
  COMMIT=$(echo "$RESULT" | jq -r '.commit_hash // empty')
  ERROR=$(echo "$RESULT" | jq -r '.error_message // empty')
  NOTES=$(echo "$RESULT" | jq -r '.notes // empty')
  
  if [ "$SUCCESS" = "true" ]; then
    update_story_status "$DB_ID" "done" "$COMMIT" ""
    COMPLETED=$((COMPLETED + 1))
    
    "$SCRIPT_DIR/notify_telegram.sh" "✅ *DONE*: \`$STORY_ID\`
━━━━━━━━━━━━━━━━━━
Commit: \`${COMMIT:0:8}\`
Duration: ${DURATION}s
$NOTES"
    
    log "Story $STORY_ID completed. Commit: $COMMIT"
  else
    update_story_status "$DB_ID" "failed" "" "$ERROR"
    FAILED=$((FAILED + 1))
    
    "$SCRIPT_DIR/notify_telegram.sh" "🔴 *FAILED*: \`$STORY_ID\`
━━━━━━━━━━━━━━━━━━
Error: $ERROR
Duration: ${DURATION}s"
    
    log "Story $STORY_ID failed: $ERROR"
  fi
  
  # Brief pause between stories
  sleep 5
done

# Final summary
"$SCRIPT_DIR/notify_telegram.sh" "🏁 *RALPH COMPLETE*
━━━━━━━━━━━━━━━━━━━━━━

📊 *Results*
┌─────────────────────
│ ✅ Completed: $COMPLETED
│ 🔴 Failed: $FAILED
│ 🔄 Iterations: $ITERATION
│ 🗄️ DB: $DB_PROVIDER
└─────────────────────

⏱️ $(date '+%Y-%m-%d %H:%M')
━━━━━━━━━━━━━━━━━━━━━━"

log "Ralph complete. Completed: $COMPLETED, Failed: $FAILED"
```

## TASK 8: CREATE STATUS CHECK SCRIPT

Create /root/ralph/scripts/check_status.sh:

```bash
#!/bin/bash
# Check Ralph status and story progress

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/db_manager.sh"

PROJECT_ID="${PROJECT_ID:-1}"

echo "=== RALPH STATUS ==="
echo "Primary DB: $DB_PROVIDER"
echo ""

db_query "
SELECT 
  story_id,
  title,
  status_emoji || ' ' || UPPER(status) as status,
  COALESCE(LEFT(commit_hash, 8), '-') as commit,
  retry_count as retries
FROM ralph_stories 
WHERE project_id = $PROJECT_ID
ORDER BY priority;
"

echo ""
echo "=== SUMMARY ==="
db_query "
SELECT 
  'Total: ' || COUNT(*) || 
  ' | Done: ' || SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) ||
  ' | Failed: ' || SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) ||
  ' | Todo: ' || SUM(CASE WHEN status='todo' THEN 1 ELSE 0 END)
FROM ralph_stories 
WHERE project_id = $PROJECT_ID;
"

echo ""
echo "=== DATABASE STATUS ==="
db_status
```

## TASK 9: CREATE ENVIRONMENT TEMPLATE

Create /root/ralph/config/.env.template:

```bash
# Claude API (required)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Telegram (required for notifications)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Database URLs (add any/all that you have)
# The system will auto-detect and use what's available

# Neon
# NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/dbname?sslmode=require

# Supabase
# SUPABASE_DB_URL=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres

# Railway
# RAILWAY_DATABASE_URL=postgresql://postgres:pass@xxx.railway.app:5432/railway

# Local
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# Project settings
PROJECT_ID=1
PROJECT_PATH=/root/rivet-pro
MAX_ITERATIONS=50
```

## TASK 10: CREATE README

Create /root/ralph/README.md:

```markdown
# Ralph - Autonomous Story Implementation

Ralph reads stories from PostgreSQL (with auto-failover), implements them using Claude Code CLI, and sends progress updates to Telegram.

## Features

- **Auto-detect databases**: Finds Supabase, Neon, Railway, local PostgreSQL
- **Fallback support**: If primary fails, automatically uses backup
- **Data replication**: Writes go to all active databases
- **Telegram updates**: Real-time notifications on your phone

## Quick Start

1. Copy config template:
   ```bash
   cp config/.env.template config/.env
   nano config/.env  # Add your credentials
   ```

2. Make scripts executable:
   ```bash
   chmod +x scripts/*.sh
   ```

3. Detect databases:
   ```bash
   ./scripts/detect_databases.sh
   ```

4. Initialize schema on all databases:
   ```bash
   ./scripts/db_manager.sh init
   ```

5. Check status:
   ```bash
   ./scripts/check_status.sh
   ```

6. Run Ralph:
   ```bash
   ./scripts/ralph_loop.sh
   ```

## Scripts

| Script | Purpose |
|--------|---------|
| detect_databases.sh | Find all available PostgreSQL databases |
| db_manager.sh | Database operations with fallback |
| sync_databases.sh | Sync data between databases |
| ralph_loop.sh | Main loop - processes stories |
| run_story.sh | Implements single story |
| notify_telegram.sh | Telegram notifications |
| check_status.sh | Show current progress |

## Database Commands

```bash
# Check all database connections
./scripts/db_manager.sh status

# Initialize schema on all databases
./scripts/db_manager.sh init

# Run a query with fallback
./scripts/db_manager.sh query "SELECT * FROM ralph_stories"

# Sync primary to all backups
./scripts/sync_databases.sh
```

## Status Emojis

- ⬜ TODO - Not started
- 🟡 IN_PROGRESS - Currently working
- ✅ DONE - Completed successfully
- 🔴 FAILED - Failed (will retry)
- ❌ BLOCKED - Needs human help

## Running in Background

```bash
nohup ./scripts/ralph_loop.sh > logs/ralph.log 2>&1 &
```
```

## TASK 11: SET PERMISSIONS

```bash
chmod +x /root/ralph/scripts/*.sh
```

## TASK 12: RUN INITIAL SETUP

After creating all files:

```bash
# 1. Detect available databases
./scripts/detect_databases.sh

# 2. Initialize schema on all found databases
./scripts/db_manager.sh init

# 3. Show status
./scripts/db_manager.sh status
```

## SUMMARY

This creates a Ralph system that:
1. Auto-detects all PostgreSQL databases (Supabase, Neon, Railway, local, Docker)
2. Designates one as primary (prefers cloud)
3. Uses fallbacks if primary fails
4. Replicates writes to all databases
5. Sends Telegram notifications
6. Uses Claude Code CLI for implementation

User just needs to:
1. Add credentials to .env
2. Run detect_databases.sh
3. Run ralph_loop.sh
