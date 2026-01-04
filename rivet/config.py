"""
RIVET Pro Configuration

All settings loaded from environment with validation.
Tier limits and API keys centralized here.
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from functools import lru_cache


class TierLimits:
    """Usage limits per subscription tier."""

    BETA = {
        "name": "beta",
        "price": 0,
        "queries_per_day": 50,
        "trial_days": 7,
        "prints_per_month": 5,
        "max_image_size_mb": 5,
        "priority": "low",
    }

    PRO = {
        "name": "pro",
        "price": 29,
        "queries_per_day": 1000,
        "trial_days": None,  # No trial, paid
        "prints_per_month": -1,  # Unlimited
        "max_image_size_mb": 20,
        "priority": "normal",
    }

    TEAM = {
        "name": "team",
        "price": 200,
        "queries_per_day": -1,  # Unlimited
        "trial_days": None,
        "prints_per_month": -1,
        "max_image_size_mb": 50,
        "max_users": 10,
        "priority": "high",
        "features": ["shared_library", "admin_dashboard", "api_access"],
    }

    @classmethod
    def get(cls, tier_name: str) -> Dict[str, Any]:
        """Get limits for a tier by name."""
        tiers = {
            "beta": cls.BETA,
            "pro": cls.PRO,
            "team": cls.TEAM,
        }
        return tiers.get(tier_name.lower(), cls.BETA)


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # App
    app_name: str = "RIVET Pro"
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")

    # API Keys - OCR Providers (in cost order)
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # Database (HARVEST 7 - Multi-provider with failover)
    database_url: str = Field(default="", env="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    database_provider: str = Field(default="neon", env="DATABASE_PROVIDER")
    database_failover_enabled: bool = Field(default=True, env="DATABASE_FAILOVER_ENABLED")
    database_failover_order: str = Field(default="neon,vps,supabase", env="DATABASE_FAILOVER_ORDER")

    # Neon
    neon_db_url: Optional[str] = Field(default=None, env="NEON_DB_URL")

    # Supabase (direct PostgreSQL access)
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY")
    supabase_db_host: Optional[str] = Field(default=None, env="SUPABASE_DB_HOST")
    supabase_db_password: Optional[str] = Field(default=None, env="SUPABASE_DB_PASSWORD")

    # VPS KB
    vps_kb_host: Optional[str] = Field(default=None, env="VPS_KB_HOST")
    vps_kb_port: int = Field(default=5432, env="VPS_KB_PORT")
    vps_kb_user: Optional[str] = Field(default=None, env="VPS_KB_USER")
    vps_kb_password: Optional[str] = Field(default=None, env="VPS_KB_PASSWORD")
    vps_kb_database: str = Field(default="rivet", env="VPS_KB_DATABASE")

    # Telegram - Multiple bots
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")  # RIVET Local Dev
    orchestrator_bot_token: str = Field(default="", env="ORCHESTRATOR_BOT_TOKEN")  # Rivet (Main)
    public_telegram_bot_token: str = Field(default="", env="PUBLIC_TELEGRAM_BOT_TOKEN")  # Rivet CMMS
    telegram_admin_ids: str = Field(default="", env="TELEGRAM_ADMIN_IDS")

    # Stripe
    stripe_secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    stripe_price_pro: Optional[str] = Field(default=None, env="STRIPE_PRICE_PRO")
    stripe_price_team: Optional[str] = Field(default=None, env="STRIPE_PRICE_TEAM")

    # Observability
    langsmith_api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="rivet-pro", env="LANGSMITH_PROJECT")
    phoenix_endpoint: Optional[str] = Field(default=None, env="PHOENIX_ENDPOINT")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")

    # OCR Settings
    ocr_confidence_threshold: float = Field(default=0.7, env="OCR_CONFIDENCE_THRESHOLD")
    ocr_max_retries: int = Field(default=3, env="OCR_MAX_RETRIES")

    # Memory Storage (HARVEST 8)
    memory_backend: str = Field(default="postgres", env="MEMORY_BACKEND")
    memory_sqlite_path: str = Field(default="./data/memory.db", env="MEMORY_SQLITE_PATH")

    # Trace Logger (HARVEST 10)
    trace_log_dir: str = Field(default="./logs/traces", env="TRACE_LOG_DIR")
    trace_log_enabled: bool = Field(default=True, env="TRACE_LOG_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = 'ignore'  # Allow extra fields in .env that aren't defined in Settings

    @property
    def admin_ids(self) -> list[int]:
        """Parse admin IDs from comma-separated string."""
        if not self.telegram_admin_ids:
            return []
        return [int(id.strip()) for id in self.telegram_admin_ids.split(",") if id.strip()]

    def get_available_ocr_providers(self) -> list[str]:
        """Return list of configured OCR providers in cost order."""
        providers = []
        if self.groq_api_key:
            providers.append("groq")
        if self.gemini_api_key:
            providers.append("gemini")
        if self.anthropic_api_key:
            providers.append("claude")
        if self.openai_api_key:
            providers.append("openai")
        return providers

    def log_status(self):
        """Print configuration status for debugging."""
        print(f"\n{'='*50}")
        print(f"RIVET Pro Configuration Status")
        print(f"{'='*50}")
        print(f"Environment: {self.app_env}")
        print(f"Debug: {self.debug}")
        print(f"\nOCR Providers Available:")
        for p in self.get_available_ocr_providers():
            print(f"  ✓ {p}")
        if not self.get_available_ocr_providers():
            print("  ✗ No providers configured!")
        print(f"\nDatabase: {'✓' if self.database_url else '✗'}")
        print(f"Telegram: {'✓' if self.telegram_bot_token else '✗'}")
        print(f"Stripe: {'✓' if self.stripe_secret_key else '✗'}")
        print(f"LangSmith: {'✓' if self.langsmith_api_key else '✗'}")
        print(f"{'='*50}\n")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias
config = get_settings()
