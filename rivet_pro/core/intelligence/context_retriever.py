"""
Context Retriever (EXPERT-006)

Retrieves relevant equipment history and past cases before generating responses.
Provides historical context to make the AI assistant aware of past issues.

Usage:
    retriever = ContextRetriever(db)
    context = await retriever.get_relevant_context(
        message="motor is overheating",
        intent=IntentType.TROUBLESHOOT,
        user_id="telegram_123"
    )
    # context.formatted_context contains bullet points for LLM injection
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from rivet_pro.core.intelligence.intent_classifier import IntentType

logger = logging.getLogger(__name__)


@dataclass
class ContextMatch:
    """A single relevant context match."""
    source: str  # 'work_order', 'equipment', 'fault_history'
    relevance_score: float  # 0.0 to 1.0
    title: str
    summary: str
    equipment_number: Optional[str] = None
    fault_code: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None


@dataclass
class RetrievedContext:
    """Result of context retrieval."""
    matches: List[ContextMatch] = field(default_factory=list)
    total_tokens_estimate: int = 0
    formatted_context: str = ""
    has_relevant_history: bool = False

    def to_system_prompt_injection(self) -> str:
        """Format context for injection into system prompt."""
        if not self.has_relevant_history:
            return ""
        return f"\n\n## Relevant Equipment History\n{self.formatted_context}"


class ContextRetriever:
    """
    Retrieves relevant equipment and work order history for context-aware responses.

    Searches for similar past issues based on:
    - Equipment mentions (manufacturer, model, type)
    - Fault codes mentioned in the query
    - Symptom keywords (overheating, noise, fault, etc.)
    """

    # Maximum tokens to inject as context (avoid prompt bloat)
    MAX_CONTEXT_TOKENS = 500

    # Keywords that indicate equipment/troubleshooting context is relevant
    EQUIPMENT_KEYWORDS = [
        'motor', 'vfd', 'drive', 'pump', 'compressor', 'chiller',
        'ahu', 'fan', 'conveyor', 'plc', 'hmi', 'sensor', 'valve'
    ]

    SYMPTOM_KEYWORDS = [
        'overheating', 'hot', 'noise', 'vibration', 'fault', 'error',
        'trip', 'fail', 'won\'t start', 'not working', 'stuck',
        'leak', 'alarm', 'warning', 'high', 'low', 'smoke', 'smell'
    ]

    # Fault code pattern (e.g., F0002, E-001, FAULT_123, ERR123)
    # Requires: letter(s) + optional separator + 3+ digits
    FAULT_CODE_PATTERN = re.compile(
        r'\b[A-Z]+[\-_]?\d{3,5}\b',  # FAULT_123, E-001, F0002, ERR123
        re.IGNORECASE
    )

    def __init__(self, db):
        """
        Initialize context retriever.

        Args:
            db: Database connection (from rivet_pro.infra.database)
        """
        self.db = db

    def _extract_equipment_terms(self, message: str) -> List[str]:
        """Extract equipment-related terms from message."""
        message_lower = message.lower()
        found = []

        for keyword in self.EQUIPMENT_KEYWORDS:
            if keyword in message_lower:
                found.append(keyword)

        return found

    def _extract_symptoms(self, message: str) -> List[str]:
        """Extract symptom keywords from message."""
        message_lower = message.lower()
        found = []

        for symptom in self.SYMPTOM_KEYWORDS:
            if symptom in message_lower:
                found.append(symptom)

        return found

    def _extract_fault_codes(self, message: str) -> List[str]:
        """Extract fault codes from message."""
        matches = self.FAULT_CODE_PATTERN.findall(message)
        return [m.upper() for m in matches]

    async def _search_work_orders_by_keywords(
        self,
        keywords: List[str],
        user_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Search work orders containing any of the keywords."""
        if not keywords:
            return []

        try:
            # Build OR condition for keywords
            keyword_conditions = " OR ".join([
                f"LOWER(title) LIKE '%{kw.lower()}%' OR LOWER(description) LIKE '%{kw.lower()}%'"
                for kw in keywords
            ])

            query = f"""
                SELECT
                    work_order_number,
                    equipment_number,
                    title,
                    description,
                    status,
                    fault_codes,
                    created_at,
                    manufacturer,
                    model_number
                FROM work_orders
                WHERE user_id = $1
                  AND ({keyword_conditions})
                ORDER BY created_at DESC
                LIMIT $2
            """

            results = await self.db.execute_query_async(query, (user_id, limit))
            return results or []

        except Exception as e:
            logger.warning(f"Error searching work orders: {e}")
            return []

    async def _search_work_orders_by_fault_code(
        self,
        fault_codes: List[str],
        user_id: str,
        limit: int = 3
    ) -> List[Dict]:
        """Search work orders with matching fault codes."""
        if not fault_codes:
            return []

        try:
            # Search for any matching fault code in the array
            query = """
                SELECT
                    work_order_number,
                    equipment_number,
                    title,
                    description,
                    status,
                    fault_codes,
                    created_at,
                    manufacturer,
                    model_number
                FROM work_orders
                WHERE user_id = $1
                  AND fault_codes && $2::text[]
                ORDER BY created_at DESC
                LIMIT $3
            """

            results = await self.db.execute_query_async(query, (user_id, fault_codes, limit))
            return results or []

        except Exception as e:
            logger.warning(f"Error searching work orders by fault code: {e}")
            return []

    async def _search_equipment_by_keywords(
        self,
        keywords: List[str],
        user_id: str,
        limit: int = 3
    ) -> List[Dict]:
        """Search equipment matching keywords."""
        if not keywords:
            return []

        try:
            # Build OR condition for equipment type matching
            keyword_conditions = " OR ".join([
                f"LOWER(equipment_type) LIKE '%{kw.lower()}%' OR LOWER(manufacturer) LIKE '%{kw.lower()}%' OR LOWER(model_number) LIKE '%{kw.lower()}%'"
                for kw in keywords
            ])

            query = f"""
                SELECT
                    equipment_number,
                    manufacturer,
                    model_number,
                    equipment_type,
                    location,
                    work_order_count,
                    last_reported_fault,
                    last_work_order_at
                FROM cmms_equipment
                WHERE owned_by_user_id = $1
                  AND ({keyword_conditions})
                ORDER BY work_order_count DESC
                LIMIT $2
            """

            results = await self.db.execute_query_async(query, (user_id, limit))
            return results or []

        except Exception as e:
            logger.warning(f"Error searching equipment: {e}")
            return []

    def _score_relevance(
        self,
        record: Dict,
        equipment_terms: List[str],
        symptoms: List[str],
        fault_codes: List[str]
    ) -> float:
        """Score how relevant a record is to the query."""
        score = 0.3  # Base score

        # Check title/description for keywords
        title = (record.get('title') or '').lower()
        desc = (record.get('description') or '').lower()
        text = f"{title} {desc}"

        for term in equipment_terms:
            if term.lower() in text:
                score += 0.15

        for symptom in symptoms:
            if symptom.lower() in text:
                score += 0.20

        # Fault code match is very relevant
        record_faults = record.get('fault_codes') or []
        for fc in fault_codes:
            if fc.upper() in [f.upper() for f in record_faults]:
                score += 0.35

        return min(1.0, score)

    def _format_work_order_match(self, wo: Dict, score: float) -> ContextMatch:
        """Format work order as context match."""
        equipment_info = ""
        if wo.get('manufacturer') or wo.get('model_number'):
            equipment_info = f" ({wo.get('manufacturer', '')} {wo.get('model_number', '')})".strip()

        fault_str = ""
        if wo.get('fault_codes'):
            fault_str = f" [Faults: {', '.join(wo['fault_codes'])}]"

        summary = f"{wo.get('title', 'Work order')}{fault_str}"
        if wo.get('status') == 'completed':
            summary += " - RESOLVED"

        return ContextMatch(
            source='work_order',
            relevance_score=score,
            title=f"WO {wo.get('work_order_number', '?')}{equipment_info}",
            summary=summary,
            equipment_number=wo.get('equipment_number'),
            fault_code=wo['fault_codes'][0] if wo.get('fault_codes') else None,
            created_at=str(wo.get('created_at', ''))[:10],
            status=wo.get('status')
        )

    def _format_equipment_match(self, equip: Dict, score: float) -> ContextMatch:
        """Format equipment as context match."""
        summary_parts = []

        if equip.get('equipment_type'):
            summary_parts.append(equip['equipment_type'])
        if equip.get('location'):
            summary_parts.append(f"at {equip['location']}")
        if equip.get('work_order_count', 0) > 0:
            summary_parts.append(f"{equip['work_order_count']} work orders")
        if equip.get('last_reported_fault'):
            summary_parts.append(f"Last fault: {equip['last_reported_fault']}")

        return ContextMatch(
            source='equipment',
            relevance_score=score,
            title=f"{equip.get('manufacturer', '')} {equip.get('model_number', '')}".strip() or equip.get('equipment_number'),
            summary=" | ".join(summary_parts) if summary_parts else "Equipment record",
            equipment_number=equip.get('equipment_number'),
            fault_code=equip.get('last_reported_fault'),
            created_at=str(equip.get('last_work_order_at', ''))[:10] if equip.get('last_work_order_at') else None,
            status=None
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens (1 token ≈ 4 chars)."""
        return len(text) // 4

    def _format_context_for_prompt(self, matches: List[ContextMatch]) -> str:
        """Format matches as bullet points for LLM injection."""
        if not matches:
            return ""

        lines = []
        for match in matches[:3]:  # Top 3 only
            line = f"- **{match.title}** ({match.created_at or 'recent'}): {match.summary}"
            lines.append(line)

        return "\n".join(lines)

    async def get_relevant_context(
        self,
        message: str,
        intent: IntentType,
        user_id: str,
    ) -> RetrievedContext:
        """
        Retrieve relevant context for a query.

        Only retrieves context for TROUBLESHOOT and EQUIPMENT_SEARCH intents.

        Args:
            message: User's natural language message
            intent: Classified intent type
            user_id: User identifier

        Returns:
            RetrievedContext with formatted context for LLM injection
        """
        # Only retrieve context for relevant intents
        if intent not in [IntentType.TROUBLESHOOT, IntentType.EQUIPMENT_SEARCH]:
            logger.debug(f"Skipping context retrieval for intent: {intent}")
            return RetrievedContext()

        # Extract search terms from message
        equipment_terms = self._extract_equipment_terms(message)
        symptoms = self._extract_symptoms(message)
        fault_codes = self._extract_fault_codes(message)

        logger.debug(
            f"Context search | equipment={equipment_terms} | "
            f"symptoms={symptoms} | faults={fault_codes}"
        )

        # Search all sources
        all_keywords = equipment_terms + symptoms

        work_orders = await self._search_work_orders_by_keywords(
            all_keywords, user_id, limit=5
        )

        fault_matches = await self._search_work_orders_by_fault_code(
            fault_codes, user_id, limit=3
        )

        equipment = await self._search_equipment_by_keywords(
            equipment_terms, user_id, limit=3
        )

        # Deduplicate work orders (fault matches may overlap)
        seen_wos = set()
        all_work_orders = []
        for wo in fault_matches + work_orders:
            wo_num = wo.get('work_order_number')
            if wo_num and wo_num not in seen_wos:
                seen_wos.add(wo_num)
                all_work_orders.append(wo)

        # Score and convert to matches
        matches: List[ContextMatch] = []

        for wo in all_work_orders[:5]:
            score = self._score_relevance(wo, equipment_terms, symptoms, fault_codes)
            if score >= 0.4:  # Only include relevant matches
                matches.append(self._format_work_order_match(wo, score))

        for eq in equipment[:3]:
            score = 0.5  # Equipment matches are moderately relevant
            matches.append(self._format_equipment_match(eq, score))

        # Sort by relevance
        matches.sort(key=lambda m: m.relevance_score, reverse=True)

        # Format for prompt (top 3)
        formatted = self._format_context_for_prompt(matches[:3])
        tokens = self._estimate_tokens(formatted)

        # Trim if too long
        if tokens > self.MAX_CONTEXT_TOKENS:
            # Just use top 2
            formatted = self._format_context_for_prompt(matches[:2])
            tokens = self._estimate_tokens(formatted)

        has_history = len(matches) > 0 and any(m.relevance_score >= 0.5 for m in matches)

        logger.info(
            f"Context retrieved | matches={len(matches)} | "
            f"has_history={has_history} | tokens={tokens}"
        )

        return RetrievedContext(
            matches=matches,
            total_tokens_estimate=tokens,
            formatted_context=formatted,
            has_relevant_history=has_history
        )


# Module-level singleton
_retriever: Optional[ContextRetriever] = None


def get_context_retriever(db) -> ContextRetriever:
    """Get or create the context retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = ContextRetriever(db)
    return _retriever


__all__ = [
    "ContextRetriever",
    "ContextMatch",
    "RetrievedContext",
    "get_context_retriever",
]
