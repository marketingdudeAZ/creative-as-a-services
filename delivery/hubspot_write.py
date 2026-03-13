"""HubSpot Write-Back — updates company records with video URLs, scripts, rationale."""

from __future__ import annotations


import json
import logging
import requests

from config import HUBSPOT_API_KEY, HUBSPOT_API_BASE, normalize_property_data

logger = logging.getLogger(__name__)


def update_company(hs_object_id: str, properties: dict) -> bool:
    """PATCH a HubSpot company record with updated properties."""
    url = f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/{hs_object_id}"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.patch(url, headers=headers, json={"properties": properties}, timeout=30)
        resp.raise_for_status()
        logger.info("Updated HubSpot company %s", hs_object_id)
        return True
    except requests.RequestException as e:
        logger.error("HubSpot write-back failed for %s: %s", hs_object_id, e)
        return False


def write_video_results(
    property_data: dict,
    video_results: list[dict],
    ai_output: dict,
    performance_snapshot: dict | None = None,
) -> bool:
    """Write all pipeline results back to HubSpot company record."""
    hs_object_id = property_data.get("hs_object_id")
    if not hs_object_id:
        logger.error("No hs_object_id for %s — cannot write back", property_data.get("name"))
        return False

    properties = {
        "video_creative_latest_urls": json.dumps(video_results),
        "video_creative_approval_status": "Pending",
        "video_creative_rationale": ai_output.get("rationale", ""),
        "video_creative_scripts_json": json.dumps(ai_output.get("scripts", [])),
        "video_creative_revision_count": "0",
    }

    if performance_snapshot:
        properties["video_creative_performance_snapshot"] = json.dumps(performance_snapshot)

    return update_company(hs_object_id, properties)


def update_approval_status(hs_object_id: str, status: str, **extra) -> bool:
    """Update approval status and optional extra fields."""
    properties = {"video_creative_approval_status": status}
    properties.update(extra)
    return update_company(hs_object_id, properties)


def increment_revision_count(property_data: dict) -> int:
    """Increment and return the new revision count."""
    current = int(property_data.get("video_creative_revision_count") or 0)
    new_count = current + 1
    hs_object_id = property_data.get("hs_object_id")
    if hs_object_id:
        update_company(hs_object_id, {"video_creative_revision_count": str(new_count)})
    return new_count


def append_feedback_log(property_data: dict, feedback_entry: dict) -> bool:
    """Append a feedback entry to the feedback log JSON array."""
    hs_object_id = property_data.get("hs_object_id")
    if not hs_object_id:
        return False

    existing_log = property_data.get("video_creative_feedback_log", "[]")
    try:
        log = json.loads(existing_log)
    except (json.JSONDecodeError, TypeError):
        log = []

    log.append(feedback_entry)
    return update_company(hs_object_id, {"video_creative_feedback_log": json.dumps(log)})


def update_revised_variant(
    property_data: dict,
    revised_script: dict,
    revised_video: dict,
    new_rationale: str,
) -> bool:
    """Replace a single revised variant in URLs and scripts JSON."""
    hs_object_id = property_data.get("hs_object_id")
    if not hs_object_id:
        return False

    script_id = revised_script.get("script_id")

    # Update video URLs
    try:
        current_urls = json.loads(property_data.get("video_creative_latest_urls", "[]"))
    except (json.JSONDecodeError, TypeError):
        current_urls = []

    updated_urls = [v for v in current_urls if v.get("script_id") != script_id]
    updated_urls.append(revised_video)

    # Update scripts
    try:
        current_scripts = json.loads(property_data.get("video_creative_scripts_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        current_scripts = []

    updated_scripts = [s for s in current_scripts if s.get("script_id") != script_id]
    updated_scripts.append(revised_script)

    properties = {
        "video_creative_latest_urls": json.dumps(updated_urls),
        "video_creative_scripts_json": json.dumps(updated_scripts),
        "video_creative_rationale": new_rationale,
        "video_creative_approval_status": "Pending",
    }

    return update_company(hs_object_id, properties)


def get_company(hs_object_id: str) -> dict | None:
    """Fetch a single company record from HubSpot."""
    from config import HUBSPOT_PROPERTIES

    url = f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/{hs_object_id}"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}"}
    params = {"properties": ",".join(HUBSPOT_PROPERTIES)}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        props = data.get("properties", {})
        props["hs_object_id"] = data.get("id", props.get("hs_object_id"))
        normalize_property_data(props)
        return props
    except requests.RequestException as e:
        logger.error("Failed to fetch company %s: %s", hs_object_id, e)
        return None


def find_company_by_uuid(uuid: str) -> dict | None:
    """Search for a company by UUID."""
    url = f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/search"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json",
    }

    from config import HUBSPOT_PROPERTIES

    body = {
        "filterGroups": [{
            "filters": [{"propertyName": "uuid", "operator": "EQ", "value": uuid}]
        }],
        "properties": HUBSPOT_PROPERTIES,
        "limit": 1,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            props = results[0].get("properties", {})
            props["hs_object_id"] = results[0].get("id", props.get("hs_object_id"))
            normalize_property_data(props)
            return props
    except requests.RequestException as e:
        logger.error("Failed to search company by UUID %s: %s", uuid, e)

    return None
