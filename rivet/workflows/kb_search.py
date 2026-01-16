"""
KB Search - Route A: Knowledge Base Vector Search

Production implementation using pgvector for semantic search.
Implements confidence-based routing per rivet_pro_skill_ai_routing.md.

Route A (LOOKUP): Confidence >0.8 → Direct answer from KB
Route B (SME): Confidence 0.7-0.8 → Fallback to vendor SME
Route C (RESEARCH): Confidence 0.4-0.7 → Log knowledge gap
Route D (CLARIFY): Confidence <0.4 → Ask clarifying questions
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from rivet.models.ocr import OCRResult
from rivet.models.knowledge import KnowledgeAtom, KnowledgeSearchResult, AtomType
from rivet.services.knowledge_service import KnowledgeService
from rivet.services.embedding_service import EmbeddingService
from rivet.atlas.database import AtlasDatabase
from rivet.integrations.llm import LLMRouter  # For answer synthesis

logger = logging.getLogger(__name__)


# Initialize services (singleton pattern for performance)
_embedding_service = None
_knowledge_service = None
_llm_router = None


def get_embedding_service() -> EmbeddingService:
    """Get or create EmbeddingService singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_knowledge_service() -> KnowledgeService:
    """Get or create KnowledgeService singleton."""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService(AtlasDatabase())
    return _knowledge_service


def get_llm_router() -> LLMRouter:
    """Get or create LLMRouter singleton."""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


async def search_knowledge_base(
    query: str,
    ocr_result: Optional[OCRResult] = None,
) -> Dict[str, Any]:
    """
    Search knowledge base for answer to query using vector search.

    Implementation:
    1. Generate query embedding
    2. Vector search with manufacturer/model filters
    3. Calculate confidence with boosts
    4. Synthesize answer from top atoms
    5. Extract safety warnings
    6. Track usage statistics

    Args:
        query: User's troubleshooting question
        ocr_result: Optional equipment data from OCR

    Returns:
        Dict with:
            - answer: str (synthesized answer or None if low confidence)
            - confidence: float (0.0-1.0, with boosts applied)
            - sources: list (knowledge atom IDs)
            - safety_warnings: list
            - llm_calls: int
            - cost_usd: float
            - route_recommendation: str (for orchestrator decision)

    Example:
        >>> result = await search_knowledge_base(
        ...     "F0002 fault code",
        ...     ocr_result=OCRResult(manufacturer="Siemens", model_number="G120C")
        ... )
        >>> if result["confidence"] >= 0.85:
        ...     return result["answer"]  # High confidence → direct answer
    """
    logger.info(f"[KB Search] Query: {query[:100]}...")

    embedding_service = get_embedding_service()
    knowledge_service = get_knowledge_service()

    # Step 1: Generate query embedding
    try:
        query_embedding = await embedding_service.generate_query_embedding(query)
        logger.debug(f"[KB Search] Generated query embedding ({len(query_embedding)} dims)")
    except Exception as e:
        logger.error(f"[KB Search] Failed to generate embedding: {e}")
        return {
            "answer": None,
            "confidence": 0.0,
            "sources": [],
            "safety_warnings": [],
            "llm_calls": 0,
            "cost_usd": 0.0,
            "route_recommendation": "sme",  # Fallback to SME on embedding failure
            "error": str(e)
        }

    # Step 2: Vector search with optional filters
    manufacturer = ocr_result.manufacturer if ocr_result else None
    equipment_type = ocr_result.equipment_type if ocr_result else None

    try:
        search_results = await knowledge_service.vector_search(
            query_embedding=query_embedding,
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            min_confidence=0.3,  # Filter out very low-confidence atoms
            limit=5
        )
        logger.info(f"[KB Search] Found {len(search_results)} candidate atoms")
    except Exception as e:
        logger.error(f"[KB Search] Vector search failed: {e}")
        return {
            "answer": None,
            "confidence": 0.0,
            "sources": [],
            "safety_warnings": [],
            "llm_calls": 0,
            "cost_usd": 0.0,
            "route_recommendation": "sme",
            "error": str(e)
        }

    # If no results, return low confidence
    if not search_results:
        logger.info("[KB Search] No matching atoms found")
        return {
            "answer": None,
            "confidence": 0.0,
            "sources": [],
            "safety_warnings": [],
            "llm_calls": 0,
            "cost_usd": 0.0,
            "route_recommendation": "research"  # Trigger research for knowledge gap
        }

    # Step 3: Calculate confidence with boosts
    enriched_results = []
    for result in search_results:
        atom = KnowledgeAtom(**result)
        final_confidence = calculate_confidence(atom, ocr_result)

        enriched_results.append(KnowledgeSearchResult(
            atom=atom,
            final_confidence=final_confidence,
            boosts_applied=_get_boosts_metadata(atom, ocr_result)
        ))

    # Sort by final confidence
    enriched_results.sort(key=lambda x: x.final_confidence, reverse=True)
    max_confidence = enriched_results[0].final_confidence

    logger.info(
        f"[KB Search] Top confidence: {max_confidence:.2f} "
        f"(atom: {enriched_results[0].atom.title[:50]})"
    )

    # Step 4: Determine routing recommendation
    route = _determine_route(max_confidence)

    # If confidence too low, don't synthesize answer
    if max_confidence < 0.4:
        return {
            "answer": None,
            "confidence": max_confidence,
            "sources": [str(r.atom.atom_id) for r in enriched_results],
            "safety_warnings": [],
            "llm_calls": 0,
            "cost_usd": 0.0,
            "route_recommendation": route
        }

    # Step 5: Synthesize answer from top atoms
    try:
        synthesis_result = await synthesize_answer(
            query=query,
            search_results=enriched_results[:3],  # Use top 3 atoms
            ocr_result=ocr_result
        )
    except Exception as e:
        logger.error(f"[KB Search] Answer synthesis failed: {e}")
        synthesis_result = {
            "answer": None,
            "llm_calls": 0,
            "cost_usd": 0.0
        }

    # Step 6: Extract safety warnings
    safety_warnings = extract_safety_warnings(enriched_results[:3])

    # Step 7: Track usage statistics (increment usage_count for top atom)
    try:
        await knowledge_service.increment_usage(enriched_results[0].atom.atom_id)
    except Exception as e:
        logger.warning(f"[KB Search] Failed to increment usage: {e}")

    result = {
        "answer": synthesis_result.get("answer"),
        "confidence": max_confidence,
        "sources": [str(r.atom.atom_id) for r in enriched_results],
        "safety_warnings": safety_warnings,
        "llm_calls": synthesis_result.get("llm_calls", 0),
        "cost_usd": synthesis_result.get("cost_usd", 0.0),
        "route_recommendation": route
    }

    logger.info(
        f"[KB Search] Complete: confidence={max_confidence:.0%}, "
        f"route={route}, llm_calls={result['llm_calls']}"
    )

    return result


