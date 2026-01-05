# RIVET Pro

AI-powered industrial maintenance assistant for equipment identification and manual delivery.

## 🎯 Mission

Help field technicians identify unfamiliar equipment and access documentation through simple photo-based interaction.

## ✨ Features

**Phase 1: Walking Skeleton** (Current)
- ✅ Telegram bot that responds to messages
- ✅ Database connection testing
- ✅ Clean architecture foundation

**Coming Soon:**
- 📸 Photo → Equipment OCR (Phase 2)
- 🔍 Equipment identification and matching (Phase 3)
- 📖 Automatic manual delivery (Phase 4)
- 🤖 LLM-powered adaptive responses (Phase 6)
- 💬 Chat with manuals via RAG (Phase 7)

## 🏗️ Architecture

```
rivet-pro/
├── core/              # Platform-agnostic business logic
│   ├── ocr/          # Multi-provider OCR pipeline
│   ├── knowledge/    # Manual search & indexing
│   ├── matching/     # Equipment classification
│   ├── reasoning/    # LLM orchestrator
│   └── models/       # Pydantic data models
├── adapters/          # Platform-specific implementations
│   ├── telegram/     # Telegram bot (current)
│   └── whatsapp/     # WhatsApp (future)
├── infra/            # Infrastructure services
│   ├── database.py   # PostgreSQL (asyncpg)
│   ├── redis.py      # Caching
│   └── storage.py    # PDF storage
├── config/           # Configuration management
└── main.py           # Application entrypoint
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (Neon, Supabase, or local)
- Telegram bot token from [@BotFather](https://t.me/botfather)
- API keys for AI providers (Groq, Anthropic, OpenAI, Google)

### Installation

1. **Clone and navigate:**
   ```bash
   cd rivet-pro
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

All configuration is done via environment variables (`.env` file):

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram bot token from BotFather |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `GROQ_API_KEY` | ✅ | Groq API key (free tier available) |
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `GOOGLE_API_KEY` | ✅ | Google AI API key |
| `BETA_MODE` | ❌ | Unlock all features (default: true) |

See `.env.example` for complete list.

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Type checking
mypy .

# Linting
flake8 .
black --check .
```

## 📖 Development Workflow

Phase 1: Walking Skeleton (Current)
- [x] Project structure
- [x] Settings loading
- [x] Basic Telegram bot
- [x] Database connection
- [x] Logging

Phase 2: Photo → Text (Next)
- [ ] Photo handler
- [ ] OCR pipeline (Groq → Gemini → Claude → GPT-4o)
- [ ] Nameplate extraction

Phase 3: Equipment Matching
- [ ] Manufacturer classifier
- [ ] Model number extraction
- [ ] Fuzzy matching

Phase 4: Manual Delivery
- [ ] Manual storage/retrieval
- [ ] PDF delivery via Telegram
- [ ] Web search fallback

See [RIVET_PRO_BUILD_SPEC.md](../RIVET_PRO_BUILD_SPEC.md) for complete roadmap.

## 🎨 Design Principles

1. **No Slash Commands** - Conversational, not CLI-like (only `/start`)
2. **Platform Agnostic** - Core logic independent of Telegram/WhatsApp
3. **LLM-Powered UX** - Adaptive responses based on user vibe
4. **Training Loop** - Every interaction improves the system

## 📝 License

MIT

## 🤝 Contributing

This is an early-stage project. Contributions welcome once Phase 2 is complete.

## 📞 Support

Issues: [GitHub Issues](https://github.com/your-repo/rivet-pro/issues)

---

Built with ❤️ for industrial maintenance technicians
