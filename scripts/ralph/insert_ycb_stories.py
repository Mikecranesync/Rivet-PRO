#!/usr/bin/env python3
"""Insert YCB stories into ralph_stories table."""

import os
import sys
from pathlib import Path

# Load DATABASE_URL from .env
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

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
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

import psycopg2

# YCB Stories from PRD
STORIES = [
    # Phase 1: Foundation
    ("YCB-1.1", "Create feature branch and YCB directory structure",
     """Create the feature/youtube-channel-builder branch in the Rivet-PRO repo and set up the complete ycb/ directory structure with all __init__.py files.

Target structure:
ycb/
├── __init__.py
├── config.py
├── agents/
│   ├── __init__.py
│   ├── content/__init__.py
│   ├── media/__init__.py
│   ├── engagement/__init__.py
│   └── committees/__init__.py
├── core/__init__.py
├── integrations/__init__.py
├── models/__init__.py
└── cli/__init__.py

Project root: C:\\Users\\hharp\\OneDrive\\Desktop\\Rivet-PRO""",
     ["Feature branch feature/youtube-channel-builder created", "All directories exist under ycb/", "All __init__.py files created"], 1),

    ("YCB-1.2", "Create YCB configuration system",
     """Create ycb/config.py with Pydantic BaseSettings for environment variable management.

Required settings: SUPABASE_URL, SUPABASE_KEY, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_CHANNEL_ID, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY, YCB_OUTPUT_DIR, YCB_MAX_VIDEOS_PER_DAY, YCB_DEFAULT_PRIVACY, YCB_AUTO_PUBLISH

Use pydantic-settings with .env file support.""",
     ["ycb/config.py exists with Settings class", "Import works: from ycb.config import settings"], 2),

    ("YCB-1.3", "Create BaseAgent class with Supabase integration",
     """Create ycb/core/base_agent.py with abstract BaseAgent class.

Features: Supabase client initialization, Agent status registration, Heartbeat method, Abstract run() method, Logging setup

Pattern: class BaseAgent(ABC) with __init__(agent_name) and _register_status() methods.""",
     ["ycb/core/base_agent.py exists", "BaseAgent is abstract with run() method", "Import works: from ycb.core.base_agent import BaseAgent"], 3),

    ("YCB-1.4", "Create Pydantic models for video and script",
     """Create ycb/models/video.py and ycb/models/script.py with Pydantic models.

Models: VideoScript, VideoMetadata, UploadJob, VideoQualityScore

Use Pydantic v2 syntax with Field validators.""",
     ["ycb/models/video.py exists", "ycb/models/script.py exists", "All models use Pydantic v2 syntax"], 4),

    ("YCB-1.5", "Extract and adapt ScriptwriterAgent",
     """Copy Agent Factory scriptwriter_agent.py to ycb/agents/content/scriptwriter.py and adapt imports.

Source: C:\\Users\\hharp\\OneDrive\\Desktop\\Agent Factory\\agents\\content\\scriptwriter_agent.py
Target: C:\\Users\\hharp\\OneDrive\\Desktop\\Rivet-PRO\\ycb\\agents\\content\\scriptwriter.py

Changes: Replace agent_factory.* -> ycb.*, Keep 4-agent chain logic""",
     ["ycb/agents/content/scriptwriter.py exists", "All imports use ycb.* namespace", "Import works: from ycb.agents.content.scriptwriter import ScriptwriterAgent"], 5),

    ("YCB-1.6", "Extract and adapt YouTubeUploaderAgent",
     """Copy Agent Factory youtube_uploader_agent.py to ycb/agents/media/youtube_uploader.py and adapt imports.

Source: C:\\Users\\hharp\\OneDrive\\Desktop\\Agent Factory\\agents\\media\\youtube_uploader_agent.py
Target: C:\\Users\\hharp\\OneDrive\\Desktop\\Rivet-PRO\\ycb\\agents\\media\\youtube_uploader.py

Changes: Replace agent_factory.* -> ycb.*, Keep OAuth2 flow and resumable uploads""",
     ["ycb/agents/media/youtube_uploader.py exists", "All imports use ycb.* namespace", "OAuth2 credential handling preserved"], 6),

    ("YCB-1.7", "Create CLI with Click framework",
     """Create ycb/cli/main.py with Click-based command-line interface.

Commands: ycb script generate "topic", ycb upload video.mp4, ycb --help

Add ycb/__main__.py to enable: python -m ycb""",
     ["ycb/cli/main.py exists with Click CLI", "python -m ycb --help works"], 7),

    ("YCB-1.8", "Create integration module stubs",
     """Create stub files:
- ycb/integrations/youtube.py - YouTube Data API v3 wrapper
- ycb/integrations/elevenlabs.py - ElevenLabs voice API
- ycb/integrations/openai_vision.py - DALL-E thumbnail API

Each stub: Class with NotImplementedError methods, Docstrings, Type hints""",
     ["ycb/integrations/youtube.py exists", "ycb/integrations/elevenlabs.py exists", "All stubs have proper type hints"], 8),

    ("YCB-1.9", "Verify Phase 1 and commit",
     """Run all Phase 1 verification commands and commit changes.

Verification:
python -c "from ycb.agents.content.scriptwriter import ScriptwriterAgent; print('OK')"
python -c "from ycb.agents.media.youtube_uploader import YouTubeUploaderAgent; print('OK')"
python -c "from ycb.config import settings; print('OK')"
python -m ycb --help

Commit: git add ycb/ && git commit -m "feat(ycb): Phase 1 - Core agent extraction and module structure" """,
     ["All import verification commands pass", "Git commit created"], 9),

    # Phase 2: Content Pipeline
    ("YCB-2.1", "Implement ContentResearcherAgent",
     """Create ycb/agents/content/researcher.py that queries the knowledge base for video topics.

Features: research_topic(topic) -> List[KBAtom], gather_sources(topic) -> List[Source], Supabase KB integration, Semantic search""",
     ["ycb/agents/content/researcher.py exists", "research_topic method works"], 10),

    ("YCB-2.2", "Implement ContentEnricherAgent",
     """Create ycb/agents/content/enricher.py that creates structured outlines from research.

Features: create_outline(atoms) -> Outline, expand_sections(outline) -> DetailedOutline, LLM integration""",
     ["ycb/agents/content/enricher.py exists", "create_outline method works"], 11),

    ("YCB-2.3", "Implement SEOAgent",
     """Create ycb/agents/content/seo.py for search engine optimization.

Features: optimize_title(title, keywords) -> str, generate_tags(content) -> List[str], keyword_research(topic) -> List[Keyword]""",
     ["ycb/agents/content/seo.py exists", "optimize_title returns SEO-friendly titles"], 12),

    ("YCB-2.4", "Implement TrendScoutAgent",
     """Create ycb/agents/content/trend_scout.py for topic discovery.

Features: discover_trends(niche) -> List[TrendingTopic], analyze_competition(topic) -> CompetitorAnalysis""",
     ["ycb/agents/content/trend_scout.py exists", "discover_trends returns topics"], 13),

    ("YCB-2.5", "Implement QualityEnhancerAgent",
     """Create ycb/agents/content/quality_enhancer.py for quality gates.

Features: score_script(script) -> QualityScore, enhance_if_needed(script, threshold=80) -> VideoScript, GPT-4 enhancement""",
     ["ycb/agents/content/quality_enhancer.py exists", "score_script returns 0-100 score"], 14),

    ("YCB-2.6", "Create content pipeline orchestrator",
     """Create ycb/core/orchestrator.py that chains content agents together.

Pipeline: TrendScout -> Researcher -> Enricher -> Scriptwriter -> QualityEnhancer -> SEO

Method: run_pipeline(topic) -> VideoPackage""",
     ["ycb/core/orchestrator.py exists", "run_pipeline chains all agents"], 15),

    ("YCB-2.7", "Add pipeline CLI command",
     """Add pipeline command to ycb/cli/main.py:

python -m ycb pipeline run "Motor Control Basics" --output video_package/

Features: Takes topic as argument, --output for save location, --dry-run to preview""",
     ["python -m ycb pipeline run works", "--dry-run shows preview"], 16),

    ("YCB-2.8", "Phase 2 verification and commit",
     """Run Phase 2 verification and commit:

python -m ycb pipeline run "Test Topic" --dry-run

Commit: git commit -m "feat(ycb): Phase 2 - Content pipeline agents" """,
     ["Pipeline dry-run works", "Git commit created"], 17),

    # Phase 3: Media Production
    ("YCB-3.1", "Implement VoiceProductionAgent with ElevenLabs",
     """Create ycb/agents/media/voice_production.py for narration generation.

Features: clone_voice(sample_path) -> VoiceID, generate_narration(script) -> AudioFile, ElevenLabs API integration""",
     ["ycb/agents/media/voice_production.py exists", "ycb/integrations/elevenlabs.py implemented"], 20),

    ("YCB-3.2", "Implement ThumbnailAgent with DALL-E",
     """Create ycb/agents/content/thumbnail.py for thumbnail generation.

Features: generate_thumbnail(topic, style) -> ImagePath, ab_test_thumbnails(variants) -> Ranking, DALL-E 3 integration""",
     ["ycb/agents/content/thumbnail.py exists", "generate_thumbnail creates 1280x720 image"], 21),

    ("YCB-3.3", "Implement VideoAssemblyAgent with MoviePy",
     """Create ycb/agents/media/video_assembly.py for video rendering.

Features: sync_audio_visuals(audio, visuals) -> VideoClip, render_video(clip, output) -> VideoPath, MoviePy for composition""",
     ["ycb/agents/media/video_assembly.py exists", "MoviePy dependency installed"], 22),

    ("YCB-3.4", "Add render CLI command",
     """Add render command to ycb/cli/main.py:

python -m ycb render --script script.json --output video.mp4

Features: Takes script JSON, --output for video path, --dry-run preview""",
     ["python -m ycb render works", "--dry-run shows render plan"], 23),

    ("YCB-3.5", "Phase 3 verification and commit",
     """Run Phase 3 verification and commit:

python -m ycb render --script test_script.json --output test.mp4 --dry-run

Commit: git commit -m "feat(ycb): Phase 3 - Media production agents" """,
     ["Render dry-run works", "Git commit created"], 24),

    # Phase 4: Publishing & Amplification
    ("YCB-4.1", "Implement PublishingStrategyAgent",
     """Create ycb/agents/media/publishing_strategy.py for optimal timing.

Features: optimal_timing(channel_analytics) -> datetime, schedule_upload(video, publish_at) -> ScheduledJob""",
     ["ycb/agents/media/publishing_strategy.py exists", "optimal_timing returns datetime"], 30),

    ("YCB-4.2", "Implement SocialAmplifierAgent",
     """Create ycb/agents/engagement/social_amplifier.py for multi-platform distribution.

Features: extract_clips(video, count=3) -> List[ClipPath], post_to_tiktok, post_to_instagram (stubs)""",
     ["ycb/agents/engagement/social_amplifier.py exists", "extract_clips generates short clips"], 31),

    ("YCB-4.3", "Implement AnalyticsAgent",
     """Create ycb/agents/engagement/analytics.py for performance tracking.

Features: track_metrics(video_id) -> VideoMetrics, generate_insights(videos) -> InsightReport, YouTube Analytics API""",
     ["ycb/agents/engagement/analytics.py exists", "track_metrics fetches video stats"], 32),

    ("YCB-4.4", "Add publish CLI command",
     """Add publish command to ycb/cli/main.py:

python -m ycb publish video.mp4 --schedule "2026-01-25 10:00"

Features: Upload to YouTube, Set thumbnail, Schedule publish, --amplify for social distribution""",
     ["python -m ycb publish works", "--schedule sets publish time"], 33),

    ("YCB-4.5", "Add autopilot CLI command",
     """Add autopilot command to ycb/cli/main.py:

python -m ycb autopilot "PLC Programming" --publish-at "2026-01-25 10:00"

Full automation: Research -> Script -> Narration -> Render -> Thumbnail -> Upload -> Clips -> Social""",
     ["python -m ycb autopilot works end-to-end", "--dry-run previews full pipeline"], 34),

    ("YCB-4.6", "Phase 4 verification and commit",
     """Run Phase 4 verification and commit:

python -m ycb autopilot "Test Topic" --dry-run

Commit: git commit -m "feat(ycb): Phase 4 - Publishing and amplification" """,
     ["Autopilot dry-run works", "Git commit created"], 35),

    # Final
    ("YCB-5.1", "Push feature branch and create PR",
     """Push all changes and create pull request:

git push -u origin feature/youtube-channel-builder

gh pr create --title "feat: YouTube Channel Builder (YCB) Module" --body "Autonomous YouTube channel growth" """,
     ["Feature branch pushed", "Pull request created on GitHub"], 40),
]

def main():
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    print("[OK] Connected")

    # Clear existing YCB stories
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ralph_stories WHERE story_id LIKE 'YCB-%'")
        deleted = cur.rowcount
        print(f"Deleted {deleted} existing YCB stories")

    # Insert new stories
    import json
    with conn.cursor() as cur:
        for story_id, title, description, acceptance_criteria, priority in STORIES:
            cur.execute("""
                INSERT INTO ralph_stories
                (project_id, story_id, title, description, acceptance_criteria, priority, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (1, story_id, title, description, json.dumps(acceptance_criteria), priority, 'todo'))

    conn.commit()
    print(f"Inserted {len(STORIES)} YCB stories")

    # Show summary
    with conn.cursor() as cur:
        cur.execute("SELECT story_id, title, priority FROM ralph_stories WHERE story_id LIKE 'YCB-%' ORDER BY priority")
        rows = cur.fetchall()
        print(f"\n{'='*70}")
        print("YCB Stories Ready for Ralph")
        print(f"{'='*70}")
        for story_id, title, priority in rows:
            print(f"  [{priority:2d}] {story_id}: {title[:50]}...")

    conn.close()
    print(f"\nRun: python scripts/ralph/ralph_api.py --prefix YCB")

if __name__ == "__main__":
    main()
