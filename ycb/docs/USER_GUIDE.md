# YouTube Channel Builder (YCB) - User Guide

## What is YCB?

YouTube Channel Builder is an AI-powered automation system that helps you create, manage, and grow a YouTube channel with minimal manual effort. It handles:

- **Script Generation** - AI writes video scripts from your topics
- **Voice Production** - ElevenLabs voice clone narrates your content
- **Thumbnail Creation** - DALL-E generates eye-catching thumbnails
- **Video Assembly** - Automatic audio + visual synchronization
- **YouTube Upload** - OAuth2 authenticated uploads with metadata
- **Social Amplification** - Clips for TikTok, Instagram, Twitter

---

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
poetry install
```

### Step 2: Configure Environment

Add these to your `.env` file:

```bash
# Required - Supabase (agent state tracking)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Required - OpenAI (script generation)
OPENAI_API_KEY=your_openai_key

# Optional - YouTube Upload
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_CHANNEL_ID=your_channel_id

# Optional - Voice Production
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# Optional - Thumbnails
# Uses OPENAI_API_KEY for DALL-E
```

### Step 3: Verify Installation

```bash
python -m ycb --help
```

Expected output:
```
Usage: python -m ycb [OPTIONS] COMMAND [ARGS]...

  YouTube Channel Builder - AI-powered content automation

Commands:
  script     Generate video scripts
  upload     Upload videos to YouTube
  thumbnail  Generate thumbnails
  pipeline   Run full content pipeline
  status     Check system status
```

---

## Core Commands

### Generate a Script

```bash
# Basic script generation
python -m ycb script generate "How to Program a PLC"

# With options
python -m ycb script generate "Motor Control Basics" \
  --type tutorial \
  --duration 600 \
  --audience "industrial technicians" \
  --output ./scripts/motor_control.json
```

**Output:** JSON file with structured script sections, visual cues, and voice directions.

### Generate a Thumbnail

```bash
# Generate thumbnail for a topic
python -m ycb thumbnail generate "PLC Programming Tutorial" \
  --style professional \
  --output ./thumbnails/plc_tutorial.png

# A/B test variants
python -m ycb thumbnail generate "Motor Faults" \
  --variants 3 \
  --output ./thumbnails/motor_faults/
```

### Upload to YouTube

```bash
# Upload with metadata
python -m ycb upload ./videos/plc_basics.mp4 \
  --title "PLC Programming for Beginners" \
  --description "Learn the fundamentals..." \
  --tags "PLC,tutorial,automation" \
  --privacy unlisted

# Schedule upload
python -m ycb upload ./videos/motor_control.mp4 \
  --title "Motor Control Tutorial" \
  --schedule "2026-01-20 14:00"
```

### Run Full Pipeline

```bash
# Generate everything from a topic
python -m ycb pipeline run "Introduction to PLCs" \
  --output ./output/plc_intro/

# What this creates:
# ./output/plc_intro/
#   ├── script.json      # Full video script
#   ├── thumbnail.png    # Generated thumbnail
#   ├── metadata.json    # YouTube metadata
#   └── voice/           # Audio files (if ElevenLabs configured)
```

### Check System Status

```bash
# View all agent status
python -m ycb status

# View quota usage
python -m ycb status --quota

# View recent activity
python -m ycb status --activity
```

---

## Workflow Examples

### Example 1: Create a Tutorial Video

```bash
# Step 1: Generate script
python -m ycb script generate "How to Wire a VFD" \
  --type tutorial \
  --duration 480 \
  --output ./vfd_wiring/script.json

# Step 2: Review and edit script (manual step)
# Open ./vfd_wiring/script.json in your editor

# Step 3: Generate thumbnail
python -m ycb thumbnail generate "VFD Wiring Tutorial" \
  --style technical \
  --output ./vfd_wiring/thumbnail.png

# Step 4: Record/render video (manual or via video assembly)

# Step 5: Upload to YouTube
python -m ycb upload ./vfd_wiring/final.mp4 \
  --title "How to Wire a VFD - Complete Tutorial" \
  --description "$(cat ./vfd_wiring/description.txt)" \
  --thumbnail ./vfd_wiring/thumbnail.png \
  --tags "VFD,wiring,tutorial,electrical" \
  --privacy public
