-- Ralph Stories: YouTube Channel Builder (YCB)
-- Generated from PRD: C:\Users\hharp\.claude\plans\steady-drifting-barto.md
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_ycb_stories.sql

-- Clear any existing YCB stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'YCB-%';

-- ============================================================================
-- PHASE 1: FOUNDATION (Priority 1-10)
-- Goal: Extract core agents, establish module structure
-- ============================================================================

INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

-- YCB-1.1: Create feature branch and directory structure
(1, 'YCB-1.1', 'Create feature branch and YCB directory structure',
'Create the feature/youtube-channel-builder branch in the Rivet-PRO repo and set up the complete ycb/ directory structure with all __init__.py files.

Target structure:
ycb/
├── __init__.py
├── config.py
├── agents/
│   ├── __init__.py
│   ├── content/
│   │   └── __init__.py
│   ├── media/
│   │   └── __init__.py
│   ├── engagement/
│   │   └── __init__.py
│   └── committees/
│       └── __init__.py
├── core/
│   └── __init__.py
├── integrations/
│   └── __init__.py
├── models/
│   └── __init__.py
└── cli/
    └── __init__.py

Project root: C:\Users\hharp\OneDrive\Desktop\Rivet-PRO',
'["Feature branch feature/youtube-channel-builder created", "All directories exist under ycb/", "All __init__.py files created with basic exports", "git status shows new files staged"]',
1, 'todo'),

-- YCB-1.2: Create config.py with environment management
(1, 'YCB-1.2', 'Create YCB configuration system',
'Create ycb/config.py with Pydantic BaseSettings for environment variable management.

Required settings:
- SUPABASE_URL, SUPABASE_KEY (existing)
- YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_CHANNEL_ID
- ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
- OPENAI_API_KEY
- YCB_OUTPUT_DIR (default: ./ycb_output)
- YCB_MAX_VIDEOS_PER_DAY (default: 3)
- YCB_DEFAULT_PRIVACY (default: unlisted)
- YCB_AUTO_PUBLISH (default: false)

Use pydantic-settings with .env file support.',
'["ycb/config.py exists with Settings class", "All environment variables have defaults or are optional", "Import works: from ycb.config import settings", "Settings load from .env file"]',
2, 'todo'),

-- YCB-1.3: Create base agent class
(1, 'YCB-1.3', 'Create BaseAgent class with Supabase integration',
'Create ycb/core/base_agent.py with abstract BaseAgent class.

Features:
- Supabase client initialization from config
- Agent status registration in ycb_agent_status table
- Heartbeat method for status updates
- Abstract run() method
- Logging setup

Pattern from PRD:
```python
class BaseAgent(ABC):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self._register_status()
```',
'["ycb/core/base_agent.py exists with BaseAgent class", "BaseAgent is abstract with run() method", "Supabase client initializes correctly", "Import works: from ycb.core.base_agent import BaseAgent"]',
3, 'todo'),

-- YCB-1.4: Create Pydantic models for video pipeline
(1, 'YCB-1.4', 'Create Pydantic models for video and script',
'Create ycb/models/video.py and ycb/models/script.py with Pydantic models.

Models needed:
- VideoScript (title, sections, visual_cues, personality_markers)
- VideoMetadata (title, description, tags, thumbnail_path)
- UploadJob (video_path, metadata, status, youtube_id)
- VideoQualityScore (score, issues, recommendations)

Use Pydantic v2 syntax with Field validators.',
'["ycb/models/video.py exists with VideoMetadata, UploadJob models", "ycb/models/script.py exists with VideoScript model", "All models use Pydantic v2 syntax", "Import works: from ycb.models import VideoScript, UploadJob"]',
4, 'todo'),

