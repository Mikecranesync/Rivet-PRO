"""
Confidence Scoring and Upsell Triggers for RIVET Pro

Evaluates answer quality and determines when to trigger premium upgrades.

Features:
- Multi-factor confidence scoring (0.0-1.0)
- Quality gates (auto-respond, suggest upgrade, require expert)
- Upsell trigger logic (question limits, low confidence, complex issues)
- Revenue optimization (maximize conversions without annoying users)

Example:
    >>> scorer = ConfidenceScorer()
    >>> quality = scorer.score_answer(
    ...     question="Motor running hot",
    ...     matched_atoms=[atom1, atom2],
    ...     user_tier="free"
    ... )
    >>> if quality.should_upsell:
    ...     print(quality.upsell_message)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class AnswerAction(Enum):
    """Recommended actions based on confidence score"""
    AUTO_RESPOND = "auto_respond"  # High confidence, send answer
    SUGGEST_UPGRADE = "suggest_upgrade"  # Medium confidence, answer + upsell
    REQUIRE_EXPERT = "require_expert"  # Low confidence, expert call required
    BLOCK_FREE_TIER = "block_free_tier"  # Question limit reached


@dataclass
class AnswerQuality:
    """
    Answer quality assessment with upsell logic.

    Combines multiple confidence factors to determine answer quality
    and appropriate monetization triggers.
    """
    # Confidence scores
    overall_confidence: float  # 0.0-1.0 (weighted average)
    semantic_similarity: float  # How well atoms match question
    atom_count: int  # Number of matched atoms
    atom_quality: float  # Average quality of matched atoms
    coverage: float  # How well atoms cover all aspects of question

    # Quality assessment
    answer_action: AnswerAction
    is_safe_to_auto_respond: bool

    # Upsell logic
    should_upsell: bool
    upsell_trigger: Optional[str] = None  # question_limit, low_confidence, complex_issue
    upsell_message: Optional[str] = None
    suggested_tier: Optional[str] = None  # pro, premium_call, enterprise

    # Context
    user_tier: str = "free"
    questions_today: int = 0
    daily_limit: int = 5

    # Metadata
    factors: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/analytics"""
        return {
            "overall_confidence": self.overall_confidence,
            "semantic_similarity": self.semantic_similarity,
            "atom_count": self.atom_count,
            "atom_quality": self.atom_quality,
            "coverage": self.coverage,
            "answer_action": self.answer_action.value,
            "is_safe_to_auto_respond": self.is_safe_to_auto_respond,
            "should_upsell": self.should_upsell,
            "upsell_trigger": self.upsell_trigger,
            "suggested_tier": self.suggested_tier,
            "user_tier": self.user_tier,
        }


