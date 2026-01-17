# YouTube Channel Builder (YCB) - Implementation Guide

## Architecture Overview

```
ycb/
├── __init__.py              # Package init, version
├── __main__.py              # CLI entry point
├── config.py                # Pydantic Settings configuration
│
├── core/                    # Core infrastructure
│   ├── __init__.py
│   └── base_agent.py        # BaseAgent with Supabase integration
│
├── models/                  # Pydantic v2 data models
│   ├── __init__.py          # Exports all models
│   ├── video.py             # VideoMetadata, UploadJob, QualityScore
│   └── script.py            # VideoScript, ScriptSection, ScriptGeneration
│
├── agents/                  # AI agents (18 total planned)
│   ├── __init__.py
│   ├── content/             # Content production agents
│   │   ├── __init__.py
│   │   └── scriptwriter.py  # ScriptwriterAgent
│   ├── media/               # Media production agents
│   │   └── __init__.py
│   ├── engagement/          # Social/analytics agents
│   │   └── __init__.py
│   └── committees/          # Multi-agent decision groups
│       └── __init__.py
│
├── integrations/            # External API wrappers
│   ├── __init__.py
│   ├── youtube.py           # YouTube Data API v3
│   ├── elevenlabs.py        # ElevenLabs voice synthesis
│   └── openai_vision.py     # DALL-E thumbnail generation
│
├── memory/                  # State persistence
│   ├── __init__.py
│   └── storage.py           # Supabase storage adapter
│
└── cli/                     # Command-line interface
    ├── __init__.py
    └── main.py              # Click CLI commands
```

---

## Core Components

### 1. Configuration System (`config.py`)

Uses Pydantic Settings for type-safe environment configuration:

```python
from ycb.config import settings

# Access settings (auto-loaded from .env)
print(settings.supabase_url)
print(settings.openai_api_key)
print(settings.ycb_output_dir)

# Check if required settings are present
if settings.validate_required_settings():
    print("All required settings configured")

# Check auto-publish eligibility
if settings.is_auto_publish_enabled:
    print("Auto-publish is enabled and privacy allows it")
```

**Adding New Settings:**

```python
# In config.py, add to Settings class:
class Settings(BaseSettings):
    # ... existing fields ...

    # Add new setting
    my_new_setting: Optional[str] = Field(
        default=None,
        description="Description of the setting"
    )
```

### 2. BaseAgent Class (`core/base_agent.py`)

All YCB agents inherit from BaseAgent which provides:
- Supabase client initialization
- Agent status registration
- Heartbeat mechanism
- Async logging with database persistence

```python
from ycb.core import BaseAgent

class MyCustomAgent(BaseAgent):
    """Custom agent implementation."""

    def __init__(self):
        super().__init__("my_custom_agent")

    def _get_capabilities(self) -> Dict[str, Any]:
        """Override to define agent capabilities."""
        return {
            **super()._get_capabilities(),
            "custom_feature": True,
            "version": "1.0.0"
        }

    async def run(self) -> None:
        """Main agent logic - MUST be implemented."""
        await self.log_info("Starting custom agent")

        try:
            # Your agent logic here
            result = await self._do_work()
            await self.log_info(f"Completed: {result}")
        except Exception as e:
            await self.log_error(f"Failed: {e}")
            raise

# Usage
agent = MyCustomAgent()
await agent.start()  # Runs with heartbeat
await agent.stop()   # Graceful shutdown
```

### 3. Pydantic Models (`models/`)

All models use Pydantic v2 syntax with comprehensive validation:

```python
from ycb.models import (
    # Video models
    VideoMetadata,
    VideoMetadataCreate,
    VideoMetadataUpdate,
    UploadJob,
    VideoQualityScore,

    # Script models
    VideoScript,
    VideoScriptCreate,
    ScriptSection,
    ScriptGenerationRequest,

    # Enums
    VideoStatus,
    VideoPrivacy,
    ScriptStatus,
    ScriptType,
    VoiceStyle
)

# Create a script
script = VideoScriptCreate(
    title="PLC Programming Basics",
    description="Learn the fundamentals of PLC programming",
    script_type=ScriptType.TUTORIAL,
    target_duration=600,
    target_audience="Industrial technicians and engineers",
    keywords=["PLC", "programming", "automation"],
    sections=[
        ScriptSection(
            section_id="intro",
            title="Introduction",
            content="Welcome to PLC programming basics...",
            duration_estimate=30,
            voice_style=VoiceStyle.ENTHUSIASTIC,
            visual_cues=["channel_logo", "plc_graphic"],
            order_index=0
        )
    ]
)

# Validate YouTube metadata
metadata = VideoMetadataCreate(
    title="How to Program a PLC",  # Max 100 chars
    description="Full tutorial...",  # Max 5000 chars
    tags=["PLC", "tutorial"],  # Max 15 tags, 30 chars each
    privacy_status=VideoPrivacy.UNLISTED
)
```

