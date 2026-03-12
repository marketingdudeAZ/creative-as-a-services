"""Phase 4 — Website Amenity Scrape.

Tier gating: Premium only.
Fetches property website amenity pages, parses for amenity lists and lifestyle copy.
"""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

AMENITY_PATHS = ["/amenities", "/features", "/community", "/community-amenities"]


def fetch_amenity_page(base_url: str) -> tuple[str, str] | None:
    """Try multiple amenity page paths, return first successful response."""
    if not base_url:
        return None

    base_url = base_url.rstrip("/")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    for path in AMENITY_PATHS:
        url = f"{base_url}{path}"
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; RPMCreativeBot/1.0)"
            })
            if resp.status_code == 200:
                logger.info("Found amenity page at %s", url)
                return url, resp.text
        except requests.RequestException:
            continue

    return None


def parse_amenities(html: str) -> dict:
    """Extract amenity lists, hero copy, and JSON-LD from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    community_amenities = []
    unit_amenities = []
    lifestyle_copy = ""

    # Extract from common list patterns
    for ul in soup.find_all("ul"):
        parent = ul.parent
        parent_text = (parent.get_text() if parent else "").lower()
        items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True)]

        if any(kw in parent_text for kw in ["community", "property", "outdoor", "common"]):
            community_amenities.extend(items)
        elif any(kw in parent_text for kw in ["unit", "apartment", "interior", "kitchen", "in-home"]):
            unit_amenities.extend(items)
        else:
            # Default: split heuristically based on common keywords
            for item in items:
                lower = item.lower()
                if any(kw in lower for kw in ["pool", "gym", "fitness", "clubhouse", "lounge",
                                                "parking", "dog", "pet", "grill", "court",
                                                "business", "cowork", "rooftop", "garden"]):
                    community_amenities.append(item)
                elif any(kw in lower for kw in ["granite", "stainless", "washer", "dryer",
                                                  "closet", "balcony", "patio", "hardwood",
                                                  "ceiling", "appliance", "counter"]):
                    unit_amenities.append(item)
                else:
                    community_amenities.append(item)

    # Extract hero/lifestyle copy from headings and prominent paragraphs
    hero_texts = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 10:
            hero_texts.append(text)

    # First substantial paragraph as lifestyle copy
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 50:
            lifestyle_copy = text
            break

    # JSON-LD structured data
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, dict):
                amenity_feature = data.get("amenityFeature", [])
                if isinstance(amenity_feature, list):
                    for feat in amenity_feature:
                        name = feat.get("name", "") if isinstance(feat, dict) else str(feat)
                        if name:
                            community_amenities.append(name)
        except (json.JSONDecodeError, TypeError):
            pass

    # Deduplicate
    community_amenities = list(dict.fromkeys(community_amenities))
    unit_amenities = list(dict.fromkeys(unit_amenities))

    return {
        "community_amenities": community_amenities,
        "unit_amenities": unit_amenities,
        "lifestyle_copy": lifestyle_copy,
        "hero_texts": hero_texts,
    }


def run(property_data: dict) -> dict | None:
    """Execute Phase 4 for a single property."""
    tier = (property_data.get("video_creative_package_tier") or "").strip()
    if tier != "Premium":
        logger.info("Skipping website scrape for %s (tier: %s)", property_data.get("name"), tier)
        return None

    website = property_data.get("website") or property_data.get("domain") or ""
    if not website:
        logger.warning("No website URL for %s — using HubSpot amenities only", property_data.get("name"))
        return None

    result = fetch_amenity_page(website)
    if not result:
        logger.warning("No amenity page found for %s at %s", property_data.get("name"), website)
        return None

    url, html = result
    amenities = parse_amenities(html)
    logger.info(
        "Scraped %d community + %d unit amenities for %s",
        len(amenities["community_amenities"]),
        len(amenities["unit_amenities"]),
        property_data.get("name"),
    )
    return amenities


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_property = {
        "name": "Test Property",
        "website": "https://example.com",
        "video_creative_package_tier": "Premium",
    }
    result = run(test_property)
    print(f"Website amenities: {result}")