class ConfidenceScorer:
    """
    Scores answer confidence and determines upsell triggers.

    Multi-factor scoring considers:
    1. Semantic similarity (vector search scores)
    2. Atom count (more matches = higher confidence)
    3. Atom quality (human-verified atoms score higher)
    4. Coverage (do atoms answer all parts of question?)
    5. User tier (context for upsell logic)
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.75  # Auto-respond
    MEDIUM_CONFIDENCE = 0.50  # Answer + suggest upgrade
    LOW_CONFIDENCE = 0.50  # Require expert (block auto-response)

    # Weights for overall confidence calculation
    WEIGHTS = {
        "semantic_similarity": 0.40,
        "atom_count_score": 0.20,
        "atom_quality": 0.25,
        "coverage": 0.15,
    }

    def __init__(self):
        """Initialize confidence scorer"""
        pass

    def score_answer(
        self,
        question: str,
        matched_atoms: List[Dict[str, Any]],
        user_tier: str = "free",
        questions_today: int = 0,
        daily_limit: int = 5,
        intent_data: Optional[Dict[str, Any]] = None,
    ) -> AnswerQuality:
        """
        Score answer quality and determine upsell triggers.

        Args:
            question: User's troubleshooting question
            matched_atoms: Knowledge atoms retrieved from KB
            user_tier: User's subscription tier (free, pro, enterprise)
            questions_today: Number of questions asked today
            daily_limit: Daily question limit for tier
            intent_data: Optional intent detection results

        Returns:
            AnswerQuality with confidence scores and upsell logic
        """
        # Calculate individual confidence factors
        semantic_similarity = self._calc_semantic_similarity(matched_atoms)
        atom_count = len(matched_atoms)
        atom_count_score = self._calc_atom_count_score(atom_count)
        atom_quality = self._calc_atom_quality(matched_atoms)
        coverage = self._calc_coverage(question, matched_atoms, intent_data)

        # Calculate overall confidence (weighted average)
        overall_confidence = (
            semantic_similarity * self.WEIGHTS["semantic_similarity"]
            + atom_count_score * self.WEIGHTS["atom_count_score"]
            + atom_quality * self.WEIGHTS["atom_quality"]
            + coverage * self.WEIGHTS["coverage"]
        )

        # Determine answer action
        answer_action = self._determine_action(overall_confidence, user_tier, questions_today, daily_limit)

        # Check if safe to auto-respond
        is_safe_to_auto_respond = (
            answer_action == AnswerAction.AUTO_RESPOND
            and overall_confidence >= self.HIGH_CONFIDENCE
        )

        # Determine upsell logic
        upsell_result = self._determine_upsell(
            overall_confidence=overall_confidence,
            user_tier=user_tier,
            questions_today=questions_today,
            daily_limit=daily_limit,
            atom_count=atom_count,
            intent_data=intent_data,
        )

        return AnswerQuality(
            overall_confidence=overall_confidence,
            semantic_similarity=semantic_similarity,
            atom_count=atom_count,
            atom_quality=atom_quality,
            coverage=coverage,
            answer_action=answer_action,
            is_safe_to_auto_respond=is_safe_to_auto_respond,
            should_upsell=upsell_result["should_upsell"],
            upsell_trigger=upsell_result.get("trigger"),
            upsell_message=upsell_result.get("message"),
            suggested_tier=upsell_result.get("suggested_tier"),
            user_tier=user_tier,
            questions_today=questions_today,
            daily_limit=daily_limit,
            factors={
                "semantic_similarity": semantic_similarity,
                "atom_count_score": atom_count_score,
                "atom_quality": atom_quality,
                "coverage": coverage,
            },
        )

    def _calc_semantic_similarity(self, matched_atoms: List[Dict[str, Any]]) -> float:
        """
        Calculate semantic similarity score from matched atoms.

        Uses vector search similarity scores (0.0-1.0).
        """
        if not matched_atoms:
            return 0.0

        # Get top 3 atoms' similarity scores
        similarities = []
        for atom in matched_atoms[:3]:
            # Assume atoms have 'similarity' field from vector search
            similarity = atom.get("similarity", 0.0)
            similarities.append(similarity)

        # Weighted average (top match counts more)
        if len(similarities) == 1:
            return similarities[0]
        elif len(similarities) == 2:
            return similarities[0] * 0.7 + similarities[1] * 0.3
        else:  # 3 or more
            return similarities[0] * 0.5 + similarities[1] * 0.3 + similarities[2] * 0.2

    def _calc_atom_count_score(self, atom_count: int) -> float:
        """
        Score based on number of matched atoms.

        More matches generally means better coverage, but diminishing returns.
        """
        if atom_count == 0:
            return 0.0
        elif atom_count == 1:
            return 0.5
        elif atom_count == 2:
            return 0.7
        elif atom_count >= 3 and atom_count <= 5:
            return 0.9
        else:  # 6+
            return 1.0

    def _calc_atom_quality(self, matched_atoms: List[Dict[str, Any]]) -> float:
        """
        Calculate average quality of matched atoms.

        Factors:
        - Human-verified atoms score higher
        - Atoms with citations score higher
        - Recent atoms score higher
        """
        if not matched_atoms:
            return 0.0

        quality_scores = []

        for atom in matched_atoms:
            quality = 0.5  # Base quality

            # Boost for human verification
            if atom.get("human_verified", False):
                quality += 0.2

            # Boost for citations
            if atom.get("citations") and len(atom.get("citations", [])) > 0:
                quality += 0.15

            # Boost for source credibility
            source_url = atom.get("source_url", "")
            if any(domain in source_url for domain in ["oem", "manufacturer", "manual"]):
                quality += 0.15

            quality_scores.append(min(1.0, quality))

        return sum(quality_scores) / len(quality_scores)

    def _calc_coverage(
        self,
        question: str,
        matched_atoms: List[Dict[str, Any]],
        intent_data: Optional[Dict[str, Any]],
    ) -> float:
        """
        Estimate how well atoms cover all aspects of question.

        Analyzes whether atoms address:
        - Equipment type mentioned
        - Fault codes mentioned
        - Symptoms mentioned
        """
        if not matched_atoms:
            return 0.0

        coverage_score = 0.5  # Base coverage

        # Check if intent data available
        if not intent_data:
            return coverage_score

        equipment_info = intent_data.get("equipment_info", {})

        # Check equipment type coverage
        equipment_type = equipment_info.get("equipment_type")
        if equipment_type:
            for atom in matched_atoms:
                atom_equipment = atom.get("equipment_type") or atom.get("atom_type")
                if atom_equipment and equipment_type in str(atom_equipment).lower():
                    coverage_score += 0.15
                    break

        # Check fault code coverage
        fault_codes = equipment_info.get("fault_codes", [])
        if fault_codes:
            for atom in matched_atoms:
                atom_codes = atom.get("code") or atom.get("fault_codes", [])
                if any(code in str(atom_codes) for code in fault_codes):
                    coverage_score += 0.20
                    break

        # Check symptom coverage
        symptoms = equipment_info.get("symptoms", [])
        if symptoms:
            for atom in matched_atoms:
                atom_symptoms = atom.get("symptoms", [])
                if any(symptom in atom_symptoms for symptom in symptoms):
                    coverage_score += 0.15
                    break

        return min(1.0, coverage_score)

    def _determine_action(
        self,
        confidence: float,
        user_tier: str,
        questions_today: int,
        daily_limit: int,
    ) -> AnswerAction:
        """
        Determine recommended action based on confidence and user tier.
        """
        # Free tier: Check question limit first
        if user_tier == "free" and questions_today >= daily_limit:
            return AnswerAction.BLOCK_FREE_TIER

        # High confidence: Auto-respond
        if confidence >= self.HIGH_CONFIDENCE:
            return AnswerAction.AUTO_RESPOND

        # Medium confidence: Suggest upgrade (but still provide answer)
        if confidence >= self.MEDIUM_CONFIDENCE:
            return AnswerAction.SUGGEST_UPGRADE

        # Low confidence: Require expert
        return AnswerAction.REQUIRE_EXPERT

    def _determine_upsell(
        self,
        overall_confidence: float,
        user_tier: str,
        questions_today: int,
        daily_limit: int,
        atom_count: int,
        intent_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Determine if and how to trigger upsell.

        Returns:
            {
                "should_upsell": bool,
                "trigger": str,  # question_limit, low_confidence, complex_issue
                "message": str,  # Upsell message to show user
                "suggested_tier": str  # pro, premium_call, enterprise
            }
        """
        # Pro/Enterprise users: No upsells (they already pay)
        if user_tier in ["pro", "enterprise"]:
            return {"should_upsell": False}

        # Trigger 1: Question limit reached (FREE tier only)
        if user_tier == "free" and questions_today >= daily_limit:
            return {
                "should_upsell": True,
                "trigger": "question_limit",
                "message": (
                    f"🚫 You've reached your daily limit ({daily_limit} questions/day)\n\n"
                    "💼 **Upgrade to Pro** for unlimited questions:\n"
                    "• Unlimited Q&A every day\n"
                    "• Priority support\n"
                    "• Image analysis (Field Eye)\n"
                    "• Export reports (PDF)\n\n"
                    "**Only $29/month**"
                ),
                "suggested_tier": "pro",
            }

        # Trigger 2: Low confidence answer (< 0.60)
        if overall_confidence < 0.60:
            if overall_confidence < 0.40:
                # Very low confidence: Suggest expert call
                return {
                    "should_upsell": True,
                    "trigger": "very_low_confidence",
                    "message": (
                        "⚠️ **This is a complex issue**\n\n"
                        "My confidence is low for this troubleshooting scenario.\n"
                        "I recommend speaking with a live expert.\n\n"
                        "📞 **Book Expert Call** - $75/hour\n"
                        "• Real-time video support\n"
                        "• 30-60 minute sessions\n"
                        "• Post-call summary report\n\n"
                        "[Book Now] [Continue with AI Answer]"
                    ),
                    "suggested_tier": "premium_call",
                }
            else:
                # Medium-low confidence: Suggest Pro upgrade
                return {
                    "should_upsell": True,
                    "trigger": "low_confidence",
                    "message": (
                        "💡 **Partial Match Found**\n\n"
                        "I found some related information, but it's not a perfect match.\n\n"
                        "For better answers, consider:\n"
                        "• **Pro Tier** ($29/mo) - Priority support + unlimited questions\n"
                        "• **Expert Call** ($75/hr) - Live troubleshooting\n\n"
                        "[Upgrade] [Continue]"
                    ),
                    "suggested_tier": "pro",
                }

        # Trigger 3: Complex issue (urgency >= 8 or multiple fault codes)
        if intent_data:
            urgency_score = intent_data.get("urgency_score", 0)
            fault_codes = intent_data.get("equipment_info", {}).get("fault_codes", [])

            if urgency_score >= 8 or len(fault_codes) >= 3:
                return {
                    "should_upsell": True,
                    "trigger": "complex_issue",
                    "message": (
                        "🚨 **Critical Issue Detected**\n\n"
                        "This appears to be a complex troubleshooting scenario.\n\n"
                        "📞 **Expert Call Recommended** - $75/hour\n"
                        "• Immediate expert assistance\n"
                        "• Real-time guidance\n"
                        "• Faster resolution\n\n"
                        "[Book Expert] [Continue with AI]"
                    ),
                    "suggested_tier": "premium_call",
                }

        # Trigger 4: Near question limit (FREE tier, 4/5 questions used)
        if user_tier == "free" and questions_today == daily_limit - 1:
            return {
                "should_upsell": True,
                "trigger": "near_limit",
                "message": (
                    "ℹ️ **Last Free Question Today**\n\n"
                    "You have 1 question remaining today.\n\n"
                    "Upgrade to **Pro** for unlimited questions:\n"
                    "• Ask as many questions as you need\n"
                    "• Priority support\n"
                    "• Image analysis\n\n"
                    "**$29/month** - Cancel anytime\n\n"
                    "[Upgrade Now]"
                ),
                "suggested_tier": "pro",
            }

        # No upsell triggers
        return {"should_upsell": False}


