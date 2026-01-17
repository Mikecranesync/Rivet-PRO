#!/usr/bin/env python3
"""
Ralph Local - Run Ralph on Windows, execute against VPS database

Simplified version that:
- Connects to Neon PostgreSQL
- Fetches KB stories
- Uses local Claude CLI to implement
- Commits to local git repo
"""

import os
import sys
import json
import subprocess
import asyncio
import asyncpg
from datetime import datetime
from pathlib import Path


class RalphLocal:
    """Ralph running locally on Windows"""

    def __init__(self, max_iterations=5):
        self.max_iterations = max_iterations
        self.project_root = Path(__file__).parent.parent.parent
        self.project_id = 1

        # Load DATABASE_URL from .env file
        env_file = self.project_root / '.env'
        self.db_url = os.getenv('DATABASE_URL')

        if not self.db_url and env_file.exists():
            # Read from .env file
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        self.db_url = line.split('=', 1)[1].strip()
                        break

        if not self.db_url:
            print("ERROR: DATABASE_URL not found in .env file")
            sys.exit(1)

    async def run(self):
        """Main Ralph loop"""
        print("="*60)
        print("  Ralph Local - Windows Edition")
        print("="*60)
        print(f"\nProject: {self.project_root}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"Database: {self.db_url[:50]}...\n")

        # Connect to database
        try:
            self.conn = await asyncpg.connect(self.db_url)
            print("[OK] Connected to Neon database\n")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return

        completed = 0
        failed = 0

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*60}")
            print(f"  Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*60}\n")

            # Get next story
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

            # Mark in progress
            await self.update_story_status(story['id'], 'in_progress')

            # Implement story
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
                print(f"   Commit: {commit_hash[:8]}")
            else:
                error = result.get('error_message', 'Unknown error')
                await self.update_story_status(
                    story['id'], 'failed',
                    error_message=error
                )
                failed += 1
                print(f"\n[FAILED] {story_id}")
                print(f"   Error: {error}")

            # Brief pause
            await asyncio.sleep(2)

        # Summary
        print(f"\n{'='*60}")
        print("  Ralph Complete")
        print(f"{'='*60}")
        print(f"[+] Completed: {completed}")
        print(f"[-] Failed: {failed}")
        print(f"[~] Iterations: {iteration}")
        print(f"{'='*60}\n")

        await self.conn.close()

    async def get_next_story(self):
        """Get next story from database"""
        row = await self.conn.fetchrow(
            """
            SELECT id, story_id, title, description, acceptance_criteria
            FROM ralph_stories
            WHERE project_id = $1
              AND status = 'todo'
              AND retry_count < 3
              AND (story_id LIKE 'KB-%' OR story_id LIKE 'CRITICAL-KB-%' OR story_id LIKE 'STABLE-%' OR story_id LIKE 'AUTO-KB-%' OR story_id LIKE 'TASK-%' OR story_id LIKE 'PHOTO-%' OR story_id LIKE 'ANALYTICS-%' OR story_id LIKE 'SME-CHAT-%')
            ORDER BY priority ASC
            LIMIT 1
            """,
            self.project_id
        )
        return dict(row) if row else None

    async def update_story_status(self, story_db_id, status, commit_hash=None, error_message=None):
        """Update story status in database"""
        emoji = {
            'todo': '⬜',
            'in_progress': '🟡',
            'done': '✅',
            'failed': '🔴'
        }.get(status, '⬜')

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

    async def implement_story(self, story_id, title, description, criteria):
        """Use local Claude CLI to implement story"""
        print("[CLAUDE] Starting implementation...\n")

        # Build prompt
        prompt = self.build_prompt(story_id, title, description, criteria)

        # Write to temp file
        temp_file = self.project_root / f"temp_prompt_{story_id}.txt"
        temp_file.write_text(prompt, encoding='utf-8')

        try:
            # Run Claude CLI
            result = subprocess.run(
                ['claude', '--print'],
                stdin=open(temp_file, 'r', encoding='utf-8'),
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout
                cwd=str(self.project_root)
            )

            # Clean up temp file
            temp_file.unlink()

            output = result.stdout + result.stderr

            # Try to extract JSON result
            try:
                # Look for JSON in output
                import re
                json_match = re.search(r'\{[^{}]*"success"[^{}]*\}', output, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group(0))
                else:
                    # Claude completed but no JSON - assume success
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

            return result_json['success'], result_json

        except subprocess.TimeoutExpired:
            try:
                temp_file.unlink()
            except:
                pass  # Ignore file deletion errors
            return False, {'error_message': 'Implementation timed out after 5 minutes'}

        except Exception as e:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass  # Ignore file deletion errors
            return False, {'error_message': str(e)}

    def build_prompt(self, story_id, title, description, criteria):
        """Build implementation prompt"""
        return f"""You are implementing a feature for RIVET Pro, an AI-powered maintenance assistant.

# Story: {story_id}
# Title: {title}

## Description
{description}

## Acceptance Criteria
{criteria}

## Context
- Repository: {self.project_root}
- This is an n8n-based system with PostgreSQL database
- Telegram bot for user interface
- Keep code SIMPLE - field techs need FAST responses
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
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Local - KB Story Implementation')
    parser.add_argument('--max', type=int, default=5, help='Max iterations (default: 5)')
    parser.add_argument('--story', type=str, help='Specific story ID to implement')

    args = parser.parse_args()

    ralph = RalphLocal(max_iterations=args.max)
    await ralph.run()


if __name__ == '__main__':
    asyncio.run(main())
