"""Revision Handler — processes feedback and triggers re-generation."""

from __future__ import annotations


import json
import logging
from datetime import datetime

from config import MAX_REVISIONS_PER_MONTH
from delivery.hubspot_write import (
    increment_revision_count,
    append_feedback_log,
    update_revised_variant,
)
from delivery.notification_email import send_revision_notification
from delivery.sheets_logger import log_audit, log_error
from phases.script_engine import run as run_script_engine
from phases.video_generator import generate_single_video

logger = logging.getLogger(__name__)


def handle_revision(property_data: dict, feedback: dict) -> tuple[dict, int]:
    """Process a revision request: re-gen script + video for a single variant."""
    property_name = property_data.get("name", "")
    current_count = int(property_data.get("video_creative_revision_count") or 0)

    # Check revision limit
    if current_count >= MAX_REVISIONS_PER_MONTH:
        return {
            "error": "Monthly revision limit reached",
            "revision_count": current_count,
            "max_revisions": MAX_REVISIONS_PER_MONTH,
            "message": "Please contact your Account Manager for additional revisions.",
        }, 429

    variant_script_id = feedback.get("variant_script_id", "")

    # Find the original script
    try:
        current_scripts = json.loads(property_data.get("video_creative_scripts_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        current_scripts = []

    original_script = None
    for s in current_scripts:
        if s.get("script_id") == variant_script_id:
            original_script = s
            break

    if not original_script:
        return {"error": f"Script {variant_script_id} not found"}, 404

    # Build revision context
    revision_context = {
        "variant_script_id": variant_script_id,
        "tone_shift": feedback.get("tone_shift"),
        "emphasis_shift": feedback.get("emphasis_shift"),
        "photo_emphasis": feedback.get("photo_emphasis"),
        "cta_change": feedback.get("cta_change"),
        "free_text_notes": feedback.get("free_text_notes", ""),
        "original_script": original_script,
    }

    # Increment revision count
    new_count = increment_revision_count(property_data)

    # Log feedback
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "variant": variant_script_id,
        "changes": {
            k: v for k, v in revision_context.items()
            if k != "original_script" and v
        },
        "notes": feedback.get("free_text_notes", ""),
    }
    append_feedback_log(property_data, feedback_entry)

    # Re-run script engine with revision context
    ai_output = run_script_engine(
        property_data,
        revision_context=revision_context,
    )

    if not ai_output or not ai_output.get("scripts"):
        log_error(property_name, "revision", "SCRIPT_FAILED", f"Revision failed for {variant_script_id}")
        return {
            "error": "Revision generation failed",
            "message": "Your account manager has been notified.",
        }, 500

    revised_script = ai_output["scripts"][0]
    new_rationale = ai_output.get("rationale", "")

    # Re-generate video for revised script
    video_result = generate_single_video(
        revised_script,
        property_data.get("website") or property_data.get("domain", ""),
        property_data,
    )

    if not video_result:
        log_error(property_name, "revision", "VIDEO_FAILED", f"Video re-gen failed for {variant_script_id}")
        return {
            "error": "Video generation failed",
            "message": "Your account manager has been notified.",
        }, 500

    # Update HubSpot with revised variant
    update_revised_variant(property_data, revised_script, video_result, new_rationale)

    # Send notification
    send_revision_notification(property_data)

    log_audit(property_name, "revision", "COMPLETE", f"Revised {variant_script_id} (rev {new_count})")

    return {
        "status": "Revision complete",
        "variant_script_id": variant_script_id,
        "revision_count": new_count,
        "max_revisions": MAX_REVISIONS_PER_MONTH,
        "new_video_url": video_result.get("url"),
    }, 200
