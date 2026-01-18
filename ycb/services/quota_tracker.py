"""
Quota Tracker for YCB Media Services

Tracks daily usage per provider to enable intelligent fallback
when quota limits are reached.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProviderQuota:
    """Quota configuration for a provider."""
    daily_limit: int
    unit_name: str = "chars"  # chars, images, requests


# Default quota limits
DEFAULT_QUOTAS: Dict[str, ProviderQuota] = {
    "elevenlabs": ProviderQuota(daily_limit=10000, unit_name="chars"),
    "piper": ProviderQuota(daily_limit=999999999, unit_name="chars"),  # Unlimited
    "edge_tts": ProviderQuota(daily_limit=999999999, unit_name="chars"),  # Unlimited
    "pollinations": ProviderQuota(daily_limit=999999999, unit_name="images"),  # Unlimited
    "stability": ProviderQuota(daily_limit=25, unit_name="images"),  # Free tier
    "placeholder": ProviderQuota(daily_limit=999999999, unit_name="images"),  # Unlimited
}


class QuotaTracker:
    """
    Track daily usage per provider with file-based persistence.

    Usage:
        tracker = QuotaTracker()

        # Check before using provider
        if not tracker.is_quota_exceeded("elevenlabs"):
            # Use elevenlabs
            tracker.add_usage("elevenlabs", len(text))
        else:
            # Fallback to piper
            pass
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize quota tracker.

        Args:
            storage_path: Path to store quota data. Defaults to ~/.ycb/quota.json
        """
        if storage_path is None:
            storage_path = Path.home() / ".ycb" / "quota.json"

        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._usage: Dict[str, Dict[str, int]] = {}
        self._load()

    def _load(self) -> None:
        """Load usage data from file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self._usage = data.get("usage", {})
            except (json.JSONDecodeError, IOError):
                self._usage = {}
        else:
            self._usage = {}

    def _save(self) -> None:
        """Save usage data to file."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump({"usage": self._usage, "updated_at": datetime.now().isoformat()}, f, indent=2)
        except IOError as e:
            print(f"[!] Failed to save quota data: {e}")

    def _today(self) -> str:
        """Get today's date as string key."""
        return date.today().isoformat()

    def get_usage(self, provider: str) -> int:
        """
        Get today's usage for a provider.

        Args:
            provider: Provider name (e.g., "elevenlabs", "piper")

        Returns:
            Current usage count for today
        """
        today = self._today()
        if today not in self._usage:
            return 0
        return self._usage[today].get(provider, 0)

    def get_limit(self, provider: str) -> int:
        """
        Get quota limit for a provider.

        Args:
            provider: Provider name

        Returns:
            Daily limit for the provider
        """
        quota = DEFAULT_QUOTAS.get(provider)
        if quota:
            return quota.daily_limit
        return 999999999  # Unknown provider = unlimited

    def add_usage(self, provider: str, units: int) -> int:
        """
        Add usage for a provider.

        Args:
            provider: Provider name
            units: Number of units used (chars, images, etc.)

        Returns:
            New total usage for today
        """
        today = self._today()
        if today not in self._usage:
            self._usage[today] = {}

        current = self._usage[today].get(provider, 0)
        self._usage[today][provider] = current + units

        self._save()
        self._cleanup_old_data()

        return self._usage[today][provider]

    def is_quota_exceeded(self, provider: str) -> bool:
        """
        Check if provider has exceeded daily quota.

        Args:
            provider: Provider name

        Returns:
            True if quota exceeded, False otherwise
        """
        usage = self.get_usage(provider)
        limit = self.get_limit(provider)
        return usage >= limit

    def get_remaining(self, provider: str) -> int:
        """
        Get remaining quota for a provider.

        Args:
            provider: Provider name

        Returns:
            Remaining units available today
        """
        limit = self.get_limit(provider)
        usage = self.get_usage(provider)
        return max(0, limit - usage)

    def get_all_usage(self) -> Dict[str, Dict[str, int]]:
        """
        Get usage summary for all providers today.

        Returns:
            Dict with provider -> {usage, limit, remaining, exceeded}
        """
        today = self._today()
        result = {}

        for provider in DEFAULT_QUOTAS:
            usage = self.get_usage(provider)
            limit = self.get_limit(provider)
            result[provider] = {
                "usage": usage,
                "limit": limit,
                "remaining": max(0, limit - usage),
                "exceeded": usage >= limit,
                "unit": DEFAULT_QUOTAS[provider].unit_name
            }

        return result

    def _cleanup_old_data(self) -> None:
        """Remove usage data older than 7 days."""
        today = date.today()
        keys_to_remove = []

        for date_str in self._usage:
            try:
                data_date = date.fromisoformat(date_str)
                if (today - data_date).days > 7:
                    keys_to_remove.append(date_str)
            except ValueError:
                keys_to_remove.append(date_str)

        for key in keys_to_remove:
            del self._usage[key]

        if keys_to_remove:
            self._save()

    def reset_provider(self, provider: str) -> None:
        """
        Reset usage for a specific provider (for testing).

        Args:
            provider: Provider name to reset
        """
        today = self._today()
        if today in self._usage and provider in self._usage[today]:
            del self._usage[today][provider]
            self._save()

    def __str__(self) -> str:
        """Return human-readable usage summary."""
        lines = ["YCB Quota Status:"]
        for provider, stats in self.get_all_usage().items():
            status = "EXCEEDED" if stats["exceeded"] else "OK"
            lines.append(
                f"  {provider}: {stats['usage']}/{stats['limit']} {stats['unit']} [{status}]"
            )
        return "\n".join(lines)


# Global instance for convenience
_tracker: Optional[QuotaTracker] = None


def get_tracker() -> QuotaTracker:
    """Get or create global quota tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = QuotaTracker()
    return _tracker
