"""
DeepSeek Component Specification Extraction Service

Second-pass extraction for model numbers, manufacturers, and specs.
Part of PHOTO-DEEP-001 feature.

Only called if Groq screening confidence >= 0.80.
Uses DeepSeek-chat for detailed text extraction.

Features:
- Photo hash caching (24h TTL) to avoid re-processing
- Confidence reduction for blurry/partial text
- Response time target: < 3 seconds
- Cost tracking: ~$0.002 per image
"""

import base64
import hashlib
import json
import logging
import time
from typing import Optional

from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.config.settings import settings

logger = logging.getLogger(__name__)

# DeepSeek model - balance of cost and quality
EXTRACTION_MODEL = "deepseek-chat"
EXTRACTION_COST_PER_IMAGE = 0.002  # ~$0.002 per extraction

# Minimum screening confidence to proceed
MIN_SCREENING_CONFIDENCE = 0.80

# Extraction prompt - focused on detailed specs
EXTRACTION_PROMPT = """Extract detailed component specifications from this industrial equipment image.

Respond ONLY with JSON (no markdown, no extra text):
{
  "manufacturer": "exact manufacturer name or null",
  "model_number": "exact model/part number as shown or null",
  "serial_number": "exact serial number or null",
  "specs": {
    "voltage": "with unit (e.g., 480V, 230V) or null",
    "current": "with unit (e.g., 15A, 2.5A) or null",
    "horsepower": "with unit (e.g., 5HP, 0.5HP) or null",
    "rpm": "revolutions per minute or null",
    "phase": "1 or 3 or null",
    "frequency": "with unit (e.g., 60Hz) or null",
    "frame": "frame size or null",
    "enclosure": "NEMA rating or null",
    "ip_rating": "IP rating or null",
    "service_factor": "SF value or null",
    "efficiency": "percentage or class or null",
    "insulation_class": "class letter or null"
  },
  "raw_text": "ALL visible text from nameplate/labels exactly as shown",
  "confidence": 0.0-1.0,
  "text_quality_issues": ["blurry", "partial", "faded", "dirty", "glare"]
}

RULES:
1. Extract EXACT values - do not normalize or guess
2. Include units with all measurements
3. raw_text must include ALL visible text, line by line
4. confidence 0.9+ only if ALL key fields clearly visible
5. Reduce confidence for: blurry text (0.7), partial visibility (0.6), faded/worn (0.5)
6. List any text quality issues that affected extraction"""


def compute_photo_hash(image_data: bytes) -> str:
    """Compute SHA256 hash of image bytes for caching."""
    return hashlib.sha256(image_data).hexdigest()


async def get_cached_extraction(db, photo_hash: str) -> Optional[ExtractionResult]:
    """
    Check cache for existing extraction result.

    Args:
        db: Database connection
        photo_hash: SHA256 hash of image

    Returns:
        ExtractionResult if cached and not expired, None otherwise
    """
    try:
        row = await db.fetchrow(
            """
            SELECT manufacturer, model_number, serial_number, specs,
                   raw_text, confidence, model_used
            FROM photo_analysis_cache
            WHERE photo_hash = $1 AND expires_at > NOW()
            """,
            photo_hash
        )

        if row:
            # Update hit count
            await db.execute(
                """
                UPDATE photo_analysis_cache
                SET hit_count = hit_count + 1, last_hit_at = NOW()
                WHERE photo_hash = $1
                """,
                photo_hash
            )

            logger.info(f"Cache HIT for hash {photo_hash[:12]}...")

            return ExtractionResult(
                manufacturer=row["manufacturer"],
                model_number=row["model_number"],
                serial_number=row["serial_number"],
                specs=row["specs"] or {},
                raw_text=row["raw_text"],
                confidence=row["confidence"],
                model_used=row["model_used"],
                from_cache=True,
                processing_time_ms=0,
                cost_usd=0.0,
            )

        return None

    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
        return None


async def save_extraction_to_cache(
    db,
    photo_hash: str,
    result: ExtractionResult
) -> None:
    """
    Save extraction result to cache.

    Args:
        db: Database connection
        photo_hash: SHA256 hash of image
        result: Extraction result to cache
    """
    try:
        await db.execute(
            """
            INSERT INTO photo_analysis_cache
            (photo_hash, manufacturer, model_number, serial_number,
             specs, raw_text, confidence, model_used,
             processing_time_ms, cost_usd)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (photo_hash) DO UPDATE SET
                manufacturer = EXCLUDED.manufacturer,
                model_number = EXCLUDED.model_number,
                serial_number = EXCLUDED.serial_number,
                specs = EXCLUDED.specs,
                raw_text = EXCLUDED.raw_text,
                confidence = EXCLUDED.confidence,
                model_used = EXCLUDED.model_used,
                processing_time_ms = EXCLUDED.processing_time_ms,
                cost_usd = EXCLUDED.cost_usd,
                created_at = NOW(),
                expires_at = NOW() + INTERVAL '24 hours'
            """,
            photo_hash,
            result.manufacturer,
            result.model_number,
            result.serial_number,
            json.dumps(result.specs),
            result.raw_text,
            result.confidence,
            result.model_used,
            result.processing_time_ms,
            result.cost_usd,
        )
        logger.debug(f"Cached extraction for hash {photo_hash[:12]}...")

    except Exception as e:
        logger.warning(f"Failed to cache extraction: {e}")


