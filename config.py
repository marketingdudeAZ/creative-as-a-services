"""Configuration constants and tier settings for RPM Video Creative Pipeline."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Credentials (from .env) ---
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
APTIQ_API_KEY = os.getenv("APTIQ_API_KEY")
APTIQ_ACCOUNT = os.getenv("APTIQ_ACCOUNT")
APTIQ_CSV_URL = os.getenv("APTIQ_CSV_URL")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_IMAP_HOST = os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
CREATIFY_API_ID = os.getenv("CREATIFY_API_ID")
CREATIFY_API_KEY = os.getenv("CREATIFY_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_SHEETS_AUDIT_ID = os.getenv("GOOGLE_SHEETS_AUDIT_ID")
GOOGLE_SHEETS_ERROR_ID = os.getenv("GOOGLE_SHEETS_ERROR_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "https://digital.rpmliving.com")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# --- Video Creative Tier Config ---
VIDEO_TIER_CONFIG = {
    "Starter": {
        "variant_count": 2,
        "lengths": [15, 30],
        "formats": ["9x16"],
        "data_sources": ["hubspot", "aptiq"],
    },
    "Standard": {
        "variant_count": 4,
        "lengths": [15, 30],
        "formats": ["9x16", "16x9"],
        "data_sources": ["hubspot", "aptiq", "ninjacat"],
    },
    "Premium": {
        "variant_count": 6,
        "lengths": [6, 15, 30],
        "formats": ["9x16", "16x9"],
        "data_sources": ["hubspot", "aptiq", "ninjacat", "website"],
    },
}

MAX_REVISIONS_PER_MONTH = 5
VIDEO_STYLE = "motion_graphics"  # or "avatar"
AVATAR_PLATFORM = "creatify"  # or "heygen"
BATCH_SIZE = 10
POLL_INTERVAL = 10  # seconds
POLL_TIMEOUT = 900  # 15 minutes

# --- HubSpot Property Names ---
# Confirmed internal names for company profile fields.
# Update these if HubSpot internal names differ.
HUBSPOT_PROPERTIES = [
    "name",
    "domain",
    "website",
    "sfid",
    "uuid",
    "ninjacat_system_id",
    "rpmmarket",
    "plestatus",
    "property_tone_and_voice",
    "property_taglines",
    "units_offered",
    "neighborhoods_to_target",
    "landmarks_near_property",
    "unique_solutions",
    "amenities_to_call_out",
    "selling_points_vs_competitors",
    "community_adjectives",
    "overarching_goals",
    "challenges_next_6_8_months",
    "competitors_outside_aptiq",
    "video_creative_package_tier",
    "video_creative_enrollment",
    "video_creative_client_email",
    "video_creative_approval_status",
    "video_creative_latest_urls",
    "video_creative_revision_count",
    "video_creative_rationale",
    "video_creative_scripts_json",
    "video_creative_performance_snapshot",
    "video_creative_feedback_log",
    "hs_object_id",
]

HUBSPOT_API_BASE = "https://api.hubapi.com"
CREATIFY_API_BASE = "https://api.creatify.ai/api"
