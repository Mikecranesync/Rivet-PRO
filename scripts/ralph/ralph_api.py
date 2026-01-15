#!/usr/bin/env python3
"""
Ralph API Story Executor - Claude API with Tool Use
Uses Anthropic API credits directly (not Claude CLI)

Usage:
    python ralph_api.py --max 5           # Run up to 5 stories
    python ralph_api.py --prefix TASK-9   # Only run TASK-9.* stories
    python ralph_api.py --story TASK-9.1  # Run specific story
"""

import os
import sys
import json
import argparse
import psycopg2
import subprocess
from pathlib import Path
from anthropic import Anthropic

# Fix Windows console encoding for emoji output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuration - auto-detect project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # scripts/ralph -> project root

# Load DATABASE_URL from .env if not in environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    DATABASE_URL = line.split("=", 1)[1].strip()
                    break

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment or .env file")
    sys.exit(1)

# Claude API setup - load from .env if not in environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    ANTHROPIC_API_KEY = line.split("=", 1)[1].strip()
                    break

if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not found in environment or .env file")
    sys.exit(1)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Define file operation tools for Claude
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file to understand current implementation",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to file from project root"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to file from project root"
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Make a targeted edit to a file by replacing old_text with new_text",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to file from project root"
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find and replace (must match exactly)"
                },
                "new_text": {
                    "type": "string",
                    "description": "New text to insert in place of old_text"
                }
            },
            "required": ["path", "old_text", "new_text"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command (for testing or git operations)",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "complete_story",
        "description": "Mark the story as complete with a commit message",
        "input_schema": {
            "type": "object",
            "properties": {
                "commit_message": {
                    "type": "string",
                    "description": "Git commit message for the changes"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what was implemented"
                }
            },
            "required": ["commit_message", "summary"]
        }
    }
]


def read_file(path: str) -> str:
    """Read file from project root"""
    file_path = PROJECT_ROOT / path
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to file"""
    file_path = PROJECT_ROOT / path
    try:
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Edit file by replacing old_text with new_text"""
    file_path = PROJECT_ROOT / path
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        if old_text not in content:
            return f"Error: old_text not found in {path}"

        new_content = content.replace(old_text, new_text, 1)  # Replace first occurrence

        with open(file_path, 'w') as f:
            f.write(new_content)

        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def run_command(command: str) -> str:
    """Run shell command"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        return output if output else "Command completed successfully"
    except Exception as e:
        return f"Error running command: {e}"


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Process a tool call from Claude"""
    print(f"  🔧 Tool: {tool_name}")

    if tool_name == "read_file":
        return read_file(tool_input["path"])

    elif tool_name == "write_file":
        return write_file(tool_input["path"], tool_input["content"])

    elif tool_name == "edit_file":
        return edit_file(
            tool_input["path"],
            tool_input["old_text"],
            tool_input["new_text"]
        )

    elif tool_name == "run_command":
        return run_command(tool_input["command"])

    elif tool_name == "complete_story":
        return json.dumps({
            "status": "complete",
            "commit_message": tool_input["commit_message"],
            "summary": tool_input["summary"]
        })

    else:
        return f"Unknown tool: {tool_name}"


def execute_story_with_tools(story_id: str, title: str, description: str,
                             acceptance_criteria: str, priority: int,
                             model: str = "claude-sonnet-4-20250514") -> tuple:
    """Execute story using Claude with tool use"""
    print(f"\n{'='*80}")
    print(f"Executing {story_id}: {title}")
    print(f"Priority: {priority}")
    print(f"{'='*80}\n")

    # Build initial prompt
    prompt = f"""You are Ralph, an autonomous AI agent implementing Knowledge Base stories for Rivet Pro.

# Current Story

**Story ID**: {story_id}
**Title**: {title}
**Priority**: {priority}

**Description**:
{description}

**Acceptance Criteria**:
{acceptance_criteria}

# Your Task

Implement this story by:
1. Use read_file to examine current code
2. Use write_file or edit_file to make changes
3. Use run_command to test if needed
4. When done, use complete_story with a commit message

Important:
- Make minimal, focused changes
- Maintain existing code style
- Add proper error handling
- Test your changes

Project root: {PROJECT_ROOT}
Main bot file: rivet_pro/adapters/telegram/bot.py
Troubleshooting modules: rivet_pro/troubleshooting/

Start by reading the relevant files to understand the current implementation."""

    messages = [{"role": "user", "content": prompt}]
    completed = False
    commit_info = None
    max_turns = 20  # Prevent infinite loops

    for turn in range(max_turns):
        print(f"\n📍 Turn {turn + 1}/{max_turns}")

        try:
            # Call Claude with tools
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                tools=TOOLS,
                messages=messages
            )

            # Process response
            assistant_content = []

            for block in response.content:
                if block.type == "text":
                    print(f"💬 Claude: {block.text[:200]}...")
                    assistant_content.append(block)

                elif block.type == "tool_use":
                    # Execute tool
                    tool_result = process_tool_call(block.name, block.input)
                    print(f"  ✅ Result: {tool_result[:100]}...")

                    # Check if story is complete
                    if block.name == "complete_story":
                        try:
                            commit_info = json.loads(tool_result)
                            completed = True
                        except:
                            pass

                    assistant_content.append(block)

                    # Add tool result to messages
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result
                        }]
                    })
                    assistant_content = []

            # If no tool use, add assistant message
            if assistant_content and not completed:
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })

            # Check stop reason
            if response.stop_reason == "end_turn" or completed:
                break

        except Exception as e:
            print(f"❌ Error in turn {turn + 1}: {e}")
            return False, {"error": str(e)}

    if completed and commit_info:
        # Create git commit
        print(f"\n📝 Creating git commit...")
        commit_msg = commit_info.get("commit_message", f"feat({story_id}): Implementation")

        # Git add and commit
        run_command("git add -A")
        commit_result = run_command(f'git commit -m "{commit_msg}"')

        print(f"✅ Git commit created")
        print(f"📋 Summary: {commit_info.get('summary', 'Completed')}")

        return True, {
            "commit_message": commit_msg,
            "summary": commit_info.get("summary"),
            "commit_result": commit_result
        }
    else:
        return False, {"error": "Story not completed within turn limit"}