async def extract_component_specs(
    base64_image: str,
    screening: ScreeningResult,
    db=None,
) -> ExtractionResult:
    """
    Extract detailed component specifications using DeepSeek.

    Only called if Groq screening confidence >= 0.80.

    Args:
        base64_image: Base64-encoded image data (no data: prefix)
        screening: ScreeningResult from Groq screening pass
        db: Optional database connection for caching

    Returns:
        ExtractionResult with manufacturer, model, serial, specs

    Example:
        >>> screening = await screen_industrial_photo(image_b64)
        >>> if screening.passes_threshold:
        ...     extraction = await extract_component_specs(image_b64, screening)
        ...     print(f"Model: {extraction.model_number}")
    """
    start_time = time.time()

    # Validate screening confidence
    if not screening.passes_threshold:
        return ExtractionResult(
            error=f"Screening confidence {screening.confidence:.0%} below threshold (80%)",
            processing_time_ms=0,
        )

    # Decode image for hashing
    try:
        image_bytes = base64.b64decode(base64_image)
    except Exception as e:
        return ExtractionResult(
            error=f"Invalid base64 image: {e}",
            processing_time_ms=0,
        )

    # Compute hash for caching
    photo_hash = compute_photo_hash(image_bytes)

    # Check cache first
    if db:
        cached = await get_cached_extraction(db, photo_hash)
        if cached:
            return cached

    # Validate DeepSeek API key
    if not settings.deepseek_api_key:
        logger.error("DEEPSEEK_API_KEY not configured")
        return ExtractionResult(
            error="Extraction service not configured (missing DEEPSEEK_API_KEY)",
            processing_time_ms=0,
        )

    try:
        # Import OpenAI client (DeepSeek uses OpenAI-compatible API)
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )

        # Call DeepSeek API
        response = client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1,  # Low temp for consistent extraction
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Parse response
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"DeepSeek response: {response_text[:500]}")

        # Extract JSON from response
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        data = json.loads(json_text)

        # Extract fields
        manufacturer = data.get("manufacturer")
        model_number = data.get("model_number")
        serial_number = data.get("serial_number")
        specs = data.get("specs", {})
        raw_text = data.get("raw_text", "")
        confidence = float(data.get("confidence", 0.0))
        text_quality_issues = data.get("text_quality_issues", [])

        # Reduce confidence for text quality issues
        if text_quality_issues:
            issue_penalties = {
                "blurry": 0.15,
                "partial": 0.20,
                "faded": 0.15,
                "dirty": 0.10,
                "glare": 0.10,
            }
            for issue in text_quality_issues:
                penalty = issue_penalties.get(issue.lower(), 0.05)
                confidence = max(0.3, confidence - penalty)
                logger.debug(f"Applied {penalty} penalty for {issue}")

        # Build result
        result = ExtractionResult(
            manufacturer=manufacturer,
            model_number=model_number,
            serial_number=serial_number,
            specs=specs,
            raw_text=raw_text,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            cost_usd=EXTRACTION_COST_PER_IMAGE,
            model_used=EXTRACTION_MODEL,
        )

        # Cache result
        if db:
            await save_extraction_to_cache(db, photo_hash, result)

        # Log to Langfuse
        _log_to_langfuse(
            model=EXTRACTION_MODEL,
            manufacturer=manufacturer,
            model_number=model_number,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            f"Extraction complete | manufacturer={manufacturer} | "
            f"model={model_number} | conf={confidence:.0%} | "
            f"time={processing_time_ms}ms | cached=False"
        )

        return result

    except json.JSONDecodeError as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"JSON parse error: {e}")

        return ExtractionResult(
            error=f"Failed to parse extraction response: {e}",
            processing_time_ms=processing_time_ms,
            cost_usd=EXTRACTION_COST_PER_IMAGE,
            model_used=EXTRACTION_MODEL,
        )

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Extraction failed: {e}", exc_info=True)

        return ExtractionResult(
            error=str(e),
            processing_time_ms=processing_time_ms,
            cost_usd=EXTRACTION_COST_PER_IMAGE,
            model_used=EXTRACTION_MODEL,
        )


def _log_to_langfuse(
    model: str,
    manufacturer: Optional[str],
    model_number: Optional[str],
    confidence: float,
    processing_time_ms: int,
) -> None:
    """Log extraction to Langfuse for cost tracking."""
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
            name="deepseek_component_extraction",
            metadata={
                "model": model,
                "manufacturer": manufacturer,
                "model_number": model_number,
                "confidence": confidence,
            }
        )

        trace.generation(
            name="deepseek_extraction",
            model=model,
            usage={
                "input_tokens": 300,  # Estimated
                "output_tokens": 200,  # Estimated
            },
            metadata={
                "cost_usd": EXTRACTION_COST_PER_IMAGE,
                "duration_ms": processing_time_ms,
                "confidence": confidence,
            }
        )

        lf.flush()

    except Exception as e:
        logger.debug(f"Langfuse logging skipped: {e}")
