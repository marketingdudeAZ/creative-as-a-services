"""Webhook Server — Flask app handling approval, revision, and upsell endpoints."""

from __future__ import annotations


import logging
import os
import sys

from flask import Flask, jsonify, request

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webhook.approve_handler import handle_approve
from webhook.revision_handler import handle_revision
from webhook.upsell_handler import handle_upsell
from delivery.notification_email import generate_hmac_token
from delivery.hubspot_write import find_company_by_uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def validate_token(uuid: str, month: str, token: str) -> bool:
    """Validate HMAC token against UUID + month."""
    expected = generate_hmac_token(uuid, month)
    return token == expected


@app.route("/api/approve", methods=["POST"])
def approve():
    """Approve one or all video variants."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    uuid = data.get("uuid", "")
    month = data.get("month", "")
    token = data.get("token", "")
    variant_ids = data.get("variant_ids", [])

    if not validate_token(uuid, month, token):
        return jsonify({"error": "Invalid or expired token"}), 403

    property_data = find_company_by_uuid(uuid)
    if not property_data:
        return jsonify({"error": "Property not found"}), 404

    result = handle_approve(property_data, variant_ids)
    return jsonify(result), 200


@app.route("/api/revision", methods=["POST"])
def revision():
    """Submit structured feedback for a variant revision."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    uuid = data.get("uuid", "")
    month = data.get("month", "")
    token = data.get("token", "")

    if not validate_token(uuid, month, token):
        return jsonify({"error": "Invalid or expired token"}), 403

    property_data = find_company_by_uuid(uuid)
    if not property_data:
        return jsonify({"error": "Property not found"}), 404

    result, status_code = handle_revision(property_data, data)
    return jsonify(result), status_code


@app.route("/api/status/<uuid>/<month>", methods=["GET"])
def status(uuid, month):
    """Return current approval status + video URLs for portal page load."""
    token = request.args.get("token", "")

    if not validate_token(uuid, month, token):
        return jsonify({"error": "Invalid or expired token"}), 403

    property_data = find_company_by_uuid(uuid)
    if not property_data:
        return jsonify({"error": "Property not found"}), 404

    import json

    try:
        video_urls = json.loads(property_data.get("video_creative_latest_urls", "[]"))
    except (json.JSONDecodeError, TypeError):
        video_urls = []

    try:
        scripts = json.loads(property_data.get("video_creative_scripts_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        scripts = []

    try:
        performance = json.loads(property_data.get("video_creative_performance_snapshot", "{}"))
    except (json.JSONDecodeError, TypeError):
        performance = {}

    try:
        feedback_log = json.loads(property_data.get("video_creative_feedback_log", "[]"))
    except (json.JSONDecodeError, TypeError):
        feedback_log = []

    return jsonify({
        "property_name": property_data.get("name", ""),
        "package_tier": property_data.get("video_creative_package_tier", ""),
        "approval_status": property_data.get("video_creative_approval_status", ""),
        "rationale": property_data.get("video_creative_rationale", ""),
        "video_urls": video_urls,
        "scripts": scripts,
        "revision_count": int(property_data.get("video_creative_revision_count") or 0),
        "max_revisions": 5,
        "performance_snapshot": performance,
        "feedback_log": feedback_log,
    }), 200


@app.route("/api/upsell", methods=["POST"])
def upsell():
    """Handle upgrade interest from budget simulator."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    uuid = data.get("uuid", "")
    token = data.get("token", "")
    month = data.get("month", "")

    if not validate_token(uuid, month, token):
        return jsonify({"error": "Invalid or expired token"}), 403

    property_data = find_company_by_uuid(uuid)
    if not property_data:
        return jsonify({"error": "Property not found"}), 404

    result = handle_upsell(property_data, data.get("interested_tier", ""))
    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