-- YCB-1.5: Extract ScriptwriterAgent from Agent Factory
(1, 'YCB-1.5', 'Extract and adapt ScriptwriterAgent',
'Copy Agent Factory scriptwriter_agent.py to ycb/agents/content/scriptwriter.py and adapt imports.

Source: C:\Users\hharp\OneDrive\Desktop\Agent Factory\agents\content\scriptwriter_agent.py
Target: C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\ycb\agents\content\scriptwriter.py

Changes required:
- Replace: from agent_factory.* -> from ycb.*
- Update: BaseAgent import to use ycb.core.base_agent
- Update: Settings import to use ycb.config
- Keep: 4-agent chain logic (researcher, outliner, writer, editor)
- Keep: KB query integration
- Keep: Personality markers and visual cues',
'["ycb/agents/content/scriptwriter.py exists (~900-1000 lines)", "All imports use ycb.* namespace", "ScriptwriterAgent class inherits from BaseAgent", "Import works: from ycb.agents.content.scriptwriter import ScriptwriterAgent"]',
5, 'todo'),

-- YCB-1.6: Extract YouTubeUploaderAgent from Agent Factory
(1, 'YCB-1.6', 'Extract and adapt YouTubeUploaderAgent',
'Copy Agent Factory youtube_uploader_agent.py to ycb/agents/media/youtube_uploader.py and adapt imports.

Source: C:\Users\hharp\OneDrive\Desktop\Agent Factory\agents\media\youtube_uploader_agent.py
Target: C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\ycb\agents\media\youtube_uploader.py

Changes required:
- Replace: from agent_factory.* -> from ycb.*
- Update: BaseAgent import to use ycb.core.base_agent
- Update: Settings import to use ycb.config
- Keep: OAuth2 flow for YouTube API
- Keep: Resumable upload support
- Keep: Thumbnail setting
- Keep: Quota management',
'["ycb/agents/media/youtube_uploader.py exists (~600-700 lines)", "All imports use ycb.* namespace", "YouTubeUploaderAgent class inherits from BaseAgent", "OAuth2 credential handling preserved", "Import works: from ycb.agents.media.youtube_uploader import YouTubeUploaderAgent"]',
6, 'todo'),

-- YCB-1.7: Create CLI entry point
(1, 'YCB-1.7', 'Create CLI with Click framework',
'Create ycb/cli/main.py with Click-based command-line interface.

Commands to implement:
- ycb script generate "topic" - Generate script using ScriptwriterAgent
- ycb upload video.mp4 --title "..." --description "..." - Upload video
- ycb --help - Show help

Add ycb/__main__.py to enable: python -m ycb

Use Rich for formatted output.',
'["ycb/cli/main.py exists with Click CLI", "ycb/__main__.py enables python -m ycb", "python -m ycb --help shows available commands", "Commands use Rich for formatting"]',
7, 'todo'),

-- YCB-1.8: Create integrations stubs
(1, 'YCB-1.8', 'Create integration module stubs',
'Create stub files for all integrations:
- ycb/integrations/youtube.py - YouTube Data API v3 wrapper (stub)
- ycb/integrations/elevenlabs.py - ElevenLabs voice API (stub)
- ycb/integrations/openai_vision.py - DALL-E thumbnail API (stub)

Each stub should have:
- Class with NotImplementedError methods
- Docstrings explaining what it will do
- Type hints for all methods',
'["ycb/integrations/youtube.py exists with YouTubeClient class stub", "ycb/integrations/elevenlabs.py exists with ElevenLabsClient class stub", "ycb/integrations/openai_vision.py exists with DALLEClient class stub", "All stubs have proper type hints and docstrings"]',
8, 'todo'),

-- YCB-1.9: Phase 1 verification and commit
(1, 'YCB-1.9', 'Verify Phase 1 and commit',
'Run all Phase 1 verification commands and commit changes.

Verification commands:
python -c "from ycb.agents.content.scriptwriter import ScriptwriterAgent; print(''OK'')"
python -c "from ycb.agents.media.youtube_uploader import YouTubeUploaderAgent; print(''OK'')"
python -c "from ycb.config import settings; print(''OK'')"
python -m ycb --help

If all pass, commit with:
git add ycb/
git commit -m "feat(ycb): Phase 1 - Core agent extraction and module structure"',
'["All import verification commands pass", "python -m ycb --help works", "Git commit created with correct message", "No import errors or warnings"]',
9, 'todo'),

-- ============================================================================
-- PHASE 2: CONTENT PIPELINE (Priority 10-20)
-- Goal: Complete content production chain
-- ============================================================================