def get_pending_stories(conn, prefix: str = None, story_id: str = None, max_stories: int = 10):
    """Get pending stories with optional filters"""
    with conn.cursor() as cur:
        if story_id:
            # Specific story
            cur.execute("""
                SELECT story_id, title, description, acceptance_criteria, priority
                FROM ralph_stories
                WHERE story_id = %s AND status = 'todo'
            """, (story_id,))
        elif prefix:
            # Stories matching prefix
            cur.execute("""
                SELECT story_id, title, description, acceptance_criteria, priority
                FROM ralph_stories
                WHERE story_id LIKE %s AND status = 'todo'
                ORDER BY priority ASC
                LIMIT %s
            """, (f"{prefix}%", max_stories))
        else:
            # All todo stories
            cur.execute("""
                SELECT story_id, title, description, acceptance_criteria, priority
                FROM ralph_stories
                WHERE status = 'todo'
                ORDER BY priority ASC
                LIMIT %s
            """, (max_stories,))
        return cur.fetchall()


def update_story_status(conn, story_id: str, status: str, commit_hash: str = None):
    """Update story status"""
    with conn.cursor() as cur:
        if commit_hash:
            cur.execute("""
                UPDATE ralph_stories
                SET status = %s, commit_hash = %s
                WHERE story_id = %s
            """, (status, commit_hash, story_id))
        else:
            cur.execute("""
                UPDATE ralph_stories
                SET status = %s
                WHERE story_id = %s
            """, (status, story_id))
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Ralph API Story Executor")
    parser.add_argument("--max", type=int, default=5, help="Max stories to run (default: 5)")
    parser.add_argument("--prefix", type=str, help="Story ID prefix filter (e.g., TASK-9, KB-)")
    parser.add_argument("--story", type=str, help="Specific story ID to run")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-20250514", help="Claude model to use")
    args = parser.parse_args()

    print("="*80)
    print("  Ralph API Story Executor (Claude API with Tool Use)")
    print("="*80)
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Model: {args.model}")
    print(f"Max Stories: {args.max}")
    if args.prefix:
        print(f"Prefix Filter: {args.prefix}")
    if args.story:
        print(f"Specific Story: {args.story}")

    # Connect to database
    print(f"\nConnecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    print("[OK] Connected\n")

    # Get pending stories
    stories = get_pending_stories(conn, prefix=args.prefix, story_id=args.story, max_stories=args.max)
    print(f"Found {len(stories)} pending stories\n")

    if not stories:
        print("No pending stories found!")
        conn.close()
        return

    completed = 0
    failed = 0

    # Execute each story
    for story_id, title, description, acceptance_criteria, priority in stories:
        try:
            print(f"\n{'='*80}")
            print(f"[STORY] {story_id}: {title}")
            print(f"[PRIORITY] {priority}")
            print(f"{'='*80}\n")

            # Update status to in_progress
            update_story_status(conn, story_id, 'in_progress')

            # Execute story with tools
            success, result = execute_story_with_tools(
                story_id, title, description,
                str(acceptance_criteria), priority,
                model=args.model
            )

            # Update status based on result
            if success:
                commit_hash = result.get("commit_result", "")[:40] if result.get("commit_result") else None
                update_story_status(conn, story_id, 'done', commit_hash)
                print(f"\n[SUCCESS] {story_id} completed")
                completed += 1
            else:
                update_story_status(conn, story_id, 'failed')
                print(f"\n[FAILED] {story_id}: {result.get('error', 'Unknown error')}")
                failed += 1

        except Exception as e:
            print(f"\n[ERROR] {e}")
            update_story_status(conn, story_id, 'failed')
            failed += 1

    conn.close()

    print(f"\n{'='*80}")
    print("  Ralph Execution Complete")
    print(f"{'='*80}")
    print(f"[+] Completed: {completed}")
    print(f"[-] Failed: {failed}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
