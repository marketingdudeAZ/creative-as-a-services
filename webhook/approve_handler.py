"""Approve Handler — processes approval requests from the review portal."""

import json
import logging
from datetime import datetime

from delivery.hubspot_write import update_approval_status
from delivery.notification_email import send_approved_notification
from delivery.sheets_logger import log_audit

logger = logging.getLogger(__name__)


def handle_approve(property_data: dict, variant_ids: list | str) -> dict:
    """Process approval for one, some, or all variants."""
    hs_object_id = property_data.get("hs_object_id", "")
    property_name = property_data.get("name", "")

    try:
        video_urls = json.loads(property_data.get("video_creative_latest_urls", "[]"))
    except (json.JSONDecodeError, TypeError):
        video_urls = []

    all_script_ids = {v.get("script_id") for v in video_urls}

    if variant_ids == "all" or variant_ids == ["all"]:
        # Approve all variants
        update_approval_status(
            hs_object_id,
            "Approved",
            video_creative_approved_date=datetime.now().isoformat(),
        )

        log_audit(property_name, "approval", "Approved", "All variants approved")
        send_approved_notification(property_data, video_urls)

        return {
            "status": "Approved",
            "message": f"All {len(video_urls)} variants approved",
            "approved_variants": list(all_script_ids),
        }

    # Partial approval
    approved_ids = set(variant_ids) if isinstance(variant_ids, list) else {variant_ids}

    # Check if all are now approved (including any previously approved)
    # For simplicity, track approved state based on current request
    if approved_ids >= all_script_ids:
        status = "Approved"
        update_approval_status(
            hs_object_id,
            "Approved",
            video_creative_approved_date=datetime.now().isoformat(),
        )
        send_approved_notification(property_data, video_urls)
    else:
        status = "Partial Approval"
        update_approval_status(hs_object_id, "Partial Approval")

    log_audit(
        property_name,
        "approval",
        status,
        f"Approved: {approved_ids}",
    )

    return {
        "status": status,
        "message": f"{len(approved_ids)} variant(s) approved",
        "approved_variants": list(approved_ids),
    }