**Model Validation Examples:**

```python
# Tags validation (YouTube limits)
try:
    metadata = VideoMetadataCreate(
        title="Test",
        description="Test",
        tags=["a" * 31]  # Exceeds 30 char limit
    )
except ValidationError as e:
    print(e)  # Tag "aaa..." exceeds 30 character limit

# Quality score validation
score = VideoQualityScoreCreate(
    video_id=uuid4(),
    overall_score=83.2,
    metrics=QualityMetrics(
        audio_quality=85.0,
        video_quality=92.0,
        content_quality=78.0,
        technical_quality=88.0,
        seo_score=73.0
    ),
    is_publishable=True,
    needs_improvement=["seo_optimization"]
)
```

---

## Integration Modules

### YouTube Integration (`integrations/youtube.py`)

```python
from ycb.integrations.youtube import YouTubeClient

# Initialize client
client = YouTubeClient()

# Authenticate (opens browser for OAuth)
await client.authenticate()

# Upload video
result = await client.upload_video(
    file_path="./video.mp4",
    title="My Video",
    description="Description here",
    tags=["tag1", "tag2"],
    privacy_status="unlisted",
    thumbnail_path="./thumbnail.png"
)
print(f"Uploaded: https://youtube.com/watch?v={result.video_id}")

# Check quota
quota = await client.get_quota_status()
print(f"Used: {quota.units_used}/{quota.units_limit}")
```

### ElevenLabs Integration (`integrations/elevenlabs.py`)

```python
from ycb.integrations.elevenlabs import ElevenLabsClient

client = ElevenLabsClient()

# Generate narration
audio_path = await client.generate_narration(
    text="Welcome to the tutorial...",
    voice_id="your_voice_id",
    output_path="./narration.mp3",
    stability=0.5,
    similarity_boost=0.75
)

# Clone voice (requires audio samples)
voice_id = await client.clone_voice(
    name="My Voice Clone",
    sample_files=["sample1.mp3", "sample2.mp3"]
)
```

### OpenAI Vision Integration (`integrations/openai_vision.py`)

```python
from ycb.integrations.openai_vision import OpenAIVisionClient

client = OpenAIVisionClient()

# Generate thumbnail
thumbnail = await client.generate_thumbnail(
    prompt="Professional YouTube thumbnail for PLC programming tutorial",
    style="vibrant",
    size="1280x720"
)
await thumbnail.save("./thumbnail.png")

# Analyze existing image
analysis = await client.analyze_image("./existing_thumbnail.png")
print(f"Quality score: {analysis.quality_score}")
```

---

## Creating New Agents

### Agent Template

```python
# ycb/agents/content/my_agent.py
"""
MyAgent - Description of what this agent does

Responsibilities:
- First responsibility
- Second responsibility

Success Metrics:
- Metric 1: target value
- Metric 2: target value
"""

from typing import Dict, Any, Optional
from ycb.core import BaseAgent
from ycb.config import settings
from ycb.models import VideoScript


class MyAgent(BaseAgent):
    """Agent that does something specific."""

    def __init__(self):
        super().__init__("my_agent")
        self.some_config = settings.some_setting

    def _get_capabilities(self) -> Dict[str, Any]:
        return {
            **super()._get_capabilities(),
            "feature_a": True,
            "feature_b": True,
            "version": "1.0.0"
        }

    async def run(self) -> None:
        """Main execution loop."""
        await self.log_info("MyAgent starting...")

        while self.is_running:
            try:
                # Check for work
                work = await self._get_pending_work()

                if work:
                    result = await self._process_work(work)
                    await self._save_result(result)
                else:
                    # No work, wait before checking again
                    await asyncio.sleep(60)

            except Exception as e:
                await self.log_error(f"Processing error: {e}")

    async def _get_pending_work(self) -> Optional[Dict]:
        """Fetch pending work from database."""
        if not self.supabase_client:
            return None

        result = self.supabase_client.table("work_queue")\
            .select("*")\
            .eq("status", "pending")\
            .eq("agent", self.agent_name)\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    async def _process_work(self, work: Dict) -> Dict:
        """Process a work item."""
        await self.log_info(f"Processing: {work['id']}")
        # Implementation here
        return {"status": "completed", "work_id": work["id"]}

    async def _save_result(self, result: Dict) -> None:
        """Save processing result."""
        if self.supabase_client:
            self.supabase_client.table("work_results")\
                .insert(result)\
                .execute()
```

