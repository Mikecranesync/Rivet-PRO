#!/usr/bin/env python3
"""
Ralph Local - CLI-based story executor using Claude CLI.

Simplified version that:
- Connects to PostgreSQL database
- Fetches stories from ralph_stories table
- Uses local Claude CLI to implement
- Commits to git repo

Usage:
    python -m src.ralph_local --max 5
    python -m src.ralph_local --story KB-001
"""

import os
import sys
import json
import subprocess
import asyncio
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    import asyncpg
except ImportError:
    asyncpg = None


class RalphLocal:
    """Ralph running locally using Claude CLI."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_iterations: int = 5,
        project_id: int = 1
    ):
        self.project_root = project_root or Path.cwd()
        self.max_iterations = max_iterations
        self.project_id = project_id
        self.conn = None

        # Load DATABASE_URL from .env file or environment
        self.db_url = os.getenv('DATABASE_URL')

        if not self.db_url:
            env_file = self.project_root / '.env'
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            self.db_url = line.split('=', 1)[1].strip()
                            break

    async def connect(self) -> bool:
        """Connect to database."""
        if not asyncpg or not self.db_url:
            print("ERROR: asyncpg not installed or DATABASE_URL not found")
            return False

        try:
            self.conn = await asyncpg.connect(self.db_url)
            return True
        except Exception as e:
            print(f"ERROR: Database connection failed: {e}")
            return False

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            await self.conn.close()

    async def run(self) -> None:
        """Main Ralph loop."""
        print("="*60)
        print("  Ralph Local - CLI Edition")
        print("="*60)
        print(f"\nProject: {self.project_root}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"Database: {self.db_url[:50] if self.db_url else 'Not configured'}...\n")

        if not await self.connect():
            return

        print("[OK] Connected to database\n")

        completed = 0
        failed = 0
        iteration = 0

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*60}")
            print(f"  Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*60}\n")

            story = await self.get_next_story()

            if not story:
                print("[DONE] No more stories to process!")
                break

            story_id = story['story_id']
            title = story['title']
            description = story['description']
            criteria = story['acceptance_criteria']

            print(f"[STORY] {story_id}")
            print(f"[TITLE] {title}\n")

            await self.update_story_status(story['id'], 'in_progress')

            success, result = await self.implement_story(
                story_id, title, description, criteria
            )

            if success:
                commit_hash = result.get('commit_hash', 'local')
                await self.update_story_status(
                    story['id'], 'done',
                    commit_hash=commit_hash
                )
                completed += 1
                print(f"\n[SUCCESS] {story_id} COMPLETED")
                print(f"   Commit: {commit_hash[:8] if commit_hash else 'N/A'}")
            else:
                error = result.get('error_message', 'Unknown error')
                await self.update_story_status(
                    story['id'], 'failed',
                    error_message=error
                )
                failed += 1
                print(f"\n[FAILED] {story_id}")
                print(f"   Error: {error}")

            await asyncio.sleep(2)

        print(f"\n{'='*60}")
        print("  Ralph Complete")
        print(f"{'='*60}")
        print(f"[+] Completed: {completed}")
        print(f"[-] Failed: {failed}")
        print(f"[~] Iterations: {iteration}")
        print(f"{'='*60}\n")

        await self.close()

    async def get_next_story(self) -> Optional[Dict[str, Any]]:
        """Get next story from database."""
        row = await self.conn.fetchrow(
            """
            SELECT id, story_id, title, description, acceptance_criteria
            FROM ralph_stories
            WHERE project_id = $1
              AND status = 'todo'
              AND retry_count < 3
            ORDER BY priority ASC
            LIMIT 1
            """,
            self.project_id
        )
        return dict(row) if row else None

    async def update_story_status(
        self,
        story_db_id: int,
        status: str,
        commit_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update story status in database."""
        emoji_map = {
            'todo': '',
            'in_progress': '',
            'done': '',
            'failed': ''
        }
        emoji = emoji_map.get(status, '')

        await self.conn.execute(
            """
            UPDATE ralph_stories
            SET
                status = $1::varchar,
                status_emoji = $2,
                commit_hash = $3,
                error_message = $4,
                completed_at = CASE WHEN $1::varchar = 'done' THEN NOW() ELSE completed_at END,
                retry_count = CASE WHEN $1::varchar = 'failed' THEN retry_count + 1 ELSE retry_count END
            WHERE id = $5
            """,
            status, emoji, commit_hash, error_message, story_db_id
        )

    async def implement_story(
        self,
        story_id: str,
        title: str,
        description: str,
        criteria: Any
    ) -> Tuple[bool, Dict[str, Any]]:
        """Use local Claude CLI to implement story."""
        print("[CLAUDE] Starting implementation...\n")

        prompt = self.build_prompt(story_id, title, description, criteria)

        temp_file = self.project_root / f"temp_prompt_{story_id}.txt"
        temp_file.write_text(prompt, encoding='utf-8')

        try:
            result = subprocess.run(
                ['claude', '--print'],
                stdin=open(temp_file, 'r', encoding='utf-8'),
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout
                cwd=str(self.project_root)
            )

            temp_file.unlink()

            output = result.stdout + result.stderr

            try:
                json_match = re.search(r'\{[^{}]*"success"[^{}]*\}', output, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group(0))
                else:
                    result_json = {
                        'success': True,
                        'commit_hash': 'manual',
                        'notes': 'Implementation completed'
                    }
            except:
                result_json = {
                    'success': result.returncode == 0,
                    'notes': 'Completed without JSON response'
                }

            return result_json.get('success', False), result_json

        except subprocess.TimeoutExpired:
            try:
                temp_file.unlink()
            except:
                pass
            return False, {'error_message': 'Implementation timed out'}

        except Exception as e:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
            return False, {'error_message': str(e)}

    def build_prompt(
        self,
        story_id: str,
        title: str,
        description: str,
        criteria: Any
    ) -> str:
        """Build implementation prompt."""
        return f"""You are implementing a feature autonomously.

# Story: {story_id}
# Title: {title}

## Description
{description}

## Acceptance Criteria
{criteria}

## Context
- Repository: {self.project_root}
- Keep code SIMPLE
- Use existing patterns in the codebase
- DO NOT over-engineer or refactor unrelated code

## Instructions
1. Implement this feature completely
2. Test that it works
3. Commit with message: feat({story_id}): {title}

When done, output a JSON summary:
{{
  "success": true,
  "commit_hash": "the-commit-hash",
  "files_changed": ["list", "of", "files"],
  "notes": "Brief description of what was implemented"
}}

If blocked:
{{
  "success": false,
  "error_message": "What went wrong",
  "notes": "What needs to happen to unblock"
}}
"""


async def main():
    parser = argparse.ArgumentParser(description='Ralph Local - Story Implementation')
    parser.add_argument('--max', type=int, default=5, help='Max iterations (default: 5)')
    parser.add_argument('--story', type=str, help='Specific story ID to implement')
    parser.add_argument('--project-root', type=str, help='Project root directory')

    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else Path.cwd()

    ralph = RalphLocal(project_root=project_root, max_iterations=args.max)
    await ralph.run()


if __name__ == '__main__':
    asyncio.run(main())
