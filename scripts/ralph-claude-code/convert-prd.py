#!/usr/bin/env python3
"""
Convert JSON PRD to markdown @fix_plan.md format.

Usage:
    python convert-prd.py <prd.json> [--include-complete] [--output FILE]

Options:
    --include-complete    Include completed stories (default: only incomplete)
    --output FILE         Write to file instead of stdout

Examples:
    python convert-prd.py ../ralph/prd.json > @fix_plan.md
    python convert-prd.py prd.json --include-complete --output @fix_plan.md
"""

import json
import sys
from typing import Dict, List, Optional


def convert_story(story: Dict, number: int) -> str:
    """Convert single story to markdown section."""
    passes = story.get('passes', False)
    story_id = story.get('id', f'STORY-{number:03d}')
    title = story.get('title', 'Untitled Story')
    description = story.get('description', '')
    acceptance_criteria = story.get('acceptanceCriteria', [])
    notes = story.get('notes', '')

    # Checkbox state
    checkbox = '[x]' if passes else '[ ]'
    status_emoji = '✅' if passes else '❌'

    # Build section
    md = f"### {status_emoji} {story_id}: {title}\n\n"
    md += f"{description}\n\n"

    if acceptance_criteria:
        md += "**Acceptance Criteria**:\n"
        for criteria in acceptance_criteria:
            md += f"- {checkbox} {criteria}\n"
        md += "\n"

    if notes:
        md += f"**Notes**: {notes}\n\n"

    md += "---\n\n"

    return md


def convert_prd(
    prd_path: str,
    include_complete: bool = False,
    output_file: Optional[str] = None
) -> str:
    """Convert entire PRD from JSON to markdown."""
    try:
        with open(prd_path, 'r', encoding='utf-8') as f:
            prd = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {prd_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {prd_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract metadata
    project = prd.get('project', 'Unknown Project')
    branch = prd.get('branchName', 'main')
    description = prd.get('description', '')
    stories = prd.get('userStories', [])

    # Separate completed and pending
    completed = [s for s in stories if s.get('passes', False)]
    pending = [s for s in stories if not s.get('passes', False)]

    # Build markdown
    md = f"# Fix Plan: {project}\n\n"
    md += f"**Branch**: `{branch}`\n"
    if description:
        md += f"**Description**: {description}\n"
    md += "\n---\n\n"

    # Completed stories (reference only)
    if completed and include_complete:
        md += "## Completed Stories (Reference)\n\n"
        md += "_These stories are already done and should not be re-implemented._\n\n"
        for idx, story in enumerate(completed, 1):
            md += convert_story(story, idx)

    # Pending stories
    if pending:
        md += "## Current Tasks\n\n"
        md += "_Complete these tasks in order of priority._\n\n"
        for idx, story in enumerate(pending, len(completed) + 1):
            md += convert_story(story, idx)
    else:
        if not completed:
            md += "## No Tasks\n\n"
            md += "_No stories found in PRD._\n\n"
        else:
            md += "## All Tasks Complete\n\n"
            md += "_All stories in PRD are marked as passing._\n\n"

    # Summary
    total = len(stories)
    complete_count = len(completed)
    pending_count = len(pending)

    md += "---\n\n"
    md += "## Summary\n\n"
    md += f"- **Total Stories**: {total}\n"
    md += f"- **Completed**: {complete_count} ✅\n"
    md += f"- **Pending**: {pending_count} ❌\n"

    if pending_count > 0:
        md += f"\n**Next**: Work on {pending[0].get('id', 'first pending story')}\n"

    # Write output
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md)
            print(f"[OK] Converted {prd_path} -> {output_file}")
            print(f"  {complete_count} completed, {pending_count} pending")
        except IOError as e:
            print(f"ERROR: Cannot write to {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        return md


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    prd_path = sys.argv[1]
    include_complete = '--include-complete' in sys.argv
    output_file = None

    # Parse --output flag
    try:
        output_idx = sys.argv.index('--output')
        if output_idx + 1 < len(sys.argv):
            output_file = sys.argv[output_idx + 1]
        else:
            print("ERROR: --output requires a filename", file=sys.stderr)
            sys.exit(1)
    except ValueError:
        pass  # --output not specified

    # Convert
    markdown = convert_prd(prd_path, include_complete, output_file)

    # Print to stdout if no output file
    if not output_file:
        print(markdown)


if __name__ == '__main__':
    main()
