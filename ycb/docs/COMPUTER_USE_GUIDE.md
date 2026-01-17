# YouTube Channel Builder (YCB) - Computer Use Guide

## Overview

This guide covers automated operation of YCB using Claude's computer use capabilities, scheduled tasks, and programmatic control. It's designed for running YCB autonomously with minimal human intervention.

---

## Quick Reference

### Essential Commands

```bash
# Check system health
python -m ycb status --json

# Generate script (non-interactive)
python -m ycb script generate "Topic" --output ./out.json --no-confirm

# Full pipeline (dry-run first)
python -m ycb pipeline run "Topic" --dry-run --output ./package/

# Upload video (with all metadata)
python -m ycb upload video.mp4 --title "Title" --description-file desc.txt --tags-file tags.txt

# Autopilot mode (fully automated)
python -m ycb autopilot "Topic" --count 1 --no-confirm
```

---

## Automation Scenarios

### Scenario 1: Scheduled Content Generation

**Goal:** Generate 3 video scripts every Monday at 9 AM.

**Windows Task Scheduler:**

```xml
<!-- ycb_weekly_scripts.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-20T09:00:00</StartBoundary>
      <ScheduleByWeek>
        <DaysOfWeek><Monday/></DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>-m ycb batch-generate --topics-file C:\ycb\weekly_topics.txt --output C:\ycb\output\</Arguments>
      <WorkingDirectory>C:\Users\hharp\OneDrive\Desktop\Rivet-PRO</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**PowerShell script (ycb_weekly.ps1):**

```powershell
# YCB Weekly Script Generation
$ErrorActionPreference = "Stop"
$LogFile = "C:\ycb\logs\weekly_$(Get-Date -Format 'yyyyMMdd').log"

function Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $msg" | Tee-Object -FilePath $LogFile -Append
}

