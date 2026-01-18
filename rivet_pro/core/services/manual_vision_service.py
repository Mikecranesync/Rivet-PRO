"""
Manual Vision Service

Handles image inputs for the PDF Manual Q&A system.
Extracts text and diagrams from manual page images using vision models.

Uses:
- ScreeningService for image classification (is this a manual page?)
- LLMRouter for DeepSeek/Groq Vision API calls
- Manual context for grounded responses
"""

import base64
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

from rivet_pro.adapters.llm.router import (
    LLMRouter,
    ProviderConfig,
    VISION_PROVIDER_CHAIN,
    get_llm_router,
)

logger = logging.getLogger(__name__)


class ImageType(Enum):
    """Type of image detected."""
    MANUAL_PAGE = "manual_page"       # Full page from manual
    DIAGRAM = "diagram"               # Technical diagram/schematic
    PHOTO = "photo"                   # Real-world photo (equipment, nameplate)
    SCREENSHOT = "screenshot"         # Digital screenshot
    UNKNOWN = "unknown"


@dataclass
class VisionExtractionResult:
    """Result of vision extraction."""
    extracted_text: str               # OCR-extracted text
    image_type: ImageType             # Detected image type
    description: str                  # Brief description of image contents
    relevant_elements: List[str]      # Key elements identified (diagrams, tables, etc.)
    confidence: float                 # Extraction confidence
    cost_usd: float                   # Vision API cost
    model_used: str                   # Model that performed extraction


# System prompt for manual page extraction
MANUAL_PAGE_EXTRACTION_PROMPT = """You are analyzing an image from an equipment manual. Your task is to:

1. **Extract all readable text** from the image, preserving structure (headings, bullet points, numbered lists)
2. **Identify key elements**:
   - Section titles and headings
   - Safety warnings (WARNING, CAUTION, DANGER)
   - Procedure steps
   - Technical specifications
   - Diagram labels and callouts
3. **Describe any diagrams or images** within the page (e.g., "Wiring diagram showing motor connections")

## Output Format:

### Extracted Text
[Structured text from the image]

### Key Elements
- [List of important elements found]

### Image Description
[Brief description of what the page contains]

Be thorough - technicians depend on accurate extraction."""