(1, 'YCB-2.1', 'Implement ContentResearcherAgent',
'Create ycb/agents/content/researcher.py that queries the knowledge base for video topics.

Features:
- research_topic(topic: str) -> List[KBAtom]
- gather_sources(topic: str) -> List[Source]
- Supabase KB integration
- Semantic search for related content

Should inherit from BaseAgent and use existing KB query patterns from scriptwriter.',
'["ycb/agents/content/researcher.py exists", "research_topic method queries KB successfully", "Returns list of relevant knowledge atoms", "Import works: from ycb.agents.content.researcher import ContentResearcherAgent"]',
10, 'todo'),

(1, 'YCB-2.2', 'Implement ContentEnricherAgent',
'Create ycb/agents/content/enricher.py that creates structured outlines from research.

Features:
- create_outline(atoms: List[KBAtom]) -> Outline
- expand_sections(outline: Outline) -> DetailedOutline
- LLM integration for expansion
- Maintains educational structure (intro, body, conclusion)',
'["ycb/agents/content/enricher.py exists", "create_outline method generates structured outline", "expand_sections adds detail to each section", "Import works: from ycb.agents.content.enricher import ContentEnricherAgent"]',
11, 'todo'),

(1, 'YCB-2.3', 'Implement SEOAgent',
'Create ycb/agents/content/seo.py for search engine optimization.

Features:
- optimize_title(title: str, keywords: List[str]) -> str
- generate_tags(content: str) -> List[str]
- keyword_research(topic: str) -> List[Keyword]
- generate_description(script: VideoScript) -> str

Use YouTube search trends if available, fallback to LLM suggestions.',
'["ycb/agents/content/seo.py exists", "optimize_title returns SEO-friendly titles", "generate_tags returns relevant YouTube tags", "Import works: from ycb.agents.content.seo import SEOAgent"]',
12, 'todo'),

(1, 'YCB-2.4', 'Implement TrendScoutAgent',
'Create ycb/agents/content/trend_scout.py for topic discovery.

Features:
- discover_trends(niche: str) -> List[TrendingTopic]
- analyze_competition(topic: str) -> CompetitorAnalysis
- Score topics by: search volume, competition, relevance

May use YouTube API trending or web scraping for ideas.',
'["ycb/agents/content/trend_scout.py exists", "discover_trends returns list of topics with scores", "analyze_competition evaluates existing videos", "Import works: from ycb.agents.content.trend_scout import TrendScoutAgent"]',
13, 'todo'),

(1, 'YCB-2.5', 'Implement QualityEnhancerAgent',
'Create ycb/agents/content/quality_enhancer.py for quality gates.

Features:
- score_script(script: VideoScript) -> QualityScore
- enhance_if_needed(script: VideoScript, threshold: int = 80) -> VideoScript
- Uses GPT-4 for enhancement when score < threshold
- Checks: clarity, engagement, accuracy, educational value',
'["ycb/agents/content/quality_enhancer.py exists", "score_script returns 0-100 quality score", "enhance_if_needed triggers LLM enhancement when score < threshold", "Import works: from ycb.agents.content.quality_enhancer import QualityEnhancerAgent"]',
14, 'todo'),

(1, 'YCB-2.6', 'Create content pipeline orchestrator',
'Create ycb/core/orchestrator.py that chains content agents together.

Pipeline:
1. TrendScout discovers topic
2. Researcher gathers KB atoms
3. Enricher creates outline
4. Scriptwriter generates script
5. QualityEnhancer scores/enhances
6. SEO optimizes metadata

Method: run_pipeline(topic: str) -> VideoPackage',
'["ycb/core/orchestrator.py exists with ContentPipeline class", "run_pipeline chains all content agents", "Returns VideoPackage with script + metadata", "Import works: from ycb.core.orchestrator import ContentPipeline"]',
15, 'todo'),

(1, 'YCB-2.7', 'Add pipeline CLI command',
'Add pipeline command to ycb/cli/main.py:

python -m ycb pipeline run "Motor Control Basics" --output video_package/

Features:
- Takes topic as argument
- Optional --output for save location
- Optional --dry-run to preview without saving
- Shows progress with Rich progress bar',
'["python -m ycb pipeline run \"Test Topic\" works", "--dry-run shows preview without saving", "--output saves to specified directory", "Progress bar shows pipeline stages"]',
16, 'todo'),

