"""Phase 1 — HubSpot Roster Pull.

Fetches all company records via Companies v3 API with getAll pagination.
Filters to video_creative_enrollment = Active.
"""

from __future__ import annotations


import logging
import requests
from config import HUBSPOT_API_KEY, HUBSPOT_API_BASE, HUBSPOT_PROPERTIES, normalize_property_data

logger = logging.getLogger(__name__)

COMPANIES_URL = f"{HUBSPOT_API_BASE}/crm/v3/objects/companies"


def fetch_all_companies() -> list[dict]:
    """Fetch all company records from HubSpot using cursor-based pagination."""
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}"}
    params = {
        "limit": 100,
        "properties": ",".join(HUBSPOT_PROPERTIES),
    }

    all_companies = []
    after = None

    while True:
        if after:
            params["after"] = after

        resp = requests.get(COMPANIES_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        for company in results:
            props = company.get("properties", {})
            props["hs_object_id"] = company.get("id", props.get("hs_object_id"))
            normalize_property_data(props)
            all_companies.append(props)

        paging = data.get("paging", {})
        next_page = paging.get("next", {})
        after = next_page.get("after")

        if not after:
            break

    logger.info("Fetched %d total companies from HubSpot", len(all_companies))
    return all_companies


def filter_enrolled(companies: list[dict]) -> list[dict]:
    """Filter to companies with video_creative_enrollment = Active."""
    enrolled = [
        c for c in companies
        if (c.get("video_creative_enrollment") or "").strip().lower() == "active"
    ]
    logger.info("Filtered to %d enrolled (Active) companies", len(enrolled))
    return enrolled


def run() -> list[dict]:
    """Execute Phase 1: fetch and filter HubSpot roster."""
    companies = fetch_all_companies()
    enrolled = filter_enrolled(companies)
    return enrolled


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run()
    print(f"Enrolled properties: {len(results)}")
    for p in results[:5]:
        print(f"  - {p.get('name')} ({p.get('video_creative_package_tier', 'N/A')})")