def calculate_confidence(
    atom: KnowledgeAtom,
    ocr_result: Optional[OCRResult]
) -> float:
    """
    Calculate final confidence with manufacturer/model/verification boosts.

    Following spec from rivet_pro_skill_ai_routing.md:
    - Base: similarity_score from vector search (0-1)
    - +0.10: Exact manufacturer match
    - +0.15: Exact model match
    - +0.10: Human verified
    - -0.10: Old atom (>2 years since last verification)

    Args:
        atom: Knowledge atom from search
        ocr_result: Optional OCR context for boosts

    Returns:
        Final confidence score (0.0-1.0, capped)
    """
    # Start with base similarity score
    score = atom.similarity_score or 0.0

    # Boost for exact manufacturer match
    if ocr_result and ocr_result.manufacturer and atom.manufacturer:
        if ocr_result.manufacturer.lower() == atom.manufacturer.lower():
            score += 0.10
            logger.debug(f"[Confidence] +0.10 manufacturer boost ({atom.manufacturer})")

    # Boost for exact model match
    if ocr_result and ocr_result.model_number and atom.model:
        if ocr_result.model_number.lower() == atom.model.lower():
            score += 0.15
            logger.debug(f"[Confidence] +0.15 model boost ({atom.model})")

    # Boost for human verification
    if atom.human_verified:
        score += 0.10
        logger.debug("[Confidence] +0.10 human verified boost")

    # Penalty for old atoms (>2 years)
    age_days = (datetime.now() - atom.last_verified).days
    if age_days > 730:
        score -= 0.10
        logger.debug(f"[Confidence] -0.10 age penalty ({age_days} days old)")

    # Cap at 1.0
    final_score = min(score, 1.0)
    logger.debug(f"[Confidence] Final: {final_score:.2f}")

    return round(final_score, 3)