(1, 'YCB-2.8', 'Phase 2 verification and commit',
'Run Phase 2 verification and commit:

python -m ycb pipeline run "Test Topic" --dry-run

If successful, commit:
git add ycb/
git commit -m "feat(ycb): Phase 2 - Content pipeline agents"',
'["Pipeline dry-run completes without errors", "All content agents import correctly", "Git commit created with correct message"]',
17, 'todo'),

-- ============================================================================
-- PHASE 3: MEDIA PRODUCTION (Priority 20-30)
-- Goal: Audio/visual production automation
-- ============================================================================

(1, 'YCB-3.1', 'Implement VoiceProductionAgent with ElevenLabs',
'Create ycb/agents/media/voice_production.py for narration generation.

Features:
- clone_voice(sample_path: str) -> VoiceID
- generate_narration(script: VideoScript) -> AudioFile
- ElevenLabs API integration via ycb/integrations/elevenlabs.py
- Segment scripts for natural pauses
- Handle API rate limits',
'["ycb/agents/media/voice_production.py exists", "ycb/integrations/elevenlabs.py fully implemented", "generate_narration creates MP3 audio file", "Import works: from ycb.agents.media.voice_production import VoiceProductionAgent"]',
20, 'todo'),

(1, 'YCB-3.2', 'Implement ThumbnailAgent with DALL-E',
'Create ycb/agents/content/thumbnail.py for thumbnail generation.

Features:
- generate_thumbnail(topic: str, style: str) -> ImagePath
- ab_test_thumbnails(variants: List[str]) -> Ranking
- DALL-E 3 integration via ycb/integrations/openai_vision.py
- Pillow for text overlay and effects
- Professional style templates',
'["ycb/agents/content/thumbnail.py exists", "ycb/integrations/openai_vision.py fully implemented", "generate_thumbnail creates 1280x720 image", "Import works: from ycb.agents.content.thumbnail import ThumbnailAgent"]',
21, 'todo'),

(1, 'YCB-3.3', 'Implement VideoAssemblyAgent with MoviePy',
'Create ycb/agents/media/video_assembly.py for video rendering.

Features:
- sync_audio_visuals(audio: AudioFile, visuals: List[Image]) -> VideoClip
- render_video(clip: VideoClip, output: str) -> VideoPath
- MoviePy for video composition
- B-roll image sequencing
- Text overlays for key points
- Fade transitions',
'["ycb/agents/media/video_assembly.py exists", "MoviePy dependency installed", "render_video outputs MP4 file", "Import works: from ycb.agents.media.video_assembly import VideoAssemblyAgent"]',
22, 'todo'),

(1, 'YCB-3.4', 'Add render CLI command',
'Add render command to ycb/cli/main.py:

python -m ycb render --script script.json --output video.mp4

Features:
- Takes script JSON file as input
- Optional --output for video path
- Optional --dry-run to preview without rendering
- Progress bar for render stages',
'["python -m ycb render --script test.json --output test.mp4 works", "--dry-run shows render plan", "Progress shows: narration, thumbnails, assembly, export"]',
23, 'todo'),

(1, 'YCB-3.5', 'Phase 3 verification and commit',
'Run Phase 3 verification and commit:

python -m ycb render --script test_script.json --output test_video.mp4 --dry-run

If successful, commit:
git add ycb/
git commit -m "feat(ycb): Phase 3 - Media production agents"',
'["Render dry-run completes without errors", "All media agents import correctly", "Git commit created with correct message"]',
24, 'todo'),

-- ============================================================================
-- PHASE 4: PUBLISHING & AMPLIFICATION (Priority 30-40)
-- Goal: Automated publishing and social distribution
-- ============================================================================

