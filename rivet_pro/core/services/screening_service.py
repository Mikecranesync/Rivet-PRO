"""
Industrial Photo Screening Service

Groq-based first-pass screening to determine if photo is industrial equipment.
Part of PHOTO-GROQ-001 feature.

Uses Groq Llama 4 Scout vision model for fast, cheap screening:
- Response time target: < 2 seconds
- Cost: ~$0.001 per image
- Confidence threshold: >= 0.80 passes to OCR stage
"""

import base64
import json
import logging
import time
from typing import Optional

from rivet_pro.core.models.screening import ScreeningResult, IndustrialCategory
from rivet_pro.config.settings import settings

logger = logging.getLogger(__name__)

# Screening model - cheap and fast for first-pass
# Note: llava-v1.5-7b-4096-preview was decommissioned - using Llama 4 Scout
SCREENING_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
SCREENING_COST_PER_IMAGE = 0.001  # ~$0.001 per screening

# Confidence threshold for passing to OCR
CONFIDENCE_THRESHOLD = 0.80

# Screening prompt - concise for speed
SCREENING_PROMPT = """Analyze this image. Is it industrial/manufacturing equipment?

Respond ONLY with JSON:
{
  "is_industrial": true/false,
  "confidence": 0.0-1.0,
  "category": "plc" | "vfd" | "motor" | "pump" | "control_panel" | "sensor" | "other" | null,
  "reason": "brief explanation"
}

Industrial equipment includes:
- Nameplates/data plates on equipment
- PLCs, VFDs, drives, motors, pumps
- Control panels, switchgear, breakers
- Sensors, relays, contactors
- Manufacturing machinery

NOT industrial:
- Food, pets, people, selfies
- Consumer electronics
- Vehicles (unless industrial)
- Documents without equipment context"""


async def screen_industrial_photo(base64_image: str) -> ScreeningResult:
    """
    Screen photo to determine if it shows industrial equipment.

    Uses Groq Llama 4 Scout vision model for fast, cheap first-pass screening.
    Photos passing threshold (>= 0.80 confidence) proceed to expensive OCR.

    Args:
        base64_image: Base64-encoded image data (no data: prefix)

    Returns:
        ScreeningResult with classification, confidence, and category

    Example:
        >>> with open("nameplate.jpg", "rb") as f:
        ...     image_b64 = base64.b64encode(f.read()).decode()
        >>> result = await screen_industrial_photo(image_b64)
        >>> if result.passes_threshold:
        ...     # Proceed to OCR
        ...     ocr_result = await analyze_image(image_bytes)
    """
    start_time = time.time()

    # Validate we have Groq API key
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not configured")
        return ScreeningResult(
            error="Screening service not configured (missing GROQ_API_KEY)",
            processing_time_ms=0
        )

    try:
        # Initialize Groq client
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)

        # Call Groq Vision API
        response = client.chat.completions.create(
            model=SCREENING_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": SCREENING_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            max_tokens=200,  # Keep response short for speed
            temperature=0.1,  # Low temp for consistent classification
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Parse response
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"Screening response: {response_text}")

        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        data = json.loads(json_text)

        is_industrial = data.get("is_industrial", False)
        confidence = float(data.get("confidence", 0.0))
        category = data.get("category")
        reason = data.get("reason", "")

        # Validate category
        valid_categories = {"plc", "vfd", "motor", "pump", "control_panel", "sensor", "other"}
        if category and category.lower() not in valid_categories:
            category = "other"
        elif category:
            category = category.lower()

        # Build rejection message for non-industrial
        rejection_message = None
        if not is_industrial:
            rejection_message = _get_rejection_message(reason)

        # Log to Langfuse for cost tracking
        _log_to_langfuse(
            model=SCREENING_MODEL,
            is_industrial=is_industrial,
            confidence=confidence,
            category=category,
            processing_time_ms=processing_time_ms
        )

        result = ScreeningResult(
            is_industrial=is_industrial,
            confidence=confidence,
            category=category,
            reason=reason,
            rejection_message=rejection_message,
            processing_time_ms=processing_time_ms,
            cost_usd=SCREENING_COST_PER_IMAGE,
            model_used=SCREENING_MODEL
        )

        logger.info(
            f"Photo screening | industrial={is_industrial} | "
            f"confidence={confidence:.0%} | category={category} | "
            f"time={processing_time_ms}ms | passes={result.passes_threshold}"
        )

        return result

    except json.JSONDecodeError as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"Screening JSON parse error: {e} | response: {response_text[:200]}")

        # Fallback: assume not industrial if we can't parse
        return ScreeningResult(
            is_industrial=False,
            confidence=0.0,
            reason="Could not parse response",
            rejection_message=(
                "📷 Couldn't analyze this image.\n\n"
                "Please send a clear photo of industrial equipment like:\n"
                "• Equipment nameplates\n"
                "• Control panels or VFDs\n"
                "• Motors or pumps"
            ),
            processing_time_ms=processing_time_ms,
            cost_usd=SCREENING_COST_PER_IMAGE,
            model_used=SCREENING_MODEL,
            error=f"JSON parse error: {e}"
        )

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Screening failed: {e}", exc_info=True)

        return ScreeningResult(
            error=str(e),
            processing_time_ms=processing_time_ms,
            cost_usd=SCREENING_COST_PER_IMAGE,
            model_used=SCREENING_MODEL
        )