def _get_boosts_metadata(atom: KnowledgeAtom, ocr_result: Optional[OCRResult]) -> dict:
    """Get metadata about which boosts were applied."""
    boosts = {}

    if ocr_result and ocr_result.manufacturer and atom.manufacturer:
        if ocr_result.manufacturer.lower() == atom.manufacturer.lower():
            boosts["manufacturer_match"] = True

    if ocr_result and ocr_result.model_number and atom.model:
        if ocr_result.model_number.lower() == atom.model.lower():
            boosts["model_match"] = True

    if atom.human_verified:
        boosts["human_verified"] = True

    age_days = (datetime.now() - atom.last_verified).days
    if age_days > 730:
        boosts["age_penalty"] = age_days

    return boosts


def _determine_route(confidence: float) -> str:
    """
    Determine routing recommendation based on confidence.

    Thresholds per rivet_pro_skill_ai_routing.md:
    - ≥0.85: kb (direct answer)
    - 0.70-0.85: sme (fallback to vendor SME)
    - 0.40-0.70: research (log knowledge gap)
    - <0.40: clarify (ask user for more info)
    """
    if confidence >= 0.85:
        return "kb"
    elif confidence >= 0.70:
        return "sme"
    elif confidence >= 0.40:
        return "research"
    else:
        return "clarify"


async def synthesize_answer(
    query: str,
    search_results: List[KnowledgeSearchResult],
    ocr_result: Optional[OCRResult]
) -> Dict[str, Any]:
    """
    Synthesize answer from top knowledge atoms using LLM.

    Args:
        query: User's question
        search_results: Top matching atoms with confidence
        ocr_result: Optional equipment context

    Returns:
        Dict with answer, llm_calls, cost_usd
    """
    llm_router = get_llm_router()

    # Format atoms as context
    context_parts = []
    for i, result in enumerate(search_results, 1):
        atom = result.atom
        context_parts.append(
            f"Source {i} (confidence: {result.final_confidence:.0%}):\n"
            f"Title: {atom.title}\n"
            f"Content: {atom.content}\n"
            f"Type: {atom.type}\n"
        )

    knowledge_context = "\n---\n".join(context_parts)

    # Build synthesis prompt
    equipment_context = ""
    if ocr_result and ocr_result.manufacturer:
        equipment_context = f"\nEquipment: {ocr_result.manufacturer} {ocr_result.model_number or ''}"

    prompt = f"""You are a technical support expert. Answer the user's question using ONLY the knowledge sources provided below.

User Question: {query}{equipment_context}

Knowledge Base Sources:
{knowledge_context}

Instructions:
- Provide a clear, actionable answer based on the sources
- If sources mention safety warnings, include them prominently
- Cite source numbers in your answer (e.g., "According to Source 1...")
- If sources don't fully answer the question, say so
- Keep answer concise (2-3 paragraphs max)

Answer:"""

    try:
        # Use LLMRouter for cost-optimized LLM selection
        response = await llm_router.route_and_call(
            prompt=prompt,
            max_tokens=500,
            temperature=0.3  # Lower temperature for factual answers
        )

        return {
            "answer": response.get("content", "").strip(),
            "llm_calls": 1,
            "cost_usd": response.get("cost_usd", 0.0)
        }

    except Exception as e:
        logger.error(f"[KB Search] LLM synthesis failed: {e}")
        # Fallback: Return first atom content directly
        return {
            "answer": search_results[0].atom.content if search_results else None,
            "llm_calls": 0,
            "cost_usd": 0.0
        }


def extract_safety_warnings(search_results: List[KnowledgeSearchResult]) -> List[str]:
    """
    Extract safety warnings from knowledge atoms.

    Args:
        search_results: List of search results

    Returns:
        List of safety warning strings
    """
    warnings = []

    for result in search_results:
        atom = result.atom

        # Include all SAFETY type atoms
        if atom.type == AtomType.SAFETY:
            warnings.append(atom.content)

        # Scan content for safety keywords
        safety_keywords = [
            "danger", "warning", "caution", "hazard",
            "electric shock", "high voltage", "lockout",
            "safety", "do not", "never"
        ]

        content_lower = atom.content.lower()
        for keyword in safety_keywords:
            if keyword in content_lower:
                # Extract sentence containing keyword
                sentences = atom.content.split(". ")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        warnings.append(sentence.strip())
                break  # Only add one warning per atom

    # Deduplicate
    return list(set(warnings))
