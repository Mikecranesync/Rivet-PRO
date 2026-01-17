# YCB Documentation

YouTube Channel Builder (YCB) - AI-powered content automation for YouTube.

## Guides

| Guide | Audience | Description |
|-------|----------|-------------|
| [User Guide](./USER_GUIDE.md) | End Users | How to use YCB commands, configuration, and workflows |
| [Implementation Guide](./IMPLEMENTATION_GUIDE.md) | Developers | Architecture, creating agents, testing, deployment |
| [Computer Use Guide](./COMPUTER_USE_GUIDE.md) | DevOps/Automation | Scheduled tasks, daemons, Claude integration, monitoring |

## Quick Links

### Getting Started
```bash
# Install
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
poetry install

# Configure (add to .env)
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
OPENAI_API_KEY=your_key

# Verify
python -m ycb --help
```

### Common Commands
```bash
python -m ycb script generate "Topic"      # Generate script
python -m ycb thumbnail generate "Topic"   # Generate thumbnail
python -m ycb upload video.mp4 --title "T" # Upload video
python -m ycb pipeline run "Topic"         # Full pipeline
python -m ycb status                       # Check status
```

### Architecture
```
ycb/
├── config.py          # Configuration (Pydantic Settings)
├── core/              # BaseAgent, infrastructure
├── models/            # Pydantic v2 data models
├── agents/            # AI agents (18 planned)
│   ├── content/       # Script, SEO, research agents
│   ├── media/         # Upload, voice, video agents
│   ├── engagement/    # Social, analytics agents
│   └── committees/    # Multi-agent decision groups
├── integrations/      # YouTube, ElevenLabs, OpenAI APIs
└── cli/               # Command-line interface
```

## Current Status

**Completed (5/29 stories):**
- Directory structure and config
- BaseAgent with Supabase
- Video/Script Pydantic models
- Integration stubs (YouTube, ElevenLabs, OpenAI)

**In Progress:**
- Content agents (Scriptwriter, SEO, etc.)
- Media production pipeline
- CLI commands

## Support

- Issues: Project issue tracker
- Logs: `./logs/ycb.log`
- Status: `python -m ycb status`
