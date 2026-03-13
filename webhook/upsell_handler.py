"""Upsell Handler — sends upgrade interest notification to AM."""

from __future__ import annotations


import logging

from delivery.notification_email import send_upsell_am_notification
from delivery.sheets_logger import log_audit

logger = logging.getLogger(__name__)


def handle_upsell(property_data: dict, interested_tier: str) -> dict:
    """Handle upgrade interest from budget simulator."""
    property_name = property_data.get("name", "")
    current_tier = property_data.get("video_creative_package_tier", "")

    send_upsell_am_notification(property_data, interested_tier)

    log_audit(
        property_name,
        "upsell",
        "INTEREST",
        f"{current_tier} → {interested_tier}",
    )

    return {
        "status": "Upgrade interest submitted",
        "current_tier": current_tier,
        "interested_tier": interested_tier,
        "message": "Your Account Manager will reach out shortly.",
    }
