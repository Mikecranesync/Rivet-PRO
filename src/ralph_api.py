#!/usr/bin/env python3
"""
Ralph API Story Executor - Claude API with Tool Use

Uses Anthropic API credits directly for autonomous code execution.

Usage:
    python -m src.ralph_api --max 5           # Run up to 5 stories
    python -m src.ralph_api --prefix TASK-9   # Only run TASK-9.* stories
    python -m src.ralph_api --story TASK-9.1  # Run specific story
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# Fix Windows console encoding for emoji output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class RalphAPI:
    """Ralph API-based story executor using Claude tool use."""

    # File operation tools for Claude
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

    def __init__(
        self,
        project_root: Optional[Path] = None,
        database_url: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        """Initialize Ralph API executor."""
        self.project_root = project_root or Path.cwd()

        # Load from .env if not provided
        self.database_url = database_url or self._load_env_var("DATABASE_URL")
        self.anthropic_api_key = anthropic_api_key or self._load_env_var("ANTHROPIC_API_KEY")

        # Initialize Anthropic client
        if Anthropic and self.anthropic_api_key:
            self.client = Anthropic(api_key=self.anthropic_api_key)
        else:
            self.client = None

    def _load_env_var(self, var_name: str) -> Optional[str]:
        """Load environment variable from .env file or environment."""
        value = os.getenv(var_name)
        if value:
            return value

        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith(f"{var_name}="):
                        return line.split("=", 1)[1].strip()
        return None

    def read_file(self, path: str) -> str:
        """Read file from project root."""
        file_path = self.project_root / path
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        file_path = self.project_root / path
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """Edit file by replacing old_text with new_text."""
        file_path = self.project_root / path
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            if old_text not in content:
                return f"Error: old_text not found in {path}"

            new_content = content.replace(old_text, new_text, 1)

            with open(file_path, 'w') as f:
                f.write(new_content)

            return f"Successfully edited {path}"
        except Exception as e:
            return f"Error editing file: {e}"

    def run_command(self, command: str) -> str:
        """Run shell command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            return output if output else "Command completed successfully"
        except Exception as e:
            return f"Error running command: {e}"

    def process_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Process a tool call from Claude."""
        print(f"  Tool: {tool_name}")

        if tool_name == "read_file":
            return self.read_file(tool_input["path"])
        elif tool_name == "write_file":
            return self.write_file(tool_input["path"], tool_input["content"])
        elif tool_name == "edit_file":
            return self.edit_file(
                tool_input["path"],
                tool_input["old_text"],
                tool_input["new_text"]
            )
        elif tool_name == "run_command":
            return self.run_command(tool_input["command"])
        elif tool_name == "complete_story":
            return json.dumps({
                "status": "complete",
                "commit_message": tool_input["commit_message"],
                "summary": tool_input["summary"]
            })
        else:
            return f"Unknown tool: {tool_name}"

    def execute_story(
        self,
        story_id: str,
        title: str,
        description: str,
        acceptance_criteria: str,
        priority: int,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 20
    ) -> Tuple[bool, Dict[str, Any]]:
        """Execute story using Claude with tool use."""
        if not self.client:
            return False, {"error": "Anthropic client not initialized"}

        print(f"\n{'='*80}")
        print(f"Executing {story_id}: {title}")
        print(f"Priority: {priority}")
        print(f"{'='*80}\n")

        # Build initial prompt
        prompt = f"""You are Ralph, an autonomous AI agent implementing stories.

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

Project root: {self.project_root}

