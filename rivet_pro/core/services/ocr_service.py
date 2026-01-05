"""
OCR Workflow - Multi-Provider Cost-Optimized Pipeline

Analyzes industrial equipment photos using multiple vision providers.
Tries cheapest providers first, escalates if confidence is low.

Extracted from rivet/workflows/ocr.py - Production-ready
"""

import io
import re
import json
import logging
from typing import Optional, Tuple
from datetime import datetime

from rivet_pro.config.settings import settings
from rivet_pro.core.models.ocr import OCRResult, calculate_confidence
from rivet_pro.adapters.llm import (
    get_llm_router,
    VISION_PROVIDER_CHAIN,
    ProviderConfig,
)
from rivet_pro.core.services.equipment_taxonomy import (
    identify_component,
    extract_fault_code,
    extract_model_number,
)

logger = logging.getLogger(__name__)

# Equipment extraction prompt (unified across providers)
EXTRACTION_PROMPT = """You are an industrial maintenance expert analyzing equipment photos.

Extract ALL relevant information from this industrial equipment nameplate/label.

RESPOND IN THIS EXACT JSON FORMAT (no markdown, no code fences):
{
  "manufacturer": "company name or null",
  "model_number": "exact model/catalog number or null",
  "serial_number": "exact serial number or null",
  "fault_code": "error code if visible on display or null",

  "equipment_type": "vfd | motor | contactor | pump | plc | relay | breaker | sensor | valve | compressor | robot | conveyor | transformer | hmi | drive | starter | other | null",
  "equipment_subtype": "more specific type if identifiable or null",

  "condition": "new | good | worn | damaged | burnt | corroded | unknown",
  "visible_issues": ["specific observable problems like 'burnt terminal on T1'"],

  "voltage": "voltage rating with unit (e.g., '480V', '208-230/460V') or null",
  "current": "current rating with unit (e.g., '15A') or null",
  "horsepower": "HP rating (e.g., '5HP') or null",
  "phase": "phase ('1' or '3') or null",
  "frequency": "frequency (e.g., '60Hz') or null",

  "additional_specs": {
    "rpm": "speed if visible",
    "frame": "frame size if visible",
    "ip_rating": "IP rating if visible",
    "enclosure": "enclosure type if visible"
  },

  "raw_text": "ALL visible text transcribed exactly as shown",
  "confidence": 0.0 to 1.0
}

CRITICAL RULES:
- Extract model numbers EXACTLY as shown (preserve hyphens, spaces)
- Include units with all electrical values (V, A, HP, Hz)
- For VFDs/drives: prioritize voltage, HP, and phase
- Describe visible damage specifically (which terminal, wire, component)
- If unsure, use null (not empty string)
- Confidence 0.9+ only if manufacturer AND model clearly visible
"""