try {
    Set-Location "C:\Users\hharp\OneDrive\Desktop\Rivet-PRO"

    Log "Starting weekly script generation"

    # Read topics from file
    $topics = Get-Content "C:\ycb\weekly_topics.txt"

    foreach ($topic in $topics) {
        if ($topic.Trim()) {
            Log "Generating: $topic"
            python -m ycb script generate $topic `
                --output "C:\ycb\output\$($topic -replace '\s+', '_').json" `
                --no-confirm 2>&1 | Tee-Object -FilePath $LogFile -Append

            # Delay between generations to avoid rate limits
            Start-Sleep -Seconds 30
        }
    }

    Log "Weekly generation complete"
}
catch {
    Log "ERROR: $_"
    exit 1
}
```

### Scenario 2: Continuous Pipeline Processing

**Goal:** Process video pipeline queue continuously.

**Python daemon script:**

```python
#!/usr/bin/env python3
"""
YCB Pipeline Daemon
Continuously processes video pipeline queue
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ycb.core import BaseAgent
from ycb.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ycb_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ycb_daemon')


class PipelineDaemon(BaseAgent):
    """Daemon that continuously processes the pipeline queue."""

    def __init__(self):
        super().__init__("pipeline_daemon")
        self.shutdown_event = asyncio.Event()

    async def run(self):
        """Main daemon loop."""
        logger.info("Pipeline daemon starting...")

        while not self.shutdown_event.is_set():
            try:
                # Check for pending work
                pending = await self._get_pending_jobs()

                if pending:
                    for job in pending:
                        if self.shutdown_event.is_set():
                            break
                        await self._process_job(job)
                else:
                    # No work, wait before checking again
                    logger.debug("No pending jobs, sleeping...")
                    await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Daemon error: {e}")
                await asyncio.sleep(30)  # Back off on error

        logger.info("Pipeline daemon shutting down...")

    async def _get_pending_jobs(self):
        """Get pending pipeline jobs from database."""
        if not self.supabase_client:
            return []

        result = self.supabase_client.table("ycb_video_pipeline")\
            .select("*")\
            .eq("status", "pending")\
            .order("created_at")\
            .limit(5)\
            .execute()

        return result.data

    async def _process_job(self, job):
        """Process a single pipeline job."""
        job_id = job["id"]
        topic = job["topic"]

        logger.info(f"Processing job {job_id}: {topic}")

        try:
            # Update status to processing
            self.supabase_client.table("ycb_video_pipeline")\
                .update({"status": "processing"})\
                .eq("id", job_id)\
                .execute()

            # Run pipeline stages
            await self._generate_script(job)
            await self._generate_thumbnail(job)
            await self._generate_voice(job)

            # Update status to complete
            self.supabase_client.table("ycb_video_pipeline")\
                .update({
                    "status": "completed",
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("id", job_id)\
                .execute()

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.supabase_client.table("ycb_video_pipeline")\
                .update({
                    "status": "failed",
                    "error_message": str(e)
                })\
                .eq("id", job_id)\
                .execute()

    async def _generate_script(self, job):
        """Generate script for job."""
        # Implementation here
        pass

    async def _generate_thumbnail(self, job):
        """Generate thumbnail for job."""
        # Implementation here
        pass

    async def _generate_voice(self, job):
        """Generate voice narration for job."""
        # Implementation here
        pass

    def shutdown(self):
        """Signal daemon to shut down."""
        self.shutdown_event.set()


async def main():
    daemon = PipelineDaemon()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        daemon.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run as Windows Service:**

```powershell
# Install NSSM (Non-Sucking Service Manager)
# Download from https://nssm.cc/

# Install service
nssm install YCBDaemon "C:\Python311\python.exe" "-m ycb daemon"
nssm set YCBDaemon AppDirectory "C:\Users\hharp\OneDrive\Desktop\Rivet-PRO"
nssm set YCBDaemon AppStdout "C:\ycb\logs\daemon_stdout.log"
nssm set YCBDaemon AppStderr "C:\ycb\logs\daemon_stderr.log"

# Start service
nssm start YCBDaemon

# Check status
nssm status YCBDaemon

# Stop service
nssm stop YCBDaemon
```

---

## Claude Computer Use Integration

### Using YCB with Claude

When Claude is controlling the computer, use these patterns:

**Script Generation:**
```bash
# Claude should use --no-confirm to avoid interactive prompts
python -m ycb script generate "Topic Name" --output ./script.json --no-confirm

# Check result
python -c "import json; d=json.load(open('script.json')); print(f'Generated: {d[\"title\"]}')"
```

**Pipeline with Validation:**
```bash
# Step 1: Dry run to validate
python -m ycb pipeline run "Topic" --dry-run --output ./test_package/

# Step 2: Check dry run results
if [ -f "./test_package/script.json" ]; then
    echo "Dry run successful, proceeding..."
    python -m ycb pipeline run "Topic" --output ./package/ --no-confirm
else
    echo "Dry run failed"
    exit 1
fi
```

**Status Checking (for Claude to read):**
```bash
# Get JSON status for parsing
python -m ycb status --json > /tmp/ycb_status.json

# Parse with Python
python -c "
import json
status = json.load(open('/tmp/ycb_status.json'))
print(f'Active agents: {len(status[\"agents\"])}')
print(f'Quota remaining: {status[\"quota\"][\"remaining\"]}')
print(f'Pending jobs: {status[\"jobs\"][\"pending\"]}')
"
```

### Claude Tool Definitions

For Claude tool use, define YCB operations as tools:

```json
{
  "name": "ycb_generate_script",
  "description": "Generate a video script using YCB",
  "input_schema": {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string",
        "description": "The topic for the video script"
      },
      "script_type": {
        "type": "string",
        "enum": ["tutorial", "review", "commentary", "news", "documentary"],
        "default": "tutorial"
      },
      "duration": {
        "type": "integer",
        "description": "Target duration in seconds",
        "default": 600
      },
      "output_path": {
        "type": "string",
        "description": "Where to save the script JSON"
      }
    },
    "required": ["topic", "output_path"]
  }
}
```

**Tool implementation:**
```python
def ycb_generate_script(topic: str, output_path: str,
                        script_type: str = "tutorial",
                        duration: int = 600) -> dict:
    """Tool for Claude to generate scripts."""
    import subprocess
    import json

    result = subprocess.run([
        "python", "-m", "ycb", "script", "generate", topic,
        "--type", script_type,
        "--duration", str(duration),
        "--output", output_path,
        "--no-confirm"
    ], capture_output=True, text=True, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        with open(output_path) as f:
            script = json.load(f)
        return {
            "success": True,
            "title": script["title"],
            "sections": len(script.get("sections", [])),
            "path": output_path
        }
    else:
        return {
            "success": False,
            "error": result.stderr
        }
```

---

## Batch Operations

### Batch Script Generation

```bash
# topics.txt (one per line):
# PLC Basics
# Ladder Logic Introduction
# Timer Instructions
# Counter Instructions

# Generate all scripts
python -m ycb batch-generate --topics-file topics.txt --output ./scripts/
```

**Python batch script:**

```python
#!/usr/bin/env python3
"""Batch generate scripts from topics file."""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from ycb.agents.content.scriptwriter import ScriptwriterAgent


async def batch_generate(topics_file: str, output_dir: str):
    """Generate scripts for all topics in file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(topics_file) as f:
        topics = [line.strip() for line in f if line.strip()]

    agent = ScriptwriterAgent()
    results = []

    for i, topic in enumerate(topics):
        print(f"[{i+1}/{len(topics)}] Generating: {topic}")

        try:
            script = await agent.generate_script(topic)
            filename = f"{topic.replace(' ', '_').lower()}.json"
            filepath = output_path / filename

            with open(filepath, 'w') as f:
                json.dump(script.model_dump(), f, indent=2, default=str)

            results.append({
                "topic": topic,
                "status": "success",
                "path": str(filepath)
            })
            print(f"  -> Saved: {filename}")

        except Exception as e:
            results.append({
                "topic": topic,
                "status": "failed",
                "error": str(e)
            })
            print(f"  -> Failed: {e}")

    # Save results summary
    summary_path = output_path / "batch_summary.json"
    with open(summary_path, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total": len(topics),
            "success": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }, f, indent=2)

    print(f"\nBatch complete: {summary_path}")


