"""
OCR Data Models

Unified result structure for all OCR providers.
Extracted from rivet/models/ocr.py - Production-ready
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Manufacturer alias mapping (normalize vendor names)
MANUFACTURER_ALIASES = {
    # Rockwell/Allen-Bradley
    "rockwell automation": "allen_bradley",
    "rockwell": "allen_bradley",
    "a-b": "allen_bradley",
    "ab": "allen_bradley",
    "allen-bradley": "allen_bradley",

    # Schneider
    "square d": "schneider_electric",
    "schneider": "schneider_electric",
    "schneider electric": "schneider_electric",

    # Eaton
    "cutler-hammer": "eaton",
    "westinghouse": "eaton",

    # GE
    "ge": "general_electric",
    "ge fanuc": "general_electric",

    # Direct mappings
    "abb": "abb",
    "siemens": "siemens",
    "omron": "omron",
    "mitsubishi": "mitsubishi",
    "yaskawa": "yaskawa",
    "fanuc": "fanuc",
    "delta": "delta",
    "fuji": "fuji_electric",
    "danfoss": "danfoss",
    "sew": "sew_eurodrive",
    "sew-eurodrive": "sew_eurodrive",
    "lenze": "lenze",
    "nord": "nord",
}


def normalize_manufacturer(name: str) -> Optional[str]:
    """Map manufacturer aliases to canonical names."""
    if not name:
        return None
    name_lower = name.lower().strip()
    return MANUFACTURER_ALIASES.get(name_lower, name_lower.replace(" ", "_"))


def normalize_model_number(model: str) -> Optional[str]:
    """Standardize model number format for KB matching."""
    if not model:
        return None
    # Remove hyphens, spaces, uppercase
    normalized = model.replace("-", "").replace(" ", "").upper()
    return normalized if normalized else None


@dataclass
class OCRResult:
    """Unified OCR result from any provider."""

    # Equipment identification
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    fault_code: Optional[str] = None

    # Equipment classification
    equipment_type: Optional[str] = None  # vfd, motor, plc, contactor, relay, sensor, etc.
    equipment_subtype: Optional[str] = None  # servo motor, safety relay, etc.
    condition: Optional[str] = None  # new, good, worn, damaged, burnt, corroded
    visible_issues: List[str] = field(default_factory=list)

    # Electrical specifications
    voltage: Optional[str] = None
    current: Optional[str] = None
    horsepower: Optional[str] = None
    phase: Optional[str] = None
    frequency: Optional[str] = None

    # Additional specs
    additional_specs: Dict[str, Any] = field(default_factory=dict)

    # Raw OCR data
    raw_text: Optional[str] = None

    # Image quality issues detected by OCR
    image_issues: List[str] = field(default_factory=list)  # rotated, upside_down, dirty, blurry, etc.

    # Quality metrics
    confidence: float = 0.0  # 0.0-1.0
    provider: str = "unknown"  # groq, gemini, claude, openai
    model_used: Optional[str] = None  # Specific model name
    processing_time_ms: int = 0
    cost_usd: float = 0.0  # Estimated cost for this call

    # Error handling
    error: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def normalize(self) -> "OCRResult":
        """Normalize manufacturer and model for KB matching. Returns self for chaining."""
        if self.manufacturer:
            self.manufacturer = normalize_manufacturer(self.manufacturer)
        if self.model_number:
            self.model_number = normalize_model_number(self.model_number)
        return self

    @property
    def is_successful(self) -> bool:
        """Check if OCR was successful (no error and reasonable confidence)."""
        return self.error is None and self.confidence >= 0.3

    @property
    def has_equipment_id(self) -> bool:
        """Check if we identified the equipment."""
        return bool(self.manufacturer or self.model_number)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "serial_number": self.serial_number,
            "fault_code": self.fault_code,
            "equipment_type": self.equipment_type,
            "equipment_subtype": self.equipment_subtype,
            "condition": self.condition,
            "visible_issues": self.visible_issues,
            "voltage": self.voltage,
            "current": self.current,
            "horsepower": self.horsepower,
            "phase": self.phase,
            "frequency": self.frequency,
            "additional_specs": self.additional_specs,
            "raw_text": self.raw_text,
            "image_issues": self.image_issues,
            "confidence": self.confidence,
            "provider": self.provider,
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
            "cost_usd": self.cost_usd,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        if self.error:
            return f"OCRResult(error={self.error})"
        return (
            f"OCRResult({self.manufacturer or 'Unknown'} {self.model_number or 'Unknown'}, "
            f"confidence={self.confidence:.0%}, provider={self.provider})"
        )


def calculate_confidence(data: dict, raw_text: str) -> float:
    """
    Calculate OCR confidence based on extracted fields.

    Scoring:
        - Manufacturer: +0.25
        - Model number: +0.30 (critical for KB matching)
        - Serial number: +0.15
        - Electrical specs with units: +0.10
        - Sufficient text (≥20 chars): +0.10
        - Phase validation: +0.05
        - Known manufacturer: +0.05
    """
    confidence = 0.0

    if data.get("manufacturer"):
        confidence += 0.25
        # Bonus for known manufacturer
        if normalize_manufacturer(data["manufacturer"]) in MANUFACTURER_ALIASES.values():
            confidence += 0.05

    if data.get("model_number"):
        confidence += 0.30

    if data.get("serial_number"):
        confidence += 0.15

    # Electrical specs
    voltage = data.get("voltage")
    if voltage and "V" in str(voltage).upper():
        confidence += 0.10

    # Text quantity
    if len(raw_text or "") >= 20:
        confidence += 0.10
    elif len(raw_text or "") < 10:
        confidence *= 0.5  # Penalty for little text

    # Phase validation
    phase = data.get("phase")
    if phase and str(phase) in ["1", "3"]:
        confidence += 0.05

    return min(0.95, confidence)  # Cap at 95%