# Example usage
if __name__ == "__main__":
    # Test confidence scoring
    scorer = ConfidenceScorer()

    # Mock matched atoms
    mock_atoms = [
        {
            "similarity": 0.92,
            "equipment_type": "motor",
            "human_verified": True,
            "citations": ["https://oem-manual.com"],
            "symptoms": ["overheating"],
        },
        {
            "similarity": 0.85,
            "equipment_type": "motor",
            "human_verified": False,
            "symptoms": ["tripping"],
        },
    ]

    # Test case 1: High confidence, free user
    quality = scorer.score_answer(
        question="Motor running hot and tripping",
        matched_atoms=mock_atoms,
        user_tier="free",
        questions_today=2,
        daily_limit=5,
    )

    print("Test Case 1: High Confidence, Free User")
    print(f"Overall Confidence: {quality.overall_confidence:.2f}")
    print(f"Action: {quality.answer_action.value}")
    print(f"Should Upsell: {quality.should_upsell}")
    print("-" * 60)

    # Test case 2: Low confidence, requires expert
    quality = scorer.score_answer(
        question="Strange VFD fault E999 never seen before",
        matched_atoms=[],  # No matches
        user_tier="free",
        questions_today=1,
        daily_limit=5,
    )

    print("\nTest Case 2: Low Confidence, No Matches")
    print(f"Overall Confidence: {quality.overall_confidence:.2f}")
    print(f"Action: {quality.answer_action.value}")
    print(f"Should Upsell: {quality.should_upsell}")
    if quality.should_upsell:
        print(f"Upsell Message:\n{quality.upsell_message}")
    print("-" * 60)

    # Test case 3: Question limit reached
    quality = scorer.score_answer(
        question="How do I check motor bearings?",
        matched_atoms=mock_atoms,
        user_tier="free",
        questions_today=5,  # Limit reached
        daily_limit=5,
    )

    print("\nTest Case 3: Question Limit Reached")
    print(f"Action: {quality.answer_action.value}")
    print(f"Should Upsell: {quality.should_upsell}")
    if quality.should_upsell:
        print(f"Trigger: {quality.upsell_trigger}")
        print(f"Message:\n{quality.upsell_message}")