def _get_rejection_message(reason: str) -> str:
    """Generate helpful rejection message based on classification reason."""
    reason_lower = reason.lower() if reason else ""

    if "food" in reason_lower or "meal" in reason_lower:
        return (
            "🍽️ This looks like food, not equipment!\n\n"
            "Please send a photo of industrial equipment like:\n"
            "• Equipment nameplates\n"
            "• Control panels or VFDs\n"
            "• Motors or pumps"
        )

    if "pet" in reason_lower or "animal" in reason_lower or "cat" in reason_lower or "dog" in reason_lower:
        return (
            "🐾 Cute, but that's not equipment!\n\n"
            "Please send a photo of industrial equipment like:\n"
            "• Equipment nameplates\n"
            "• Control panels or VFDs\n"
            "• Motors or pumps"
        )

    if "person" in reason_lower or "selfie" in reason_lower or "face" in reason_lower:
        return (
            "👤 Nice photo, but I need equipment!\n\n"
            "Please send a photo of industrial equipment like:\n"
            "• Equipment nameplates\n"
            "• Control panels or VFDs\n"
            "• Motors or pumps"
        )

    if "document" in reason_lower or "paper" in reason_lower or "text" in reason_lower:
        return (
            "📄 This looks like a document.\n\n"
            "For equipment help, please send a photo of:\n"
            "• Equipment nameplates (data plates)\n"
            "• Control panels or VFDs\n"
            "• The actual equipment"
        )

    if "car" in reason_lower or "vehicle" in reason_lower:
        return (
            "🚗 I specialize in industrial equipment.\n\n"
            "Please send a photo of:\n"
            "• Equipment nameplates\n"
            "• Control panels or VFDs\n"
            "• Motors or pumps\n"
            "• PLCs or sensors"
        )

    # Default rejection message
    return (
        "📷 This doesn't appear to be industrial equipment.\n\n"
        "Please send a photo of:\n"
        "• Equipment nameplates (data plates)\n"
        "• Control panels\n"
        "• VFDs/drives\n"
        "• Motors or pumps\n"
        "• PLCs or sensors"
    )


def _log_to_langfuse(
    model: str,
    is_industrial: bool,
    confidence: float,
    category: Optional[str],
    processing_time_ms: int
) -> None:
    """Log screening to Langfuse for cost tracking."""
    try:
        from langfuse import Langfuse

        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            return

        lf = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url or "https://us.cloud.langfuse.com",
        )

        trace = lf.trace(
            name="industrial_photo_screening",
            metadata={
                "model": model,
                "is_industrial": is_industrial,
                "confidence": confidence,
                "category": category,
            }
        )

        trace.generation(
            name="groq_screening",
            model=model,
            usage={
                "input_tokens": 150,  # Estimated
                "output_tokens": 50,   # Estimated
            },
            metadata={
                "cost_usd": SCREENING_COST_PER_IMAGE,
                "duration_ms": processing_time_ms,
                "is_industrial": is_industrial,
                "confidence": confidence,
                "category": category,
            }
        )

        lf.flush()

    except Exception as e:
        logger.debug(f"Langfuse logging skipped: {e}")


# Convenience function for integration
async def should_proceed_to_ocr(base64_image: str) -> tuple[bool, ScreeningResult]:
    """
    Quick check if photo should proceed to OCR.

    Returns:
        Tuple of (should_proceed: bool, result: ScreeningResult)

    Example:
        >>> should_proceed, screening = await should_proceed_to_ocr(image_b64)
        >>> if should_proceed:
        ...     ocr_result = await analyze_image(image_bytes)
        ... else:
        ...     send_message(screening.get_user_message())
    """
    result = await screen_industrial_photo(base64_image)
    return result.passes_threshold, result