class ManualVisionService:
    """
    Service for processing manual page images.

    Features:
    - Image type detection
    - OCR extraction with structure preservation
    - Diagram/schematic description
    - Integration with text RAG pipeline
    """

    # Minimum confidence for accepting extraction
    MIN_CONFIDENCE = 0.6

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None
    ):
        """
        Initialize vision service.

        Args:
            llm_router: LLMRouter instance. Uses singleton if None.
        """
        self.llm_router = llm_router or get_llm_router()
        logger.info("ManualVisionService initialized")

    async def process_manual_image(
        self,
        image_data: bytes,
        query: str,
        manual_context: Optional[str] = None
    ) -> VisionExtractionResult:
        """
        Process a manual page image and extract information.

        Args:
            image_data: Raw image bytes (JPEG/PNG)
            query: User's question about the image
            manual_context: Optional text context from RAG

        Returns:
            VisionExtractionResult with extracted text and metadata

        Example:
            result = await vision_service.process_manual_image(
                image_data=image_bytes,
                query="What safety warnings are shown?"
            )
            print(result.extracted_text)
        """
        logger.info(f"[Vision] Processing image ({len(image_data)} bytes)")

        # Step 1: Detect image type
        image_type = self._detect_image_type(image_data)

        # Step 2: Build extraction prompt
        prompt = self._build_extraction_prompt(query, manual_context)

        # Step 3: Call vision API
        extracted_text, cost, model = await self._call_vision_api(
            image_data, prompt
        )

        if not extracted_text:
            return VisionExtractionResult(
                extracted_text="Unable to extract text from image.",
                image_type=ImageType.UNKNOWN,
                description="Extraction failed",
                relevant_elements=[],
                confidence=0.0,
                cost_usd=cost,
                model_used=model
            )

        # Step 4: Parse extraction results
        parsed = self._parse_extraction(extracted_text)

        logger.info(
            f"[Vision] Extracted {len(parsed['text'])} chars | "
            f"type={image_type.value} | cost=${cost:.4f}"
        )

        return VisionExtractionResult(
            extracted_text=parsed['text'],
            image_type=image_type,
            description=parsed['description'],
            relevant_elements=parsed['elements'],
            confidence=parsed['confidence'],
            cost_usd=cost,
            model_used=model
        )

    async def answer_image_question(
        self,
        image_data: bytes,
        query: str,
        manual_context: Optional[str] = None
    ) -> Tuple[str, float, str]:
        """
        Answer a question about a manual page image.

        Combines vision extraction with question answering in a single call.

        Args:
            image_data: Raw image bytes
            query: User's question
            manual_context: Optional RAG context for grounding

        Returns:
            Tuple of (answer, cost_usd, model_used)
        """
        # Build Q&A prompt
        prompt = self._build_qa_prompt(query, manual_context)

        # Call vision API
        answer, cost, model = await self._call_vision_api(image_data, prompt)

        return answer or "Unable to analyze the image.", cost, model

    def _detect_image_type(self, image_data: bytes) -> ImageType:
        """
        Detect the type of image based on properties.

        For now, uses simple heuristics. Could be enhanced with ML classifier.
        """
        # Basic detection based on image size
        # Manual pages tend to be larger (full page scans)
        size_kb = len(image_data) / 1024

        if size_kb > 500:
            return ImageType.MANUAL_PAGE
        elif size_kb > 100:
            return ImageType.DIAGRAM
        else:
            return ImageType.PHOTO

    def _build_extraction_prompt(
        self,
        query: str,
        manual_context: Optional[str]
    ) -> str:
        """Build prompt for extraction task."""
        parts = [MANUAL_PAGE_EXTRACTION_PROMPT]

        if manual_context:
            parts.append("\n## Additional Context from Manual")
            parts.append(manual_context[:1000])

        if query:
            parts.append(f"\n## User's Specific Question")
            parts.append(f"While extracting, pay special attention to: {query}")

        return "\n".join(parts)

    def _build_qa_prompt(
        self,
        query: str,
        manual_context: Optional[str]
    ) -> str:
        """Build prompt for direct Q&A task."""
        parts = [
            "You are a PDF Manual Assistant analyzing a manual page image.",
            "",
            "## Instructions",
            "1. Examine the image carefully",
            "2. Answer the user's question based ONLY on what you can see",
            "3. Cite specific sections, page numbers, or labels visible in the image",
            "4. If the answer is not visible in the image, say so clearly",
            "",
        ]

        if manual_context:
            parts.append("## Related Manual Context")
            parts.append(manual_context[:1000])
            parts.append("")

        parts.append(f"## User's Question")
        parts.append(query)
        parts.append("")
        parts.append("Provide a helpful, accurate answer based on the image.")

        return "\n".join(parts)

    async def _call_vision_api(
        self,
        image_data: bytes,
        prompt: str
    ) -> Tuple[str, float, str]:
        """
        Call vision API with fallback chain.

        Returns:
            Tuple of (response_text, cost_usd, model_name)
        """
        # Try providers in cost order
        for provider_config in VISION_PROVIDER_CHAIN:
            if not self.llm_router.is_provider_available(provider_config.name):
                continue

            # Check image size limit
            image_size_mb = len(image_data) / (1024 * 1024)
            if image_size_mb > provider_config.max_image_size_mb:
                logger.warning(
                    f"Image too large for {provider_config.name}: "
                    f"{image_size_mb:.1f}MB > {provider_config.max_image_size_mb}MB"
                )
                continue

            try:
                logger.debug(
                    f"[Vision] Trying {provider_config.name}/{provider_config.model}"
                )

                text, cost = await self.llm_router.call_vision(
                    provider_config=provider_config,
                    image_bytes=image_data,
                    prompt=prompt,
                    max_tokens=2000
                )

                if text:
                    return text, cost, provider_config.model

            except Exception as e:
                logger.warning(
                    f"[Vision] {provider_config.name} failed: {e}"
                )
                continue

        # All providers failed
        logger.error("[Vision] All vision providers failed")
        return "", 0.0, "none"

    def _parse_extraction(self, raw_response: str) -> dict:
        """
        Parse extraction response into structured data.

        Returns dict with:
        - text: Extracted text
        - description: Image description
        - elements: List of key elements
        - confidence: Estimated confidence
        """
        result = {
            'text': raw_response,
            'description': '',
            'elements': [],
            'confidence': 0.7  # Default confidence
        }

        # Try to parse structured sections
        lines = raw_response.split('\n')
        current_section = None
        text_lines = []
        elements = []
        description_lines = []

        for line in lines:
            line_lower = line.lower().strip()

            if 'extracted text' in line_lower:
                current_section = 'text'
            elif 'key elements' in line_lower:
                current_section = 'elements'
            elif 'image description' in line_lower or 'description' in line_lower:
                current_section = 'description'
            elif line.strip():
                if current_section == 'text':
                    text_lines.append(line)
                elif current_section == 'elements':
                    # Parse bullet points
                    if line.strip().startswith(('-', '*', '•')):
                        elements.append(line.strip()[1:].strip())
                elif current_section == 'description':
                    description_lines.append(line)
                else:
                    # Default to text
                    text_lines.append(line)

        # Assemble results
        if text_lines:
            result['text'] = '\n'.join(text_lines)
        if elements:
            result['elements'] = elements[:10]  # Limit to 10
        if description_lines:
            result['description'] = ' '.join(description_lines)[:500]

        # Estimate confidence based on content richness
        content_length = len(result['text'])
        if content_length > 1000:
            result['confidence'] = 0.85
        elif content_length > 500:
            result['confidence'] = 0.75
        elif content_length > 100:
            result['confidence'] = 0.65
        else:
            result['confidence'] = 0.5

        return result

    def is_manual_page(self, image_data: bytes) -> bool:
        """
        Quick check if image appears to be a manual page.

        For filtering out non-relevant images before processing.
        """
        image_type = self._detect_image_type(image_data)
        return image_type in (ImageType.MANUAL_PAGE, ImageType.DIAGRAM)


__all__ = [
    "ManualVisionService",
    "VisionExtractionResult",
    "ImageType",
]
