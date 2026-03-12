"""Phase 2 — Apartment IQ Market Data Pull.

Fetches fresh competitive market CSV from Apt IQ.
Filters to property's RPM Market. No caching.
"""

import csv
import io
import logging
import time
import requests
from config import APTIQ_API_KEY, APTIQ_ACCOUNT, APTIQ_CSV_URL

logger = logging.getLogger(__name__)


def fetch_csv(retry: bool = True) -> list[dict]:
    """Download Apt IQ CSV export and parse rows."""
    if not APTIQ_CSV_URL or APTIQ_CSV_URL == "TBD_placeholder":
        logger.warning("APTIQ_CSV_URL not configured — skipping market data")
        return []

    headers = {
        "X-API-Key": APTIQ_API_KEY,
        "X-Account-ID": APTIQ_ACCOUNT,
    }

    try:
        resp = requests.get(APTIQ_CSV_URL, headers=headers, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        if retry:
            logger.warning("Apt IQ fetch failed (%s), retrying in 30s...", e)
            time.sleep(30)
            return fetch_csv(retry=False)
        logger.error("Apt IQ fetch failed after retry: %s", e)
        return []

    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def filter_by_market(rows: list[dict], rpmmarket: str) -> list[dict]:
    """Filter CSV rows to match the property's RPM Market."""
    if not rpmmarket:
        return []
    market_lower = rpmmarket.strip().lower()
    return [r for r in rows if (r.get("market", "") or "").strip().lower() == market_lower]


def extract_market_context(comp_rows: list[dict], property_data: dict) -> dict | None:
    """Build market_context dict from Apt IQ data for a single property."""
    if not comp_rows:
        return None

    comp_names = []
    rents = []
    occupancy_rates = []
    concessions = []
    amenities_lists = []
    velocity_data = []
    pricing_changes = []

    for row in comp_rows:
        if row.get("property_name"):
            comp_names.append(row["property_name"])
        if row.get("average_rent"):
            try:
                rents.append(float(row["average_rent"].replace("$", "").replace(",", "")))
            except (ValueError, AttributeError):
                pass
        if row.get("occupancy"):
            occupancy_rates.append(row["occupancy"])
        if row.get("concessions"):
            concessions.append(row["concessions"])
        if row.get("amenities"):
            amenities_lists.append(row["amenities"])
        if row.get("leasing_velocity"):
            velocity_data.append(row["leasing_velocity"])
        if row.get("pricing_change"):
            pricing_changes.append(row["pricing_change"])

    # Include additional competitors from HubSpot
    extra_comps = property_data.get("competitors_outside_aptiq", "")

    return {
        "competitor_names": comp_names,
        "average_market_rents": rents,
        "occupancy_rates": occupancy_rates,
        "concessions": concessions,
        "competitor_amenities": amenities_lists,
        "leasing_velocity": velocity_data,
        "recent_pricing_changes": pricing_changes,
        "additional_competitors": extra_comps,
    }


def run(property_data: dict) -> dict | None:
    """Execute Phase 2 for a single property."""
    rpmmarket = property_data.get("rpmmarket", "")
    all_rows = fetch_csv()

    if not all_rows:
        logger.warning("No Apt IQ data available for %s", property_data.get("name"))
        return None

    filtered = filter_by_market(all_rows, rpmmarket)
    context = extract_market_context(filtered, property_data)

    if context:
        logger.info(
            "Market data for %s: %d comps in %s",
            property_data.get("name"),
            len(filtered),
            rpmmarket,
        )
    else:
        logger.warning("No market matches for %s in market '%s'", property_data.get("name"), rpmmarket)

    return context


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_property = {"name": "Test Property", "rpmmarket": "Dallas"}
    result = run(test_property)
    print(f"Market context: {result}")