if __name__ == "__main__":
    import asyncio

    if len(sys.argv) != 3:
        print("Usage: python batch_generate.py <topics_file> <output_dir>")
        sys.exit(1)

    asyncio.run(batch_generate(sys.argv[1], sys.argv[2]))
```

### Batch Upload

```bash
# Upload all videos in directory
for video in ./videos/*.mp4; do
    name=$(basename "$video" .mp4)
    python -m ycb upload "$video" \
        --title "$name" \
        --description-file "./descriptions/${name}.txt" \
        --tags-file "./tags/${name}.txt" \
        --thumbnail "./thumbnails/${name}.png" \
        --privacy unlisted \
        --no-confirm

    # Respect YouTube quota (6 uploads = 9600 units, daily limit 10000)
    sleep 300  # 5 minutes between uploads
done
```

---

## Monitoring & Alerting

### Health Check Script

```python
#!/usr/bin/env python3
"""YCB Health Check - Run periodically to monitor system."""

import json
import sys
import subprocess
from datetime import datetime, timedelta

def check_health():
    """Perform health checks and return status."""
    issues = []

    # Check 1: YCB imports work
    try:
        result = subprocess.run(
            ["python", "-c", "from ycb.config import settings; print('OK')"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            issues.append(f"Import failed: {result.stderr}")
    except Exception as e:
        issues.append(f"Import check error: {e}")

    # Check 2: Database connection
    try:
        result = subprocess.run(
            ["python", "-c", """
from ycb.config import settings
from supabase import create_client
client = create_client(settings.supabase_url, settings.supabase_key)
client.table('ycb_agent_status').select('count').limit(1).execute()
print('OK')
"""],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            issues.append(f"Database connection failed: {result.stderr}")
    except Exception as e:
        issues.append(f"Database check error: {e}")

    # Check 3: Agent heartbeats (none older than 5 minutes)
    try:
        result = subprocess.run(
            ["python", "-c", """
from ycb.config import settings
from supabase import create_client
from datetime import datetime, timedelta

client = create_client(settings.supabase_url, settings.supabase_key)
cutoff = (datetime.utcnow() - timedelta(minutes=5)).isoformat()

result = client.table('ycb_agent_status')\
    .select('agent_name,last_heartbeat')\
    .lt('last_heartbeat', cutoff)\
    .eq('status', 'running')\
    .execute()

if result.data:
    for agent in result.data:
        print(f"STALE: {agent['agent_name']}")
else:
    print('OK')
"""],
            capture_output=True, text=True, timeout=30
        )
        if "STALE:" in result.stdout:
            issues.append(f"Stale agents: {result.stdout}")
    except Exception as e:
        issues.append(f"Heartbeat check error: {e}")

    # Check 4: Quota remaining
    try:
        result = subprocess.run(
            ["python", "-c", """
from ycb.config import settings
from supabase import create_client
from datetime import date

client = create_client(settings.supabase_url, settings.supabase_key)
result = client.table('ycb_api_quota')\
    .select('*')\
    .eq('date', str(date.today()))\
    .execute()

for quota in result.data:
    pct = quota['units_used'] / quota['units_limit'] * 100
    if pct > 80:
        print(f"WARN: {quota['service']} at {pct:.0f}%")
    else:
        print(f"OK: {quota['service']} at {pct:.0f}%")
"""],
            capture_output=True, text=True, timeout=30
        )
        if "WARN:" in result.stdout:
            issues.append(f"Quota warning: {result.stdout}")
    except Exception as e:
        issues.append(f"Quota check error: {e}")

    return {
        "timestamp": datetime.now().isoformat(),
        "healthy": len(issues) == 0,
        "issues": issues
    }


if __name__ == "__main__":
    status = check_health()
    print(json.dumps(status, indent=2))

    if not status["healthy"]:
        sys.exit(1)
```

### Alerting Integration

```python
# Send alerts via webhook (Slack, Discord, etc.)
import requests

def send_alert(message: str, severity: str = "warning"):
    """Send alert to monitoring system."""
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "text": f"[YCB {severity.upper()}] {message}",
        "username": "YCB Monitor",
        "icon_emoji": ":robot_face:"
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")
```

---

## Error Recovery

### Automatic Retry on Failure

```python
import asyncio
from functools import wraps

def with_retry(max_attempts: int = 3, delay: float = 5.0):
    """Decorator for automatic retry on failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        wait = delay * (2 ** attempt)  # Exponential backoff
                        logging.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}), "
                            f"retrying in {wait}s: {e}"
                        )
                        await asyncio.sleep(wait)
            raise last_error
        return wrapper
    return decorator


# Usage
@with_retry(max_attempts=3, delay=10.0)
async def upload_video(video_path: str, metadata: dict):
    """Upload video with automatic retry."""
    # Implementation here
    pass
```

### Recovery from Incomplete State

```bash
# Find and resume incomplete jobs
python -c "
from ycb.config import settings
from supabase import create_client

client = create_client(settings.supabase_url, settings.supabase_key)

# Find jobs stuck in 'processing' for over 1 hour
from datetime import datetime, timedelta
cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()

result = client.table('ycb_video_pipeline')\
    .update({'status': 'pending'})\
    .eq('status', 'processing')\
    .lt('updated_at', cutoff)\
    .execute()

print(f'Reset {len(result.data)} stuck jobs')
"
```

---

## Environment Variables Reference

```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...

# YouTube OAuth
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_CHANNEL_ID=UC...

# YCB Settings
YCB_OUTPUT_DIR=./ycb_output
YCB_MAX_VIDEOS_PER_DAY=5
YCB_DEFAULT_PRIVACY=private
YCB_AUTO_PUBLISH=false
YCB_LOG_LEVEL=INFO

# Computer Use / Automation
YCB_NO_CONFIRM=true           # Skip all confirmations
YCB_HEADLESS=true             # No GUI prompts
YCB_DAEMON_MODE=true          # Run as background daemon
YCB_HEALTH_CHECK_PORT=8080    # Health check HTTP port

# Alerting
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
ALERT_EMAIL=admin@example.com
```

---

## Logging Configuration

```python
# logging_config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "ycb.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "ycb": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

---

## Quick Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| "No module named 'ycb'" | `pip show ycb` | `pip install -e .` |
| "SUPABASE_URL not set" | `echo $SUPABASE_URL` | Add to `.env` |
| Agent stuck "processing" | Check `ycb_agent_status` | Reset status to idle |
| Quota exceeded | `python -m ycb status --quota` | Wait for reset or upgrade |
| Upload fails | Check YouTube OAuth | Re-run `python -m ycb auth youtube` |
| Daemon won't start | Check logs | `tail -f ycb_daemon.log` |