### Registering New Agents

```python
# ycb/agents/content/__init__.py
from .scriptwriter import ScriptwriterAgent
from .my_agent import MyAgent  # Add import

__all__ = [
    "ScriptwriterAgent",
    "MyAgent",  # Add to exports
]
```

---

## Database Schema

### Agent Status Table

```sql
CREATE TABLE ycb_agent_status (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    last_heartbeat TIMESTAMPTZ,
    current_task TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_status_name ON ycb_agent_status(agent_name);
CREATE INDEX idx_agent_status_status ON ycb_agent_status(status);
```

### Agent Logs Table

```sql
CREATE TABLE ycb_agent_logs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    extra_data JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_logs_agent ON ycb_agent_logs(agent_name);
CREATE INDEX idx_agent_logs_level ON ycb_agent_logs(level);
CREATE INDEX idx_agent_logs_timestamp ON ycb_agent_logs(timestamp);
```

### Video Pipeline Table

```sql
CREATE TABLE ycb_video_pipeline (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    script_id UUID REFERENCES ycb_scripts(id),
    script_generated BOOLEAN DEFAULT FALSE,
    voice_generated BOOLEAN DEFAULT FALSE,
    video_rendered BOOLEAN DEFAULT FALSE,
    thumbnail_generated BOOLEAN DEFAULT FALSE,
    uploaded BOOLEAN DEFAULT FALSE,
    youtube_video_id VARCHAR(50),
    youtube_url TEXT,
    quality_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Testing

### Unit Tests

```python
# tests/ycb/test_models.py
import pytest
from ycb.models import VideoScript, ScriptSection, ScriptType, VoiceStyle

def test_video_script_creation():
    script = VideoScript(
        script_id=uuid4(),
        title="Test Script",
        description="Test description",
        script_type=ScriptType.TUTORIAL,
        target_audience="Developers",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    assert script.title == "Test Script"
    assert script.script_type == "tutorial"

def test_section_validation():
    with pytest.raises(ValidationError):
        ScriptSection(
            section_id="test",
            title="Test",
            content="x" * 2001,  # Exceeds 2000 char limit
            order_index=0
        )
```

### Integration Tests

```python
# tests/ycb/test_integration.py
import pytest
from ycb.integrations.youtube import YouTubeClient

@pytest.mark.integration
async def test_youtube_quota_check():
    client = YouTubeClient()
    # This should work without authentication
    assert client.quota_limit == 10000
```

### Running Tests

```bash
# Run all YCB tests
pytest tests/ycb/ -v

# Run with coverage
pytest tests/ycb/ --cov=ycb --cov-report=html

# Run integration tests (requires API keys)
pytest tests/ycb/ -v -m integration
```

---

## Error Handling

### Standard Error Pattern

```python
from ycb.core.exceptions import (
    YCBError,
    ConfigurationError,
    APIError,
    QuotaExceededError,
    ValidationError
)

async def my_function():
    try:
        result = await external_api_call()
    except QuotaExceededError:
        # Handle quota exceeded
        await self.log_warning("Quota exceeded, waiting...")
        await asyncio.sleep(3600)
    except APIError as e:
        # Handle API errors
        await self.log_error(f"API error: {e}")
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        await self.log_error(f"Unexpected error: {e}")
        raise YCBError(f"Operation failed: {e}") from e
```

---

## Performance Considerations

### Rate Limiting

```python
# All integrations should implement rate limiting
from asyncio import Semaphore

class RateLimitedClient:
    def __init__(self, max_concurrent: int = 5):
        self._semaphore = Semaphore(max_concurrent)

    async def call_api(self, *args):
        async with self._semaphore:
            return await self._actual_call(*args)
```

### Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache expensive operations
@lru_cache(maxsize=100)
def get_cached_config(key: str) -> str:
    return settings.get(key)

# Time-based cache
class TimedCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (value, datetime.now())
```

---

## Deployment

### Development

```bash
# Install in development mode
poetry install

# Run with hot reload
python -m ycb --debug
```

### Production

```bash
# Install production dependencies only
poetry install --no-dev

# Set production environment
export YCB_ENV=production
export YCB_LOG_LEVEL=INFO

# Run
python -m ycb
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY ycb/ ./ycb/
CMD ["python", "-m", "ycb"]
```

---

## Contributing

### Code Style

- Use `black` for formatting
- Use `isort` for import sorting
- Use `mypy` for type checking
- Follow Google Python Style Guide

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes with tests
3. Run full test suite: `pytest`
4. Update documentation
5. Submit PR with description
