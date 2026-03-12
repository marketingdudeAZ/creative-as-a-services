"""Setup Script: Verify existing HubSpot property names match config.

Fetches all Company properties from HubSpot and checks which ones
from our config actually exist. Helps identify misnamed properties.

    python setup/verify_hubspot_properties.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

# The property names we expect to exist (from config.py)
EXPECTED_PROPERTIES = [
    "name", "domain", "website", "sfid", "uuid", "ninjacat_system_id",
    "rpmmarket", "plestatus",
    "property_tone_and_voice", "property_taglines", "units_offered",
    "neighborhoods_to_target", "landmarks_near_property", "unique_solutions",
    "amenities_to_call_out", "selling_points_vs_competitors",
    "community_adjectives", "overarching_goals", "challenges_next_6_8_months",
    "competitors_outside_aptiq",
    "video_creative_package_tier", "video_creative_enrollment",
    "video_creative_client_email", "video_creative_approval_status",
    "video_creative_latest_urls", "video_creative_revision_count",
    "video_creative_rationale", "video_creative_scripts_json",
    "video_creative_performance_snapshot", "video_creative_feedback_log",
    "hs_object_id",
]


def fetch_all_property_names() -> dict:
    """Fetch all Company property definitions from HubSpot."""
    url = "https://api.hubapi.com/crm/v3/properties/companies"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    props = {}
    for p in resp.json().get("results", []):
        props[p["name"]] = p.get("label", "")
    return props


def main():
    if not HUBSPOT_API_KEY:
        print("ERROR: HUBSPOT_API_KEY not set in .env")
        sys.exit(1)

    print("Fetching all Company properties from HubSpot...\n")
    existing = fetch_all_property_names()
    print(f"Found {len(existing)} total properties.\n")

    found = []
    missing = []

    for prop in EXPECTED_PROPERTIES:
        if prop in existing:
            found.append((prop, existing[prop]))
        else:
            missing.append(prop)

    print("--- FOUND (matched) ---")
    for name, label in found:
        print(f"  {name:45s} → {label}")

    if missing:
        print(f"\n--- MISSING ({len(missing)}) ---")
        for name in missing:
            print(f"  {name}")

        # Try fuzzy matching
        print("\n--- POSSIBLE MATCHES ---")
        for m in missing:
            keywords = m.replace("_", " ").split()
            candidates = []
            for existing_name, existing_label in existing.items():
                combined = f"{existing_name} {existing_label}".lower()
                matches = sum(1 for kw in keywords if kw.lower() in combined)
                if matches >= max(1, len(keywords) // 2):
                    candidates.append((existing_name, existing_label, matches))
            candidates.sort(key=lambda x: -x[2])
            if candidates:
                print(f"\n  {m}:")
                for c_name, c_label, _ in candidates[:3]:
                    print(f"    → {c_name} ({c_label})")
    else:
        print("\nAll expected properties exist in HubSpot!")

    # Also print all properties for reference
    print("\n\n--- ALL COMPANY PROPERTIES (for reference) ---")
    for name in sorted(existing.keys()):
        print(f"  {name:50s} {existing[name]}")


if __name__ == "__main__":
    main()
