"""
Industrial Photo Screening Models

Data models for Groq Vision industrial photo screening service.
Part of PHOTO-GROQ-001 feature.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Literal


# Supported industrial equipment categories
IndustrialCategory = Literal[
    "plc",           # Programmable Logic Controller
    "vfd",           # Variable Frequency Drive
    "motor",         # Electric motor
    "pump",          # Pump
    "control_panel", # Control panel/cabinet
    "sensor",        # Industrial sensor
    "other"          # Other industrial equipment
]


@dataclass
class ScreeningResult:
    """
    Result from industrial photo screening.

    Determines if a photo is industrial equipment before expensive OCR.
    Uses Groq Llama 4 Scout vision model for fast, cheap first-pass.

    Attributes:
        is_industrial: True if photo shows industrial equipment
        confidence: 0.0-1.0 confidence score (>= 0.80 passes)
        category: Equipment category (plc, vfd, motor, pump, control_panel, sensor, other)
        reason: Brief explanation of classification
        processing_time_ms: Time taken for screening
        cost_usd: Estimated API cost (~$0.001 per image)
        model_used: Model that performed screening
        error: Error message if screening failed
    """

    # Core classification
    is_industrial: bool = False
    confidence: float = 0.0
    category: Optional[IndustrialCategory] = None
    reason: str = ""

    # Rejection handling
    rejection_message: Optional[str] = None  # Helpful message for non-industrial

    # Performance metrics
    processing_time_ms: int = 0
    cost_usd: float = 0.0
    model_used: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # Error handling
    error: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def passes_threshold(self) -> bool:
        """Check if confidence passes the 0.80 threshold for OCR."""
        return self.is_industrial and self.confidence >= 0.80

    @property
    def is_successful(self) -> bool:
        """Check if screening completed without error."""
        return self.error is None

    def get_user_message(self) -> str:
        """Get user-friendly message about the screening result."""
        if self.error:
            return f"❌ Screening failed: {self.error}"

        if not self.is_industrial:
            return self.rejection_message or (
                "📷 This doesn't appear to be industrial equipment.\n\n"
                "Please send a photo of:\n"
                "• Equipment nameplates\n"
                "• Control panels\n"
                "• VFDs/drives\n"
                "• Motors or pumps\n"
                "• PLCs or sensors"
            )

        if self.confidence < 0.80:
            return (
                f"⚠️ Low confidence ({self.confidence:.0%}). "
                "Try a clearer photo with better lighting."
            )

        return f"✅ Industrial equipment detected: {self.category or 'equipment'}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_industrial": self.is_industrial,
            "confidence": self.confidence,
            "category": self.category,
            "reason": self.reason,
            "rejection_message": self.rejection_message,
            "processing_time_ms": self.processing_time_ms,
            "cost_usd": self.cost_usd,
            "model_used": self.model_used,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "passes_threshold": self.passes_threshold,
        }

    def __str__(self) -> str:
        if self.error:
            return f"ScreeningResult(error={self.error})"
        status = "PASS" if self.passes_threshold else "REJECT"
        return (
            f"ScreeningResult({status}, industrial={self.is_industrial}, "
            f"confidence={self.confidence:.0%}, category={self.category})"
        )
