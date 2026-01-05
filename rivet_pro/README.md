# Rivet Pro

AI-powered industrial maintenance assistant for field technicians. Send a photo of any equipment nameplate and get the manual instantly.

## Phase 1: Walking Skeleton ✅

Current status: Basic infrastructure is complete.

### What's Working

- Project structure with all directories
- Pydantic settings configuration from environment variables
- Telegram bot that responds to messages
- Database connection to Neon PostgreSQL
- Logging infrastructure

### Quick Start

1. **Install Dependencies**

```bash
cd rivet_pro
pip install -r requirements.txt
```

2. **Configure Environment**

```bash
cp .env.example .env
# Edit .env and add your credentials
```

Required for Phase 1:
- `TELEGRAM_BOT_TOKEN` - Get from [@BotFather](https://t.me/BotFather)
- `DATABASE_URL` - Your Neon PostgreSQL connection string

3. **Run the Bot**

```bash
python -m rivet_pro.main
```

4. **Test**

Open Telegram and message your bot. You should get an "I'm alive" response.

## Architecture

```
rivet_pro/
├── core/                      # Platform-agnostic business logic
│   ├── ocr/                   # OCR pipeline (Phase 2)
│   ├── knowledge/             # Knowledge base (Phase 4)
│   ├── matching/              # Equipment matching (Phase 3)
│   ├── reasoning/             # LLM orchestration (Phase 6)
│   ├── models/                # Pydantic models
│   ├── workflows/             # LangGraph workflows
│   └── nodes/                 # Individual workflow nodes
├── adapters/                  # Platform-specific implementations
│   ├── telegram/              # Telegram bot ✅
│   └── whatsapp/              # WhatsApp (Future)
├── infra/
│   ├── database.py            # Neon PostgreSQL ✅
│   ├── redis.py               # Redis (Phase 2)
│   └── observability.py       # Logging ✅
├── config/
│   └── settings.py            # Pydantic settings ✅
└── main.py                    # Application entrypoint ✅
```

## Next Steps: Phase 2

- Photo handler receives image
- OCR pipeline with Groq (single provider first)
- Return extracted text to user
- Add fallback providers

## Development

### Testing

```bash
pytest
```

### Code Quality

```bash
black rivet_pro/
ruff check rivet_pro/
mypy rivet_pro/
```

## Documentation

- [Build Specification](../RIVET_PRO_BUILD_SPEC.md) - Complete product requirements
- [LangGraph Layer](../RIVET_PRO_LANGGRAPH_LAYER.md) - Workflow architecture

## License

Proprietary
