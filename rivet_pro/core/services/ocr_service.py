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

# Equipment extraction prompt (unified across providers) - OPTIMIZED FOR SPEED
EXTRACTION_PROMPT = """Extract equipment info from this photo. Return ONLY JSON (no markdown):
{
  "manufacturer": "name or null",
  "model_number": "exact as shown or null",
  "serial_number": "exact or null",
  "fault_code": "error code or null",
  "equipment_type": "vfd|motor|plc|drive|pump|contactor|relay|breaker|sensor|other|null",
  "condition": "new|good|worn|damaged|burnt|unknown",
  "visible_issues": ["specific problems"],
  "voltage": "with unit or null",
  "current": "with unit or null",
  "horsepower": "or null",
  "phase": "1|3|null",
  "frequency": "or null",
  "additional_specs": {"rpm":"","frame":"","ip_rating":""},
  "raw_text": "ALL visible text exactly",
  "confidence": 0.0-1.0,
  "image_issues": ["rotated|upside_down|dirty|damaged|blurry|glare|partial"]
}
RULES:
- IMPORTANT: If image is rotated or upside-down, mentally rotate it before reading text
- Preserve exact model numbers. Include units. Use null not empty string
- Confidence 0.9+ only if manufacturer+model absolutely clear
- Lower confidence to 0.7 or below if image is dirty, rotated, or partially visible
- Add any image quality issues to "image_issues" array"""


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

            # Reduce confidence if image quality issues detected
            image_issues = data.get("image_issues", [])
            if image_issues:
                # Major issues: upside_down, rotated require correction
                major_issues = {'upside_down', 'rotated', 'partial'}
                # Minor issues: dirt, glare can still be read
                if major_issues & set(image_issues):
                    confidence = min(confidence, 0.65)  # Force cascade to verify
                    logger.info(f"{user_log} Major image issues detected: {image_issues} - capping confidence at 65%")
                else:
                    confidence = min(confidence, 0.80)
                    logger.info(f"{user_log} Minor image issues detected: {image_issues} - capping confidence at 80%")

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
                image_issues=data.get("image_issues", []),
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
            error_str = str(e)
            error_type = type(e).__name__

            # Skip immediately on permission denied (403) - don't waste time retrying
            if "403" in error_str or "PERMISSION_DENIED" in error_str or "permission denied" in error_str.lower():
                logger.warning(
                    f"{user_log} {provider_config.name} PERMISSION DENIED - skipping immediately (no retry)",
                    extra={
                        "user_id": user_id,
                        "provider": provider_config.name,
                        "error_type": "permission_denied",
                        "skip_reason": "API key blocked/leaked"
                    }
                )
                continue

            logger.warning(
                f"{user_log} {provider_config.name} failed: {error_type}: {e}",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "provider": provider_config.name,
                    "error_type": error_type
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
