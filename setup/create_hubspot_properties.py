"""Setup Script: Create all 11 custom HubSpot properties on the Company object.

Run once before first pipeline execution:
    python setup/create_hubspot_properties.py

Requires HUBSPOT_API_KEY in .env with Companies write scope.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
API_URL = "https://api.hubapi.com/crm/v3/properties/companies"

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    "Content-Type": "application/json",
}

# All 11 custom properties per the build spec (Section 3.4)
PROPERTIES = [
    {
        "name": "video_creative_package_tier",
        "label": "Video Creative Package Tier",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "companyinformation",
        "description": "Determines variant count and data depth for video creative pipeline",
        "options": [
            {"label": "Starter", "value": "Starter", "displayOrder": 1},
            {"label": "Standard", "value": "Standard", "displayOrder": 2},
            {"label": "Premium", "value": "Premium", "displayOrder": 3},
        ],
    },
    {
        "name": "video_creative_enrollment",
        "label": "Video Creative Enrollment",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "companyinformation",
        "description": "Enrollment filter for video creative pipeline",
        "options": [
            {"label": "Active", "value": "Active", "displayOrder": 1},
            {"label": "Inactive", "value": "Inactive", "displayOrder": 2},
            {"label": "Paused", "value": "Paused", "displayOrder": 3},
        ],
    },
    {
        "name": "video_creative_client_email",
        "label": "Video Creative Client Email",
        "type": "string",
        "fieldType": "text",
        "groupName": "companyinformation",
        "description": "Approval email + portal notification recipient",
    },
    {
        "name": "video_creative_latest_urls",
        "label": "Video Creative Latest URLs",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "companyinformation",
        "description": "JSON array of video objects [{url, length, format, platform, script_id}]",
    },
    {
        "name": "video_creative_approval_status",
        "label": "Video Creative Approval Status",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "companyinformation",
        "description": "Current approval status of video creative",
        "options": [
            {"label": "Pending", "value": "Pending", "displayOrder": 1},
            {"label": "Approved", "value": "Approved", "displayOrder": 2},
            {"label": "Revision Requested", "value": "Revision Requested", "displayOrder": 3},
            {"label": "Partial Approval", "value": "Partial Approval", "displayOrder": 4},
        ],
    },
    {
        "name": "video_creative_approved_date",
        "label": "Video Creative Approved Date",
        "type": "date",
        "fieldType": "date",
        "groupName": "companyinformation",
        "description": "Timestamp of last approval",
    },
    {
        "name": "video_creative_revision_count",
        "label": "Video Creative Revision Count",
        "type": "number",
        "fieldType": "number",
        "groupName": "companyinformation",
        "description": "Revisions used this month (resets monthly, max 5)",
    },
    {
        "name": "video_creative_rationale",
        "label": "Video Creative Rationale",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "companyinformation",
        "description": "AI-generated strategic rationale displayed on portal",
    },
    {
        "name": "video_creative_scripts_json",
        "label": "Video Creative Scripts JSON",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "companyinformation",
        "description": "Full script objects JSON for portal display (hook/body/cta per variant)",
    },
    {
        "name": "video_creative_performance_snapshot",
        "label": "Video Creative Performance Snapshot",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "companyinformation",
        "description": "JSON of NinjaCat metrics snapshot for budget simulator",
    },
    {
        "name": "video_creative_feedback_log",
        "label": "Video Creative Feedback Log",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "companyinformation",
        "description": "JSON log of all revision requests [{timestamp, variant, changes, notes}]",
    },
]


def create_property(prop: dict) -> bool:
    """Create a single HubSpot custom property."""
    resp = requests.post(API_URL, headers=HEADERS, json=prop, timeout=30)

    if resp.status_code == 201:
        print(f"  CREATED: {prop['name']}")
        return True
    elif resp.status_code == 409:
        print(f"  EXISTS:  {prop['name']} (already created)")
        return True
    else:
        print(f"  FAILED:  {prop['name']} — {resp.status_code}: {resp.text}")
        return False


def main():
    if not HUBSPOT_API_KEY:
        print("ERROR: HUBSPOT_API_KEY not set in .env")
        sys.exit(1)

    print(f"Creating {len(PROPERTIES)} custom properties on Company object...\n")

    success = 0
    for prop in PROPERTIES:
        if create_property(prop):
            success += 1

    print(f"\nDone: {success}/{len(PROPERTIES)} properties created/confirmed.")

    if success == len(PROPERTIES):
        print("All properties ready. You can now enroll properties in HubSpot.")
    else:
        print("Some properties failed. Check HubSpot API key permissions (needs CRM schema write).")


if __name__ == "__main__":
    main()