```

### Example 2: Batch Content Creation

```bash
# Create multiple scripts at once
for topic in "PLC Basics" "Ladder Logic" "Timer Instructions" "Counter Instructions"; do
  python -m ycb script generate "$topic" \
    --type tutorial \
    --output "./plc_series/${topic// /_}.json"
done
```

### Example 3: Autopilot Mode (Fully Automated)

```bash
# WARNING: This will generate and optionally publish content automatically
python -m ycb autopilot "Industrial Maintenance Tips" \
  --count 5 \
  --schedule-start "2026-01-20 10:00" \
  --schedule-interval 48h \
  --dry-run  # Remove to actually publish
```

---

## Configuration Reference

### YCB Settings (in .env)

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `SUPABASE_URL` | Yes | Supabase project URL | - |
| `SUPABASE_KEY` | Yes | Supabase anon key | - |
| `OPENAI_API_KEY` | Yes | OpenAI API key | - |
| `YOUTUBE_CLIENT_ID` | For upload | YouTube OAuth client ID | - |
| `YOUTUBE_CLIENT_SECRET` | For upload | YouTube OAuth secret | - |
| `YOUTUBE_CHANNEL_ID` | For upload | Target channel ID | - |
| `ELEVENLABS_API_KEY` | For voice | ElevenLabs API key | - |
| `ELEVENLABS_VOICE_ID` | For voice | Voice clone ID | - |
| `YCB_OUTPUT_DIR` | No | Output directory | `./ycb_output` |
| `YCB_MAX_VIDEOS_PER_DAY` | No | Daily limit | `5` |
| `YCB_DEFAULT_PRIVACY` | No | Default privacy | `private` |
| `YCB_AUTO_PUBLISH` | No | Auto-publish enabled | `false` |

### Script Types

| Type | Description | Best For |
|------|-------------|----------|
| `tutorial` | Step-by-step educational | How-to videos |
| `review` | Product/service analysis | Equipment reviews |
| `commentary` | Opinion/discussion | Industry news |
| `news` | Current events | Announcements |
| `documentary` | In-depth exploration | Case studies |

### Voice Styles

| Style | Description |
|-------|-------------|
| `professional` | Formal, business-like |
| `casual` | Relaxed, conversational |
| `enthusiastic` | High energy, excited |
| `educational` | Teaching, informative |
| `narrative` | Storytelling |
| `news_anchor` | News broadcast style |

---

## Troubleshooting

### "SUPABASE_URL not configured"

Add Supabase credentials to your `.env` file:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### "YouTube OAuth failed"

1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials
3. Download `client_secrets.json`
4. Run: `python -m ycb auth youtube`
5. Follow browser prompts

### "ElevenLabs quota exceeded"

Check your ElevenLabs plan limits:
- Free: 10,000 characters/month
- Starter: 30,000 characters/month
- Creator: 100,000 characters/month

### "Script generation failed"

1. Check OpenAI API key is valid
2. Verify you have API credits
3. Try with a simpler topic first

---

## Best Practices

### Content Quality

1. **Review AI-generated scripts** - Always check for accuracy
2. **Add personal touches** - Include your expertise
3. **Verify technical claims** - AI can hallucinate
4. **Test thumbnails** - Use A/B variants

### YouTube Optimization

1. **Titles**: Keep under 60 characters
2. **Descriptions**: Include keywords naturally
3. **Tags**: Use 10-15 relevant tags
4. **Thumbnails**: High contrast, readable text
5. **Scheduling**: Post at optimal times (use analytics)

### API Usage

1. **Batch operations** when possible
2. **Monitor quota** usage daily
3. **Use `--dry-run`** before bulk operations
4. **Cache results** to avoid redundant calls

---

## Getting Help

- **Documentation**: See `ycb/docs/` folder
- **Issues**: Report bugs in project issue tracker
- **Logs**: Check `./logs/ycb.log` for errors

---

## Next Steps

1. [Implementation Guide](./IMPLEMENTATION_GUIDE.md) - For developers
2. [Computer Use Guide](./COMPUTER_USE_GUIDE.md) - For automation
3. [API Reference](./API_REFERENCE.md) - Full API documentation
