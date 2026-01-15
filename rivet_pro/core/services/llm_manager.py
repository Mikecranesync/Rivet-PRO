"""
MultiProviderLLMManager - LLM provider failover with caching.

Provider order: Claude (primary) -> GPT-4 (fallback) -> Cache (last resort)
Tracks costs per provider and logs which provider was used.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers"""

    def __init__(self, name: str):
        self.name = name

    def generate(self, prompt: str, max_tokens: int = 1000) -> Tuple[str, Dict[str, Any]]:
        raise NotImplementedError


class ClaudeProvider(LLMProvider):
    """Claude API provider (Anthropic)"""

    def __init__(self):
        super().__init__("claude")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1000) -> Tuple[str, Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("Claude API key not configured")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": self.model
        }

        return text, usage


class GPT4Provider(LLMProvider):
    """GPT-4 API provider (OpenAI)"""

    def __init__(self):
        super().__init__("gpt4")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("GPT4_MODEL", "gpt-4-turbo-preview")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1000) -> Tuple[str, Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "model": self.model
        }

        return text, usage


class CacheProvider(LLMProvider):
    """Cache provider using database storage"""

    def __init__(self, database_url: Optional[str] = None):
        super().__init__("cache")
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.cache_ttl_hours = int(os.getenv("LLM_CACHE_TTL_HOURS", "24"))

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt hash"""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Get cached response if available and not expired"""
        import psycopg2

        if not self.database_url:
            return None

        cache_key = self._get_cache_key(prompt)
        cutoff = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours)

        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT response, metadata FROM llm_cache
                    WHERE cache_key = %s AND created_at > %s
                    ORDER BY created_at DESC LIMIT 1
                """, (cache_key, cutoff))
                row = cur.fetchone()
                conn.close()

                if row:
                    return row[0], row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        return None

    def set(self, prompt: str, response: str, metadata: Dict[str, Any]) -> bool:
        """Store response in cache"""
        import psycopg2

        if not self.database_url:
            return False

        cache_key = self._get_cache_key(prompt)

        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO llm_cache (cache_key, prompt_hash, response, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (cache_key) DO UPDATE SET
                        response = EXCLUDED.response,
                        metadata = EXCLUDED.metadata,
                        created_at = NOW()
                """, (
                    cache_key,
                    cache_key[:64],  # Truncate for index
                    response,
                    json.dumps(metadata)
                ))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.warning(f"Cache store failed: {e}")
            return False

    def generate(self, prompt: str, max_tokens: int = 1000) -> Tuple[str, Dict[str, Any]]:
        """Get from cache or raise error"""
        result = self.get(prompt)
        if result:
            return result
        raise RuntimeError("No cached response available")


class MultiProviderLLMManager:
    """
    LLM manager with automatic failover.

    Provider order: Claude -> GPT-4 -> Cache

    Usage:
        manager = MultiProviderLLMManager()
        response, metadata = manager.generate("What is 2+2?", max_tokens=100)
        print(f"Response: {response}")
        print(f"Provider used: {metadata['provider']}")
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

        # Initialize providers in order of preference
        self.providers = [
            ClaudeProvider(),
            GPT4Provider(),
            CacheProvider(self.database_url),
        ]

        # Cost tracking (rough estimates per 1K tokens)
        self.cost_per_1k_tokens = {
            "claude": {"input": 0.003, "output": 0.015},
            "gpt4": {"input": 0.01, "output": 0.03},
            "cache": {"input": 0, "output": 0},
        }

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        skip_cache_check: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate response using available providers with failover.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response
            skip_cache_check: If True, don't check cache first

        Returns:
            Tuple of (response_text, metadata_dict)
            metadata includes: provider, usage, estimated_cost, timestamp
        """
        cache_provider = self.providers[-1]  # CacheProvider is last

        # Check cache first (unless skipped)
        if not skip_cache_check:
            cached = cache_provider.get(prompt)
            if cached:
                response, cache_meta = cached
                logger.info("LLM response served from cache")
                return response, {
                    "provider": "cache",
                    "usage": cache_meta.get("usage", {}),
                    "estimated_cost": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "cached": True,
                    "original_provider": cache_meta.get("provider")
                }

        # Try each provider in order (except cache)
        errors = []
        for provider in self.providers[:-1]:  # Skip cache provider
            if not hasattr(provider, 'is_available') or not provider.is_available():
                continue

            try:
                logger.info(f"Trying LLM provider: {provider.name}")
                response, usage = provider.generate(prompt, max_tokens)

                # Calculate estimated cost
                cost = self._estimate_cost(provider.name, usage)

                # Log cost warning for expensive providers
                if provider.name == "gpt4" and cost > 0.01:
                    logger.warning(f"GPT-4 fallback used - estimated cost: ${cost:.4f}")

                metadata = {
                    "provider": provider.name,
                    "usage": usage,
                    "estimated_cost": cost,
                    "timestamp": datetime.utcnow().isoformat(),
                    "cached": False
                }

                # Cache the response for future use
                cache_provider.set(prompt, response, metadata)

                return response, metadata

            except Exception as e:
                errors.append(f"{provider.name}: {str(e)}")
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        # All providers failed - try cache as last resort
        cached = cache_provider.get(prompt)
        if cached:
            response, cache_meta = cached
            logger.warning("All LLM providers failed, serving stale cache")
            return response, {
                "provider": "cache",
                "usage": {},
                "estimated_cost": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "cached": True,
                "stale": True,
                "original_provider": cache_meta.get("provider")
            }

        # Complete failure
        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")

    def _estimate_cost(self, provider_name: str, usage: Dict[str, Any]) -> float:
        """Estimate cost based on token usage"""
        rates = self.cost_per_1k_tokens.get(provider_name, {"input": 0, "output": 0})
        input_cost = (usage.get("input_tokens", 0) / 1000) * rates["input"]
        output_cost = (usage.get("output_tokens", 0) / 1000) * rates["output"]
        return input_cost + output_cost


# Create llm_cache table if it doesn't exist
def ensure_cache_table():
    """Ensure the llm_cache table exists"""
    import psycopg2

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    id SERIAL PRIMARY KEY,
                    cache_key VARCHAR(64) UNIQUE NOT NULL,
                    prompt_hash VARCHAR(64) NOT NULL,
                    response TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_cache(cache_key);
                CREATE INDEX IF NOT EXISTS idx_llm_cache_created ON llm_cache(created_at DESC);
            """)
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to create llm_cache table: {e}")
        return False


# Convenience function
def get_llm_manager() -> MultiProviderLLMManager:
    """Get a MultiProviderLLMManager instance"""
    return MultiProviderLLMManager()