def validate_image_quality(
    image_bytes: bytes,
    min_width: int = 400,
    min_height: int = 400,
    max_dark_ratio: float = 0.90,      # Relaxed from 0.80
    max_bright_ratio: float = 0.90,    # Relaxed from 0.80
) -> Tuple[bool, str]:
    """
    Check if image is suitable for OCR.

    Thresholds are lenient because:
    - Real equipment photos often have reflective nameplates (highlights)
    - Shop floor lighting varies (shadows, bright spots)
    - OCR providers are robust to imperfect lighting
    - False rejection costs more than false acceptance

    Args:
        image_bytes: Image data
        min_width: Minimum width in pixels
        min_height: Minimum height in pixels
        max_dark_ratio: Maximum ratio of very dark pixels (0.0-1.0)
        max_bright_ratio: Maximum ratio of very bright pixels (0.0-1.0)

    Returns:
        (is_valid, message) tuple
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        logger.debug(f"Image validation: size={img.width}x{img.height}, mode={img.mode}")

        # Min resolution check
        if img.width < min_width or img.height < min_height:
            return False, (
                f"Image too small ({img.width}x{img.height}). "
                f"Minimum {min_width}x{min_height} required."
            )

        # Max resolution warning only
        if img.width > 4096 or img.height > 4096:
            logger.warning(f"Large image ({img.width}x{img.height}), may be slower")

        # Brightness check
        gray = img.convert("L")
        histogram = gray.histogram()
        total_pixels = sum(histogram)

        dark_pixels = sum(histogram[:77])
        dark_ratio = dark_pixels / total_pixels

        if dark_ratio > max_dark_ratio:
            return False, (
                f"Image too dark ({dark_ratio:.0%} dark pixels). "
                f"Please use better lighting."
            )

        bright_pixels = sum(histogram[178:])
        bright_ratio = bright_pixels / total_pixels

        if bright_ratio > max_bright_ratio:
            return False, (
                f"Image overexposed ({bright_ratio:.0%} bright pixels). "
                f"Reduce lighting or avoid direct flash."
            )

        logger.debug(f"Validation passed: dark={dark_ratio:.1%}, bright={bright_ratio:.1%}")
        return True, "OK"

    except Exception as e:
        logger.warning(f"Validation error: {e}. Allowing image through.")
        return True, "Validation skipped due to error"


def parse_json_response(text: str) -> dict:
    """
    Parse JSON from LLM response, handling common issues.
    """
    # Remove markdown code fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        data = json.loads(text)

        # Clean string fields
        str_fields = [
            "manufacturer", "model_number", "serial_number", "fault_code",
            "equipment_type", "equipment_subtype", "condition",
            "voltage", "current", "horsepower", "phase", "frequency", "raw_text"
        ]
        for key in str_fields:
            if key in data and isinstance(data[key], str):
                cleaned = data[key].strip()
                data[key] = cleaned if cleaned else None

        # Ensure lists/dicts
        if not isinstance(data.get("visible_issues"), list):
            data["visible_issues"] = []
        if not isinstance(data.get("additional_specs"), dict):
            data["additional_specs"] = {}

        return data

    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON: {text[:200]}")
        return {
            "raw_text": text[:500],
            "confidence": 0.0,
        }


async def analyze_image(
    image_bytes: bytes,
    user_id: Optional[str] = None,
    skip_quality_check: bool = False,
    min_confidence: float = 0.7,
) -> OCRResult:
    """
    Analyze equipment photo with cost-optimized provider chain.

    Tries providers in cost order until one succeeds with confidence >= min_confidence.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG)
        user_id: User ID for logging
        skip_quality_check: Skip image validation
        min_confidence: Minimum confidence to accept result (default 0.7)

    Returns:
        OCRResult with best extraction
    """
    router = get_llm_router()

    user_log = f"[{user_id}]" if user_id else "[OCR]"
    start_time = datetime.utcnow()

    # Step 1: Quality check
    if not skip_quality_check:
        logger.info(f"{user_log} Running image quality validation...")
        is_valid, quality_msg = validate_image_quality(image_bytes)
        logger.info(f"{user_log} Quality check result: valid={is_valid}, msg={quality_msg}")

        if not is_valid:
            logger.warning(
                f"{user_log} Image rejected by quality check: {quality_msg}",
                extra={"user_id": user_id, "rejection_reason": quality_msg}
            )
            return OCRResult(
                error=quality_msg,
                provider="quality_check",
                confidence=0.0,
            )
        else:
            logger.info(f"{user_log} Quality check passed")

    # Step 2: Try providers in cost order
    available_providers = router.get_available_providers()
    best_result: Optional[OCRResult] = None
    total_cost = 0.0
    providers_tried = []

    logger.info(
        f"{user_log} Starting provider chain. Available: {available_providers}. "
        f"Min confidence required: {min_confidence:.0%}"
    )

    for provider_config in VISION_PROVIDER_CHAIN:
        # Skip unavailable providers
        if provider_config.name not in available_providers:
            logger.debug(f"{user_log} Skipping unavailable: {provider_config.name}")
            continue

        # Skip if we already tried this provider (e.g., multiple gemini models)
        provider_model_key = f"{provider_config.name}:{provider_config.model}"

        logger.info(
            f"{user_log} Trying {provider_config.name}/{provider_config.model}"
        )
        providers_tried.append(provider_model_key)

        try:
            response_text, cost = await router.call_vision(
                provider_config,
                image_bytes,
                EXTRACTION_PROMPT,
            )
            total_cost += cost

            # Parse response
            data = parse_json_response(response_text)

            # Enhance with equipment taxonomy (fallback for missing data)
            if data.get("raw_text"):
                component = identify_component(data["raw_text"])

                # Use taxonomy as fallback if LLM missed something
                if component["manufacturer"] and not data.get("manufacturer"):
                    data["manufacturer"] = component["manufacturer"]
                    logger.info(f"{user_log} Taxonomy filled manufacturer: {component['manufacturer']}")

                if component["family"] and not data.get("equipment_type"):
                    data["equipment_type"] = component["family_key"]
                    logger.info(f"{user_log} Taxonomy filled equipment_type: {component['family_key']}")

                if not data.get("fault_code"):
                    fault = extract_fault_code(data["raw_text"])
                    if fault:
                        data["fault_code"] = fault
                        logger.info(f"{user_log} Taxonomy extracted fault_code: {fault}")

                if not data.get("model_number"):
                    model = extract_model_number(data["raw_text"])
                    if model:
                        data["model_number"] = model
                        logger.info(f"{user_log} Taxonomy extracted model_number: {model}")

            # Calculate confidence if not provided
            llm_confidence = data.get("confidence", 0.0)
            calculated_confidence = calculate_confidence(data, data.get("raw_text", ""))
            confidence = max(llm_confidence, calculated_confidence)

            # Build result
            result = OCRResult(
                manufacturer=data.get("manufacturer"),
                model_number=data.get("model_number"),
                serial_number=data.get("serial_number"),
                fault_code=data.get("fault_code"),
                equipment_type=data.get("equipment_type"),
                equipment_subtype=data.get("equipment_subtype"),
                condition=data.get("condition", "unknown"),
                visible_issues=data.get("visible_issues", []),
                voltage=data.get("voltage"),
                current=data.get("current"),
                horsepower=data.get("horsepower"),
                phase=data.get("phase"),
                frequency=data.get("frequency"),
                additional_specs=data.get("additional_specs", {}),
                raw_text=data.get("raw_text"),
                confidence=confidence,
                provider=provider_config.name,
                model_used=provider_config.model,
                cost_usd=cost,
            )

            logger.info(
                f"{user_log} {provider_config.name} result: "
                f"{result.manufacturer} {result.model_number} "
                f"(confidence={confidence:.0%})"
            )

            # Check if good enough
            if confidence >= min_confidence:
                result.processing_time_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                result.cost_usd = total_cost
                logger.info(
                    f"{user_log} ✓ Accepted result from {provider_config.name}. "
                    f"Confidence: {confidence:.0%} >= {min_confidence:.0%}. "
                    f"Extracted: {result.manufacturer} {result.model_number}. "
                    f"Total cost: ${total_cost:.4f}"
                )
                return result.normalize()

            # Keep best result so far
            if best_result is None or confidence > best_result.confidence:
                best_result = result

        except Exception as e:
            logger.warning(
                f"{user_log} {provider_config.name} failed: {type(e).__name__}: {e}",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "provider": provider_config.name,
                    "error_type": type(e).__name__
                }
            )
            continue

    # Step 3: Return best result (even if below threshold)
    processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if best_result:
        best_result.processing_time_ms = processing_time
        best_result.cost_usd = total_cost
        logger.info(
            f"{user_log} Returning best result: {best_result.provider} "
            f"(confidence={best_result.confidence:.0%})"
        )
        return best_result.normalize()

    # All providers failed
    logger.error(f"{user_log} All OCR providers failed. Tried: {providers_tried}")
    return OCRResult(
        error=f"All OCR providers failed. Tried: {', '.join(providers_tried)}",
        provider="all_failed",
        confidence=0.0,
        processing_time_ms=processing_time,
        cost_usd=total_cost,
    )


# Convenience sync wrapper
def analyze_image_sync(
    image_bytes: bytes,
    user_id: Optional[str] = None,
    **kwargs
) -> OCRResult:
    """Synchronous wrapper for analyze_image."""
    import asyncio
    return asyncio.run(analyze_image(image_bytes, user_id, **kwargs))
