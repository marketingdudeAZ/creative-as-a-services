"""Configuration constants and tier settings for RPM Video Creative Pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the project root (next to config.py)
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

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
    "property_voice_and_tone",
    "property_tag_lines",
    "units_offered",
    "neighborhoods_to_target",
    "landmarks_near_the_property",
    "what_unique_solutions_does_the_community_offer_residents_that_set_it_apart_from_competitors_",
    "what_amenities_do_we_want_to_call_out_",
    "what_are_additional_selling_points_of_living_here_vs_the_competitors_",
    "what_adjectives_would_you_use_to_describe_the_community_",
    "what_are_your_overarching_goals_for_this_property_",
    "what_challenges_will_have_in_the_next_6_8_months_",
    "properties_competitors_outside_of_comps_in_apt_iq_",
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

# Mapping from clean names (used in code) → actual HubSpot internal names
# This lets the pipeline code use readable names while matching HubSpot's actual fields
PROPERTY_ALIAS = {
    "property_tone_and_voice": "property_voice_and_tone",
    "property_taglines": "property_tag_lines",
    "landmarks_near_property": "landmarks_near_the_property",
    "unique_solutions": "what_unique_solutions_does_the_community_offer_residents_that_set_it_apart_from_competitors_",
    "amenities_to_call_out": "what_amenities_do_we_want_to_call_out_",
    "selling_points_vs_competitors": "what_are_additional_selling_points_of_living_here_vs_the_competitors_",
    "community_adjectives": "what_adjectives_would_you_use_to_describe_the_community_",
    "overarching_goals": "what_are_your_overarching_goals_for_this_property_",
    "challenges_next_6_8_months": "what_challenges_will_have_in_the_next_6_8_months_",
    "competitors_outside_aptiq": "properties_competitors_outside_of_comps_in_apt_iq_",
}

# Reverse mapping: HubSpot internal name → clean alias
PROPERTY_REVERSE = {v: k for k, v in PROPERTY_ALIAS.items()}


def normalize_property_data(props: dict) -> dict:
    """Add clean alias keys to a property dict so code can use readable names."""
    for clean_name, hs_name in PROPERTY_ALIAS.items():
        if hs_name in props and clean_name not in props:
            props[clean_name] = props[hs_name]
    return props


HUBSPOT_API_BASE = "https://api.hubapi.com"
CREATIFY_API_BASE = "https://api.creatify.ai/api"
