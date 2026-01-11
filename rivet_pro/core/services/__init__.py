"""Core services for Rivet Pro"""

from .ocr_service import analyze_image, analyze_image_sync
from .sme_service import route_to_sme, detect_manufacturer
from .equipment_taxonomy import (
    identify_component,
    extract_fault_code,
    extract_model_number,
    identify_issue_type,
    identify_urgency,
)
from .usage_service import UsageService, FREE_TIER_LIMIT
from .stripe_service import StripeService, send_telegram_confirmation

__all__ = [
    # OCR
    "analyze_image",
    "analyze_image_sync",
    # SME Router
    "route_to_sme",
    "detect_manufacturer",
    # Equipment Taxonomy
    "identify_component",
    "extract_fault_code",
    "extract_model_number",
    "identify_issue_type",
    "identify_urgency",
    # Usage Tracking
    "UsageService",
    "FREE_TIER_LIMIT",
    # Stripe Payments
    "StripeService",
    "send_telegram_confirmation",
]
