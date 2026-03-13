"""Notification Email — sends review portal links and revision notifications via SMTP."""

from __future__ import annotations


import hashlib
import hmac
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, PORTAL_BASE_URL, WEBHOOK_SECRET

logger = logging.getLogger(__name__)

# Jinja2 template environment — resolve relative to this file
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
template_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


def generate_hmac_token(uuid: str, month: str) -> str:
    """Generate HMAC-SHA256 token for portal URL authentication."""
    message = f"{uuid}{month}"
    return hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_portal_url(uuid: str, month: str) -> str:
    """Build the full review portal URL with HMAC token."""
    token = generate_hmac_token(uuid, month)
    return f"{PORTAL_BASE_URL}/creative-review/{uuid}/{month}?token={token}"


def send_email(to_email: str, subject: str, html_body: str, retry: bool = True) -> bool:
    """Send an HTML email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception as e:
        if retry:
            logger.warning("Email send failed (%s), retrying...", e)
            return send_email(to_email, subject, html_body, retry=False)
        logger.error("Email send failed after retry: %s", e)
        return False


def send_new_creative_notification(property_data: dict, variant_count: int) -> bool:
    """Send notification that new creative is ready for review."""
    to_email = property_data.get("video_creative_client_email", "")
    if not to_email:
        logger.warning("No client email for %s — skipping notification", property_data.get("name"))
        return False

    uuid = property_data.get("uuid", "")
    month = datetime.now().strftime("%Y%m")
    portal_url = build_portal_url(uuid, month)
    tier = property_data.get("video_creative_package_tier", "Starter")

    template = template_env.get_template("notification_email.html")
    html_body = template.render(
        property_name=property_data.get("name", ""),
        variant_count=variant_count,
        package_tier=tier,
        portal_url=portal_url,
        month_display=datetime.now().strftime("%B %Y"),
    )

    subject = (
        f"Your {datetime.now().strftime('%B %Y')} video creative is ready for review "
        f"— {property_data.get('name', '')}"
    )

    return send_email(to_email, subject, html_body)


def send_revision_notification(property_data: dict) -> bool:
    """Send notification that revised creative is ready."""
    to_email = property_data.get("video_creative_client_email", "")
    if not to_email:
        return False

    uuid = property_data.get("uuid", "")
    month = datetime.now().strftime("%Y%m")
    portal_url = build_portal_url(uuid, month)

    template = template_env.get_template("revision_ready_email.html")
    html_body = template.render(
        property_name=property_data.get("name", ""),
        portal_url=portal_url,
        month_display=datetime.now().strftime("%B %Y"),
    )

    subject = f"Your revised creative is ready for review — {property_data.get('name', '')}"
    return send_email(to_email, subject, html_body)


def send_upsell_am_notification(
    property_data: dict,
    interested_tier: str,
    projections: dict | None = None,
) -> bool:
    """Send upgrade interest notification to the property's AM."""
    # For now, send to SMTP_USER as AM placeholder
    # In production, this would go to the assigned AM
    to_email = SMTP_USER

    template = template_env.get_template("upsell_am_email.html")
    html_body = template.render(
        property_name=property_data.get("name", ""),
        current_tier=property_data.get("video_creative_package_tier", ""),
        interested_tier=interested_tier,
        projections=projections,
        hs_object_id=property_data.get("hs_object_id", ""),
        hubspot_url=f"https://app.hubspot.com/contacts/companies/{property_data.get('hs_object_id', '')}",
    )

    subject = f"Upgrade Interest: {property_data.get('name', '')} → {interested_tier}"
    return send_email(to_email, subject, html_body)


def send_approved_notification(property_data: dict, approved_urls: list[dict]) -> bool:
    """Notify paid media team that creative is approved."""
    to_email = SMTP_USER  # Placeholder — route to PM team

    template = template_env.get_template("approved_confirmation.html")
    html_body = template.render(
        property_name=property_data.get("name", ""),
        approved_urls=approved_urls,
        tier=property_data.get("video_creative_package_tier", ""),
    )

    subject = f"Creative Approved: {property_data.get('name', '')} — Ready for Deployment"
    return send_email(to_email, subject, html_body)
