"""
Component Extraction Models

Data models for DeepSeek component specification extraction.
Part of PHOTO-DEEP-001 feature.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ExtractionResult:
    """
    Result from DeepSeek component specification extraction.

    Contains detailed manufacturer, model, serial, and spec data
    extracted from industrial equipment photos.

    Attributes:
        manufacturer: Equipment manufacturer name
        model_number: Exact model number as shown on nameplate
        serial_number: Serial number if visible
        specs: Dictionary of extracted specifications (voltage, hp, rpm, etc.)
        raw_text: All visible text extracted from image
        confidence: 0.0-1.0 extraction confidence
        processing_time_ms: Time taken for extraction
        cost_usd: Estimated API cost (~$0.002 per image)
        model_used: Model that performed extraction
        from_cache: True if result came from cache
        error: Error message if extraction failed
    """

    # Core extraction results
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    specs: Dict[str, Any] = field(default_factory=dict)
    raw_text: Optional[str] = None

    # Quality metrics
    confidence: float = 0.0

    # Performance metrics
    processing_time_ms: int = 0
    cost_usd: float = 0.0
    model_used: str = "deepseek-chat"

    # Cache indicator
    from_cache: bool = False

    # Error handling
    error: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_successful(self) -> bool:
        """Check if extraction completed without error."""
        return self.error is None and self.confidence > 0.0

    @property
    def has_model_info(self) -> bool:
        """Check if we have manufacturer or model number."""
        return bool(self.manufacturer or self.model_number)

    def get_user_message(self) -> str:
        """Get user-friendly message about the extraction result."""
        if self.error:
            return f"Extraction failed: {self.error}"

        if not self.has_model_info:
            return (
                "Could not extract equipment details.\n"
                "Please try a clearer photo with better lighting."
            )

        parts = []
        if self.manufacturer:
            parts.append(f"Manufacturer: {self.manufacturer}")
        if self.model_number:
            parts.append(f"Model: {self.model_number}")
        if self.serial_number:
            parts.append(f"Serial: {self.serial_number}")

        # Add key specs
        for key in ["voltage", "current", "horsepower", "rpm", "phase"]:
            if key in self.specs and self.specs[key]:
                parts.append(f"{key.title()}: {self.specs[key]}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "serial_number": self.serial_number,
            "specs": self.specs,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "cost_usd": self.cost_usd,
            "model_used": self.model_used,
            "from_cache": self.from_cache,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        if self.error:
            return f"ExtractionResult(error={self.error})"
        cache_tag = " [CACHED]" if self.from_cache else ""
        return (
            f"ExtractionResult({self.manufacturer or 'Unknown'} "
            f"{self.model_number or 'Unknown'}, "
            f"confidence={self.confidence:.0%}{cache_tag})"
        )
