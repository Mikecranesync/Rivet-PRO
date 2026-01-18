"""
PDF Chunker Service

Intelligent PDF text chunking with semantic overlap for RAG retrieval.
Chunks are optimized for vector embedding and context retrieval.

Features:
- Section-aware chunking (preserves headings)
- Overlapping chunks for context continuity
- Page number tracking for citations
- Keyword extraction for metadata
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# PDF extraction
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logging.warning("PyPDF2 not installed - PDF chunking disabled")

logger = logging.getLogger(__name__)


@dataclass
class SectionBoundary:
    """Represents a detected section boundary in the text."""
    title: str
    char_start: int
    level: int = 1  # 1 = main section, 2 = subsection, etc.


@dataclass
class ManualChunk:
    """A single chunk of manual text with metadata."""
    content: str
    page_number: int
    chunk_index: int
    section_title: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    char_start: int = 0
    char_end: int = 0

    def __post_init__(self):
        if self.char_end == 0:
            self.char_end = self.char_start + len(self.content)


class PDFChunkerService:
    """
    Service for intelligent PDF text chunking.

    Produces overlapping chunks optimized for RAG retrieval:
    - Target chunk size: ~1024 tokens (~4000 chars)
    - Overlap: 25% (256 tokens, ~1000 chars)
    - Section boundaries respected when possible
    """

    # Section detection patterns (ordered by priority)
    SECTION_PATTERNS = [
        # Numbered sections: "1.", "1.1", "1.1.1", etc.
        (r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{5,80})', 1),
        # Chapter headings: "Chapter 1:", "CHAPTER 1:", etc.
        (r'^(?:CHAPTER|Chapter)\s+\d+[:\s]+([^\n]{5,80})', 1),
        # ALL CAPS headings (likely section titles)
        (r'^([A-Z][A-Z\s]{10,60})$', 1),
        # Bold-style numbered: "1) Something", "A. Something"
        (r'^([A-Z\d][.)]\s+[A-Z][^\n]{5,80})', 2),
    ]

    # Keywords to extract (equipment-related)
    KEYWORD_PATTERNS = [
        r'\b[A-Z]\d{3,5}\b',  # Fault codes: F0001, E0123
        r'\b\d+\s*(?:V|A|kW|HP|Hz)\b',  # Electrical specs
        r'\b(?:WARNING|CAUTION|DANGER|NOTE)\b',  # Safety markers
    ]

    def __init__(
        self,
        chunk_size: int = 1024,
        overlap: int = 256,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in tokens (~4 chars per token)
            overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum chunk size in tokens
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

        # Convert to approximate character counts
        self.chunk_chars = chunk_size * 4
        self.overlap_chars = overlap * 4
        self.min_chunk_chars = min_chunk_size * 4

        logger.info(
            f"PDFChunkerService initialized | "
            f"chunk_size={chunk_size} tokens | overlap={overlap} tokens"
        )

    async def chunk_pdf(
        self,
        pdf_path: str,
        max_pages: int = 100
    ) -> List[ManualChunk]:
        """
        Extract and chunk text from a PDF file.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process

        Returns:
            List of ManualChunk objects with metadata

        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PyPDF2 not installed or PDF is invalid
        """
        if not HAS_PYPDF2:
            raise ValueError("PyPDF2 not installed - cannot process PDF")

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Extract text with page tracking
        pages_text = await self._extract_pages(str(path), max_pages)
        if not pages_text:
            logger.warning(f"No text extracted from {pdf_path}")
            return []

        # Combine text with page markers
        full_text, page_map = self._combine_pages(pages_text)

        # Detect sections
        sections = self._detect_sections(full_text)
        logger.debug(f"Detected {len(sections)} sections in {pdf_path}")

        # Create overlapping chunks
        chunks = self._create_overlapping_chunks(full_text, sections, page_map)

        # Extract keywords for each chunk
        for chunk in chunks:
            chunk.keywords = self._extract_keywords(chunk.content)

        logger.info(
            f"Chunked PDF | file={path.name} | "
            f"pages={len(pages_text)} | chunks={len(chunks)}"
        )

        return chunks

    async def _extract_pages(
        self,
        pdf_path: str,
        max_pages: int
    ) -> List[Tuple[int, str]]:
        """
        Extract text from PDF pages.

        Returns:
            List of (page_number, text) tuples (1-indexed)
        """
        pages = []

        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)

                # Handle encryption
                if reader.is_encrypted:
                    try:
                        reader.decrypt('')
                    except Exception:
                        logger.warning(f"PDF is encrypted: {pdf_path}")
                        return []

                num_pages = min(len(reader.pages), max_pages)

                for page_num in range(num_pages):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        if text and text.strip():
                            cleaned = self._clean_text(text)
                            pages.append((page_num + 1, cleaned))  # 1-indexed
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue

        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"PDF read error: {e}")
            return []
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return []

        return pages

    def _combine_pages(
        self,
        pages: List[Tuple[int, str]]
    ) -> Tuple[str, List[Tuple[int, int]]]:
        """
        Combine page texts and build character-to-page mapping.

        Returns:
            (full_text, page_map) where page_map is [(page_num, char_start), ...]
        """
        full_text = ""
        page_map = []  # (page_num, char_start)

        for page_num, text in pages:
            page_map.append((page_num, len(full_text)))
            full_text += text + "\n\n"

        return full_text, page_map

    def _detect_sections(self, text: str) -> List[SectionBoundary]:
        """
        Detect section boundaries in the text.

        Returns:
            List of SectionBoundary objects sorted by position
        """
        sections = []

        for pattern, level in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE):
                title = match.group(1) if match.lastindex else match.group(0)
                title = title.strip()[:100]  # Limit title length

                sections.append(SectionBoundary(
                    title=title,
                    char_start=match.start(),
                    level=level
                ))

        # Sort by position and deduplicate nearby sections
        sections.sort(key=lambda s: s.char_start)

        # Remove sections too close together (within 100 chars)
        deduplicated = []
        for section in sections:
            if not deduplicated or section.char_start - deduplicated[-1].char_start > 100:
                deduplicated.append(section)

        return deduplicated

    def _create_overlapping_chunks(
        self,
        text: str,
        sections: List[SectionBoundary],
        page_map: List[Tuple[int, int]]
    ) -> List[ManualChunk]:
        """
        Create overlapping chunks with section awareness.

        Strategy:
        1. Start at position 0
        2. Find chunk end (~chunk_chars from start)
        3. Try to end at sentence boundary
        4. Next chunk starts at (end - overlap_chars)
        5. Track current section for each chunk
        """
        chunks = []
        position = 0
        chunk_index = 0
        text_len = len(text)

        while position < text_len:
            # Calculate chunk boundaries
            chunk_start = position
            chunk_end = min(position + self.chunk_chars, text_len)

            # Try to end at sentence boundary
            if chunk_end < text_len:
                # Look for sentence end in last 20% of chunk
                search_start = chunk_end - int(self.chunk_chars * 0.2)
                sentence_end = self._find_sentence_boundary(
                    text, search_start, chunk_end + 100
                )
                if sentence_end > search_start:
                    chunk_end = sentence_end

            # Extract chunk content
            content = text[chunk_start:chunk_end].strip()

            # Skip if too small
            if len(content) < self.min_chunk_chars:
                position = chunk_end
                continue

            # Determine page number
            page_num = self._get_page_for_position(chunk_start, page_map)

            # Determine current section
            section_title = self._get_section_for_position(chunk_start, sections)

            # Create chunk
            chunk = ManualChunk(
                content=content,
                page_number=page_num,
                chunk_index=chunk_index,
                section_title=section_title,
                char_start=chunk_start,
                char_end=chunk_end
            )
            chunks.append(chunk)
            chunk_index += 1

            # Move position with overlap
            position = chunk_end - self.overlap_chars

            # Ensure forward progress
            if position <= chunk_start:
                position = chunk_end

        return chunks

    def _find_sentence_boundary(
        self,
        text: str,
        start: int,
        end: int
    ) -> int:
        """
        Find sentence boundary (. ! ? followed by space/newline) in range.

        Returns:
            Position after sentence end, or end if no boundary found
        """
        search_text = text[start:end]

        # Find last sentence boundary
        pattern = r'[.!?](?:\s|$)'
        matches = list(re.finditer(pattern, search_text))

        if matches:
            # Return position after the last sentence end
            last_match = matches[-1]
            return start + last_match.end()

        # Fallback: try to break at newline
        newline_pos = search_text.rfind('\n')
        if newline_pos > 0:
            return start + newline_pos + 1

        return end

    def _get_page_for_position(
        self,
        position: int,
        page_map: List[Tuple[int, int]]
    ) -> int:
        """Get page number for a character position."""
        page_num = 1
        for pn, char_start in page_map:
            if char_start <= position:
                page_num = pn
            else:
                break
        return page_num

    def _get_section_for_position(
        self,
        position: int,
        sections: List[SectionBoundary]
    ) -> Optional[str]:
        """Get section title for a character position."""
        current_section = None
        for section in sections:
            if section.char_start <= position:
                current_section = section.title
            else:
                break
        return current_section

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from chunk text."""
        keywords = set()

        for pattern in self.KEYWORD_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                keyword = match.group(0).upper()
                keywords.add(keyword)

        return list(keywords)[:10]  # Limit to 10 keywords

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted PDF text.

        - Normalize whitespace
        - Remove page numbers and headers
        - Fix common OCR issues
        """
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove standalone page numbers
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        text = re.sub(r'\n\s*Page \d+ of \d+\s*\n', '\n', text, flags=re.I)

        # Remove common footer patterns
        text = re.sub(r'\n\s*©.*?\n', '\n', text)
        text = re.sub(r'\n\s*All rights reserved.*?\n', '\n', text, flags=re.I)

        return text.strip()

    def estimate_chunks(self, text_length: int) -> int:
        """
        Estimate number of chunks for given text length.

        Args:
            text_length: Character count

        Returns:
            Estimated chunk count
        """
        if text_length <= self.chunk_chars:
            return 1

        effective_chunk_size = self.chunk_chars - self.overlap_chars
        return max(1, (text_length - self.overlap_chars) // effective_chunk_size + 1)


# ===== Utility Functions =====

def chunk_text_simple(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[str]:
    """
    Simple text chunking without PDF-specific features.

    Args:
        text: Text to chunk
        chunk_size: Characters per chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    position = 0
    text_len = len(text)

    while position < text_len:
        end = min(position + chunk_size, text_len)
        chunk = text[position:end].strip()
        if chunk:
            chunks.append(chunk)
        position = end - overlap
        if position <= 0:
            position = end

    return chunks


__all__ = [
    "PDFChunkerService",
    "ManualChunk",
    "SectionBoundary",
    "chunk_text_simple",
]
