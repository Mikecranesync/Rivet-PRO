"""
Voice Normalizer (EXPERT-007)

Cleans up speech-to-text artifacts for better intent classification.
Handles filler words, spoken abbreviations, and incomplete sentences.

Usage:
    normalizer = VoiceNormalizer()
    clean_text = normalizer.normalize("uh the vee eff dee is like acting up")
    # Returns: "the VFD is acting up"
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class VoiceNormalizer:
    """
    Normalizes speech-to-text output for industrial maintenance context.

    Handles:
    - Filler words (uh, um, like, you know)
    - Spoken abbreviations (vee eff dee → VFD)
    - Incomplete sentences (motor... pump... not working)
    - Common STT errors (bare ring → bearing)
    """

    # Filler words to strip (order matters - longer phrases first)
    FILLER_WORDS = [
        "you know what",
        "you know",
        "i mean",
        "basically",
        "actually",
        "literally",
        "honestly",
        "like",
        "um",
        "uh",
        "er",
        "ah",
        "so",
        "well",
    ]

    # Spoken abbreviations → correct form
    # Maps phonetic spellings to industry acronyms
    SPOKEN_ABBREVIATIONS: Dict[str, str] = {
        # Equipment types
        "vee eff dee": "VFD",
        "vfd": "VFD",
        "v f d": "VFD",
        "ay ach you": "AHU",
        "ahu": "AHU",
        "a h u": "AHU",
        "pee el see": "PLC",
        "plc": "PLC",
        "p l c": "PLC",
        "h m i": "HMI",
        "hmi": "HMI",
        "r t u": "RTU",
        "rtu": "RTU",

        # Electrical terms
        "ay see": "AC",
        "a c": "AC",
        "dee see": "DC",
        "d c": "DC",
        "eff el ay": "FLA",
        "f l a": "FLA",
        "fla": "FLA",
        "ar el ay": "RLA",
        "r l a": "RLA",
        "rla": "RLA",
        "kay dubya": "kW",
        "kay double u": "kW",
        "k w": "kW",
        "aitch pee": "HP",
        "h p": "HP",
        "hp": "HP",
        "are pee em": "RPM",
        "r p m": "RPM",
        "rpm": "RPM",

        # Measurements
        "pee ess eye": "PSI",
        "p s i": "PSI",
        "psi": "PSI",
        "gee pee em": "GPM",
        "g p m": "GPM",
        "gpm": "GPM",
        "see eff em": "CFM",
        "c f m": "CFM",
        "cfm": "CFM",

        # Equipment parts
        "bee tee you": "BTU",
        "b t u": "BTU",
        "btu": "BTU",
        "oh ring": "O-ring",
        "ohring": "O-ring",

        # Processes
        "pee em": "PM",
        "p m": "PM",
        "double u oh": "WO",
        "w o": "WO",
        "wo": "WO",
    }

    # Common speech-to-text errors → corrections
    # Maps misheard words to correct technical terms
    STT_CORRECTIONS: Dict[str, str] = {
        # Bearing-related
        "bare ring": "bearing",
        "baring": "bearing",
        "baron": "bearing",
        "barring": "bearing",

        # Motor-related
        "motor": "motor",
        "moder": "motor",
        "murder": "motor",

        # Technical terms
        "mega": "megger",
        "meager": "megger",
        "meggar": "megger",
        "over heating": "overheating",
        "over heat": "overheat",
        "short circuit": "short circuit",
        "short-circuit": "short circuit",
        "ground fault": "ground fault",
        "ground-fault": "ground fault",
        "phase imbalance": "phase imbalance",
        "face imbalance": "phase imbalance",
        "phase and balance": "phase imbalance",

        # Fault codes
        "fault code": "fault code",
        "faultcode": "fault code",
        "error code": "error code",
        "errorcode": "error code",

        # Actions
        "work order": "work order",
        "workorder": "work order",
        "log it": "log this",
        "logged it": "log this",
        "create a": "create",
        "make a": "create",

        # Common brand names
        "see mens": "Siemens",
        "seamen": "Siemens",
        "siemens": "Siemens",
        "allen bradley": "Allen-Bradley",
        "allen-bradley": "Allen-Bradley",
        "ab": "Allen-Bradley",
        "abb": "ABB",
        "a b b": "ABB",
        "dain fuss": "Danfoss",
        "dan foss": "Danfoss",
        "danfoss": "Danfoss",
    }

    # Technical terms to preserve (case-sensitive matching)
    PRESERVE_TERMS = [
        "megger",
        "FLA",
        "RLA",
        "phase imbalance",
        "ground fault",
        "short circuit",
        "nameplate",
        "torque",
        "alignment",
        "lockout",
        "tagout",
        "LOTO",
        "cavitation",
        "harmonics",
    ]

    def __init__(self):
        """Initialize voice normalizer with compiled patterns."""
        # Pre-compile patterns for efficiency
        self._filler_pattern = self._build_filler_pattern()
        self._ellipsis_pattern = re.compile(r'\.{2,}|\s*\.\s*\.\s*\.?\s*')
        self._whitespace_pattern = re.compile(r'\s+')

    def _build_filler_pattern(self) -> re.Pattern:
        """Build regex pattern for filler words."""
        # Sort by length (longest first) to match phrases before words
        sorted_fillers = sorted(self.FILLER_WORDS, key=len, reverse=True)
        # Escape and join with word boundaries
        escaped = [re.escape(f) for f in sorted_fillers]
        pattern = r'\b(?:' + '|'.join(escaped) + r')\b'
        return re.compile(pattern, re.IGNORECASE)

    def normalize(self, text: str) -> str:
        """
        Normalize speech-to-text input.

        Args:
            text: Raw speech-to-text output

        Returns:
            Normalized text suitable for intent classification
        """
        if not text:
            return ""

        original = text
        result = text

        # Step 1: Lowercase for processing (we'll fix case later)
        result = result.lower()

        # Step 2: Strip filler words
        result = self._strip_fillers(result)

        # Step 3: Handle ellipsis/incomplete sentences
        result = self._handle_ellipsis(result)

        # Step 4: Apply STT corrections
        result = self._apply_corrections(result)

        # Step 5: Expand spoken abbreviations
        result = self._expand_abbreviations(result)

        # Step 6: Clean up whitespace
        result = self._clean_whitespace(result)

        # Step 7: Capitalize preserved terms
        result = self._capitalize_terms(result)

        if result != original.lower():
            logger.debug(f"Voice normalized: '{original}' -> '{result}'")

        return result.strip()

    def _strip_fillers(self, text: str) -> str:
        """Remove filler words from text."""
        result = self._filler_pattern.sub(' ', text)
        return result

    def _handle_ellipsis(self, text: str) -> str:
        """Convert ellipsis to spaces for coherent sentences."""
        # Replace ellipsis with single space
        result = self._ellipsis_pattern.sub(' ', text)
        return result

    def _apply_corrections(self, text: str) -> str:
        """Apply speech-to-text error corrections."""
        result = text
        for wrong, correct in self.STT_CORRECTIONS.items():
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
            result = pattern.sub(correct, result)
        return result

    def _expand_abbreviations(self, text: str) -> str:
        """Expand spoken abbreviations to proper form."""
        result = text
        # Sort by length (longest first) to match multi-word phrases first
        sorted_abbrevs = sorted(
            self.SPOKEN_ABBREVIATIONS.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
        for spoken, proper in sorted_abbrevs:
            pattern = re.compile(r'\b' + re.escape(spoken) + r'\b', re.IGNORECASE)
            result = pattern.sub(proper, result)
        return result

    def _clean_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        result = self._whitespace_pattern.sub(' ', text)
        return result.strip()

    def _capitalize_terms(self, text: str) -> str:
        """Ensure technical terms have correct capitalization."""
        result = text
        for term in self.PRESERVE_TERMS:
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            result = pattern.sub(term, result)
        return result

    def is_voice_input(self, text: str) -> bool:
        """
        Heuristically detect if input is likely from speech-to-text.

        Indicators:
        - Contains filler words
        - Contains spoken abbreviations
        - Contains ellipsis
        - All lowercase
        - No punctuation

        Args:
            text: Input text to analyze

        Returns:
            True if input appears to be from speech-to-text
        """
        if not text:
            return False

        indicators = 0

        # Check for filler words
        if self._filler_pattern.search(text.lower()):
            indicators += 1

        # Check for spoken abbreviations
        lower_text = text.lower()
        for spoken in self.SPOKEN_ABBREVIATIONS.keys():
            if spoken in lower_text:
                indicators += 1
                break

        # Check for ellipsis
        if '...' in text or self._ellipsis_pattern.search(text):
            indicators += 1

        # Check if all lowercase (no caps at all)
        if text == text.lower() and len(text) > 5:
            indicators += 1

        # Check for lack of punctuation
        if not any(c in text for c in '.,!?;:'):
            indicators += 0.5

        return indicators >= 1.5


# Module-level singleton
_normalizer: Optional[VoiceNormalizer] = None


def get_voice_normalizer() -> VoiceNormalizer:
    """Get or create the voice normalizer singleton."""
    global _normalizer
    if _normalizer is None:
        _normalizer = VoiceNormalizer()
    return _normalizer


def normalize_voice_input(text: str) -> str:
    """Convenience function to normalize voice input."""
    return get_voice_normalizer().normalize(text)


__all__ = [
    "VoiceNormalizer",
    "get_voice_normalizer",
    "normalize_voice_input",
]
