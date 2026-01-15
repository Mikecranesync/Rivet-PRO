"""
BacklogGenerator - Auto-generates Backlog.md every 5 minutes.

Scans backlog/tasks/ directory and ralph_stories database to generate
a comprehensive Backlog.md file with task counts, phase summaries, and status.
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class BacklogGenerator:
    """
    Generates Backlog.md from task files and database.

    Usage:
        generator = BacklogGenerator()
        await generator.generate()  # Single generation
        await generator.run()       # Continuous loop every 5 minutes
    """

    def __init__(
        self,
        tasks_dir: Optional[Path] = None,
        output_file: Optional[Path] = None,
        database_url: Optional[str] = None,
        interval_seconds: int = 300  # 5 minutes
    ):
        self.tasks_dir = tasks_dir or PROJECT_ROOT / "backlog" / "tasks"
        self.output_file = output_file or PROJECT_ROOT / "Backlog.md"
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.interval_seconds = interval_seconds
        self._running = False

    async def run(self):
        """Run continuous generation loop"""
        self._running = True
        logger.info(f"BacklogGenerator started (interval: {self.interval_seconds}s)")

        while self._running:
            try:
                await self.generate()
                logger.info(f"Backlog.md regenerated at {datetime.utcnow().isoformat()}")
            except Exception as e:
                logger.error(f"Error generating Backlog.md: {e}")

            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        """Stop the generation loop"""
        self._running = False
        logger.info("BacklogGenerator stopped")

    async def generate(self):
        """Generate Backlog.md"""
        # Gather data
        tasks = self._scan_task_files()
        ralph_stories = self._get_ralph_stories()

        # Count by status
        task_counts = self._count_by_status(tasks)
        ralph_counts = self._count_ralph_stories(ralph_stories)

        # Generate markdown
        content = self._generate_markdown(tasks, task_counts, ralph_stories, ralph_counts)

        # Write to file
        self.output_file.write_text(content, encoding="utf-8")

    def _scan_task_files(self) -> List[Dict[str, Any]]:
        """Scan backlog/tasks/ directory for task files"""
        tasks = []

        if not self.tasks_dir.exists():
            logger.warning(f"Tasks directory not found: {self.tasks_dir}")
            return tasks

        for file_path in self.tasks_dir.glob("*.md"):
            task = self._parse_task_file(file_path)
            if task:
                tasks.append(task)

        # Sort by ID
        tasks.sort(key=lambda t: t.get("id", ""))
        return tasks

    def _parse_task_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a task markdown file"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            task = {
                "file": file_path.name,
                "id": "",
                "title": "",
                "status": "To Do",
                "labels": [],
                "parent": None
            }

            for line in lines:
                line = line.strip()
                if line.startswith("id:"):
                    task["id"] = line.replace("id:", "").strip()
                elif line.startswith("Status:"):
                    status_part = line.replace("Status:", "").strip()
                    if "Done" in status_part or "[x]" in line.lower():
                        task["status"] = "Done"
                    elif "In Progress" in status_part:
                        task["status"] = "In Progress"
                    else:
                        task["status"] = "To Do"
                elif line.startswith("Labels:"):
                    task["labels"] = [l.strip() for l in line.replace("Labels:", "").split(",")]
                elif line.startswith("Parent:"):
                    task["parent"] = line.replace("Parent:", "").strip()
                elif line.startswith("# ") or line.startswith("Task "):
                    # Extract title from header or "Task X - Title" format
                    if " - " in line:
                        task["title"] = line.split(" - ", 1)[1].strip()
                    else:
                        task["title"] = line.replace("#", "").strip()

            # Use filename as fallback ID
            if not task["id"]:
                task["id"] = file_path.stem.split(" - ")[0] if " - " in file_path.stem else file_path.stem

            return task

        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
            return None

    def _get_ralph_stories(self) -> List[Dict[str, Any]]:
        """Get Ralph stories from database"""
        stories = []

        if not self.database_url:
            return stories

        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT story_id, title, status, priority
                    FROM ralph_stories
                    ORDER BY priority, story_id
                """)
                for row in cur.fetchall():
                    stories.append({
                        "story_id": row[0],
                        "title": row[1],
                        "status": row[2],
                        "priority": row[3]
                    })
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching Ralph stories: {e}")

        return stories

    def _count_by_status(self, tasks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count tasks by status"""
        counts = {"Done": 0, "In Progress": 0, "To Do": 0}
        for task in tasks:
            status = task.get("status", "To Do")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _count_ralph_stories(self, stories: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count Ralph stories by status"""
        counts = {"done": 0, "todo": 0, "in_progress": 0, "failed": 0}
        for story in stories:
            status = story.get("status", "todo")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _generate_markdown(
        self,
        tasks: List[Dict[str, Any]],
        task_counts: Dict[str, int],
        ralph_stories: List[Dict[str, Any]],
        ralph_counts: Dict[str, int]
    ) -> str:
        """Generate the Backlog.md content"""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        total_tasks = sum(task_counts.values())
        total_ralph = sum(ralph_counts.values())
        ralph_done = ralph_counts.get("done", 0)

        content = f"""# RIVET Pro Backlog

> Auto-generated: {now}

## Summary

| Status | Count |
|--------|-------|
| Done | {task_counts.get('Done', 0)} |
| In Progress | {task_counts.get('In Progress', 0)} |
| To Do | {task_counts.get('To Do', 0)} |
| **Total** | **{total_tasks}** |

## Ralph Stories: {ralph_done}/{total_ralph} DONE ({int(ralph_done/total_ralph*100) if total_ralph > 0 else 0}%)

"""

        # Group Ralph stories by prefix
        story_groups: Dict[str, List[Dict[str, Any]]] = {}
        for story in ralph_stories:
            prefix = story["story_id"].split("-")[0] if "-" in story["story_id"] else "OTHER"
            if prefix not in story_groups:
                story_groups[prefix] = []
            story_groups[prefix].append(story)

        for prefix, group in sorted(story_groups.items()):
            done_count = sum(1 for s in group if s["status"] == "done")
            content += f"### {prefix} ({done_count}/{len(group)})\n"
            for story in group:
                icon = "[x]" if story["status"] == "done" else "[ ]"
                content += f"- {icon} {story['story_id']}: {story['title']}\n"
            content += "\n"

        # Group tasks by phase/parent
        content += "---\n\n## Backlog Tasks by Phase\n\n"

        task_groups: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            parent = task.get("parent") or "Ungrouped"
            if parent not in task_groups:
                task_groups[parent] = []
            task_groups[parent].append(task)

        for parent, group in sorted(task_groups.items()):
            done_count = sum(1 for t in group if t["status"] == "Done")
            status_label = "DONE" if done_count == len(group) else "PARTIAL" if done_count > 0 else "TODO"
            content += f"### {status_label} - {parent}\n"
            for task in sorted(group, key=lambda t: t["id"]):
                icon = "[x]" if task["status"] == "Done" else "[ ]"
                content += f"- {icon} {task['id']}: {task['title']}\n"
            content += "\n"

        content += """---

## DevOps Status

| Component | Status |
|-----------|--------|
| Database Failover | Neon -> Railway -> Supabase |
| Langfuse Tracing | Implemented |
| Pipeline Orchestrator | Implemented |
| Telegram Approval | Implemented |

---

*This file is auto-generated every 5 minutes by BacklogGenerator.*
"""

        return content


async def main():
    """Run the backlog generator"""
    generator = BacklogGenerator()
    await generator.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
