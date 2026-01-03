# RIVET Pro 2.0

Industrial maintenance AI assistant for field technicians.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Mikecranesync/Rivet-PRO.git
cd Rivet-PRO
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Test
pytest tests/ -v

# Run bot (Phase 3)
python -m rivet.integrations.telegram
```

## Features

- **Multi-Provider OCR**: Cost-optimized photo analysis (Groq → Gemini → Claude → GPT-4o)
- **4-Route Troubleshooting**: KB → SME → Research → General
- **Subscription Tiers**: Beta (free) / Pro ($29) / Team ($200)
- **Full Observability**: Phoenix + LangSmith tracing

## Architecture

```
Query → OCR (if photo) → Route Decision → KB/SME/Research/General → Response
```

## Tiers

| Tier | Price | Limits |
|------|-------|--------|
| Beta | Free | 50 queries/day, 7-day trial |
| Pro | $29/mo | 1000 queries/day, unlimited prints |
| Team | $200/mo | 10 users, shared library, API access |

## Phase 1 Status

✅ Repository structure
✅ Multi-provider OCR workflow
✅ Configuration system with tier limits
✅ Equipment identification with normalization
✅ Phoenix + LangSmith observability
✅ Full test coverage

**Next: Phase 2** - 4-route troubleshooting orchestrator + SME prompts

## Development

```bash
# Run tests
pytest tests/ -v

# Check config
python -c "from rivet.config import config; config.log_status()"

# Test OCR
python scripts/test_ocr_local.py
```

## License

MIT