(1, 'YCB-4.1', 'Implement PublishingStrategyAgent',
'Create ycb/agents/media/publishing_strategy.py for optimal timing.

Features:
- optimal_timing(channel_analytics: dict) -> datetime
- schedule_upload(video: VideoPath, publish_at: datetime) -> ScheduledJob
- Analyze channel audience patterns
- Default to peak times if no analytics',
'["ycb/agents/media/publishing_strategy.py exists", "optimal_timing returns datetime for best publish time", "schedule_upload creates scheduled job", "Import works: from ycb.agents.media.publishing_strategy import PublishingStrategyAgent"]',
30, 'todo'),

(1, 'YCB-4.2', 'Implement SocialAmplifierAgent',
'Create ycb/agents/engagement/social_amplifier.py for multi-platform distribution.

Features:
- extract_clips(video: VideoPath, count: int = 3) -> List[ClipPath]
- post_to_tiktok(clip: ClipPath, caption: str) -> PostID
- post_to_instagram(clip: ClipPath, caption: str) -> PostID
- Stub implementations for TikTok/Instagram APIs
- Extract 15-60 second highlight clips',
'["ycb/agents/engagement/social_amplifier.py exists", "extract_clips generates short clips from video", "Platform posting methods exist (can be stubs)", "Import works: from ycb.agents.engagement.social_amplifier import SocialAmplifierAgent"]',
31, 'todo'),

(1, 'YCB-4.3', 'Implement AnalyticsAgent',
'Create ycb/agents/engagement/analytics.py for performance tracking.

Features:
- track_metrics(video_id: str) -> VideoMetrics
- generate_insights(videos: List[VideoMetrics]) -> InsightReport
- YouTube Analytics API integration
- Store metrics in ycb_published_videos table',
'["ycb/agents/engagement/analytics.py exists", "track_metrics fetches video stats from YouTube", "generate_insights creates performance report", "Import works: from ycb.agents.engagement.analytics import AnalyticsAgent"]',
32, 'todo'),

(1, 'YCB-4.4', 'Add publish CLI command',
'Add publish command to ycb/cli/main.py:

python -m ycb publish video.mp4 --schedule "2026-01-25 10:00"

Features:
- Upload video to YouTube
- Set custom thumbnail
- Schedule publish time
- Optional --amplify to trigger social distribution',
'["python -m ycb publish video.mp4 --title \"...\" works", "--schedule sets publish time", "--amplify triggers clip extraction", "Upload progress shown"]',
33, 'todo'),

(1, 'YCB-4.5', 'Add autopilot CLI command',
'Add autopilot command to ycb/cli/main.py:

python -m ycb autopilot "PLC Programming" --publish-at "2026-01-25 10:00"

Full automation:
1. Research topic
2. Generate script
3. Create narration
4. Render video
5. Generate thumbnail
6. Upload to YouTube
7. Extract clips
8. Post to socials',
'["python -m ycb autopilot \"Topic\" works end-to-end", "--publish-at schedules upload", "--dry-run previews full pipeline", "All stages log progress"]',
34, 'todo'),

(1, 'YCB-4.6', 'Phase 4 verification and commit',
'Run Phase 4 verification and commit:

python -m ycb autopilot "Test Topic" --dry-run --schedule "2026-01-25 10:00"

If successful, commit:
git add ycb/
git commit -m "feat(ycb): Phase 4 - Publishing and amplification"',
'["Autopilot dry-run completes all stages", "All engagement agents import correctly", "Git commit created with correct message"]',
35, 'todo'),

-- ============================================================================
-- FINAL: Push to GitHub and create PR
-- ============================================================================

(1, 'YCB-5.1', 'Push feature branch and create PR',
'Push all changes and create pull request:

git push -u origin feature/youtube-channel-builder

gh pr create --title "feat: YouTube Channel Builder (YCB) Module" \
  --body "Autonomous YouTube channel growth through AI-powered content pipeline

## Summary
- 18-agent content production system
- Full pipeline: research -> script -> media -> publish
- CLI interface for all operations
- Integration stubs for YouTube, ElevenLabs, DALL-E

## Test
\`\`\`bash
python -m ycb --help
python -m ycb autopilot \"Test\" --dry-run
\`\`\`
"',
'["Feature branch pushed to origin", "Pull request created on GitHub", "PR description includes summary and test commands"]',
40, 'todo');