Start by reading the relevant files to understand the current implementation."""

        messages = [{"role": "user", "content": prompt}]
        completed = False
        commit_info = None

        for turn in range(max_turns):
            print(f"\nTurn {turn + 1}/{max_turns}")

            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    tools=self.TOOLS,
                    messages=messages
                )

                assistant_content = []

                for block in response.content:
                    if block.type == "text":
                        print(f"Claude: {block.text[:200]}...")
                        assistant_content.append(block)

                    elif block.type == "tool_use":
                        tool_result = self.process_tool_call(block.name, block.input)
                        print(f"  Result: {tool_result[:100]}...")

                        if block.name == "complete_story":
                            try:
                                commit_info = json.loads(tool_result)
                                completed = True
                            except:
                                pass

                        assistant_content.append(block)

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

                if assistant_content and not completed:
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })

                if response.stop_reason == "end_turn" or completed:
                    break

            except Exception as e:
                print(f"Error in turn {turn + 1}: {e}")
                return False, {"error": str(e)}

        if completed and commit_info:
            print(f"\nCreating git commit...")
            commit_msg = commit_info.get("commit_message", f"feat({story_id}): Implementation")

            self.run_command("git add -A")
            commit_result = self.run_command(f'git commit -m "{commit_msg}"')

            print(f"Git commit created")
            print(f"Summary: {commit_info.get('summary', 'Completed')}")

            return True, {
                "commit_message": commit_msg,
                "summary": commit_info.get("summary"),
                "commit_result": commit_result
            }
        else:
            return False, {"error": "Story not completed within turn limit"}

    def get_pending_stories(
        self,
        prefix: Optional[str] = None,
        story_id: Optional[str] = None,
        max_stories: int = 10
    ) -> List[Dict[str, Any]]:
        """Get pending stories from database."""
        if not psycopg2 or not self.database_url:
            return []

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                if story_id:
                    cur.execute("""
                        SELECT story_id, title, description, acceptance_criteria, priority
                        FROM ralph_stories
                        WHERE story_id = %s AND status = 'todo'
                    """, (story_id,))
                elif prefix:
                    cur.execute("""
                        SELECT story_id, title, description, acceptance_criteria, priority
                        FROM ralph_stories
                        WHERE story_id LIKE %s AND status = 'todo'
                        ORDER BY priority ASC
                        LIMIT %s
                    """, (f"{prefix}%", max_stories))
                else:
                    cur.execute("""
                        SELECT story_id, title, description, acceptance_criteria, priority
                        FROM ralph_stories
                        WHERE status = 'todo'
                        ORDER BY priority ASC
                        LIMIT %s
                    """, (max_stories,))

                rows = cur.fetchall()
                return [
                    {
                        "story_id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "acceptance_criteria": row[3],
                        "priority": row[4]
                    }
                    for row in rows
                ]
        finally:
            conn.close()

    def update_story_status(
        self,
        story_id: str,
        status: str,
        commit_hash: Optional[str] = None
    ) -> None:
        """Update story status in database."""
        if not psycopg2 or not self.database_url:
            return

        conn = psycopg2.connect(self.database_url)
        try:
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
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Ralph API Story Executor")
    parser.add_argument("--max", type=int, default=5, help="Max stories to run (default: 5)")
    parser.add_argument("--prefix", type=str, help="Story ID prefix filter (e.g., TASK-9, KB-)")
    parser.add_argument("--story", type=str, help="Specific story ID to run")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--project-root", type=str, help="Project root directory")
    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else Path.cwd()

    print("="*80)
    print("  Ralph API Story Executor")
    print("="*80)
    print(f"\nProject Root: {project_root}")
    print(f"Model: {args.model}")
    print(f"Max Stories: {args.max}")
    if args.prefix:
        print(f"Prefix Filter: {args.prefix}")
    if args.story:
        print(f"Specific Story: {args.story}")

    ralph = RalphAPI(project_root=project_root)

    if not ralph.client:
        print("ERROR: Anthropic client not initialized. Check ANTHROPIC_API_KEY.")
        sys.exit(1)

    stories = ralph.get_pending_stories(
        prefix=args.prefix,
        story_id=args.story,
        max_stories=args.max
    )

    print(f"\nFound {len(stories)} pending stories\n")

    if not stories:
        print("No pending stories found!")
        return

    completed = 0
    failed = 0

    for story in stories:
        try:
            ralph.update_story_status(story["story_id"], 'in_progress')

            success, result = ralph.execute_story(
                story["story_id"],
                story["title"],
                story["description"],
                str(story["acceptance_criteria"]),
                story["priority"],
                model=args.model
            )

            if success:
                commit_hash = result.get("commit_result", "")[:40] if result.get("commit_result") else None
                ralph.update_story_status(story["story_id"], 'done', commit_hash)
                print(f"\n[SUCCESS] {story['story_id']} completed")
                completed += 1
            else:
                ralph.update_story_status(story["story_id"], 'failed')
                print(f"\n[FAILED] {story['story_id']}: {result.get('error', 'Unknown error')}")
                failed += 1

        except Exception as e:
            print(f"\n[ERROR] {e}")
            ralph.update_story_status(story["story_id"], 'failed')
            failed += 1

    print(f"\n{'='*80}")
    print("  Ralph Execution Complete")
    print(f"{'='*80}")
    print(f"[+] Completed: {completed}")
    print(f"[-] Failed: {failed}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
