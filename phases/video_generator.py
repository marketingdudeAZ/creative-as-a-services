"""Phase 6 — Video Generation via Creatify/HeyGen APIs.

Submits scripts to Creatify URL-to-Video workflow.
Polls for completion. Returns video URLs.
"""

import logging
import time
import requests

from config import (
    CREATIFY_API_ID,
    CREATIFY_API_KEY,
    CREATIFY_API_BASE,
    HEYGEN_API_KEY,
    VIDEO_STYLE,
    AVATAR_PLATFORM,
    POLL_INTERVAL,
    POLL_TIMEOUT,
)

logger = logging.getLogger(__name__)


def _creatify_headers() -> dict:
    return {
        "X-API-ID": CREATIFY_API_ID,
        "X-API-KEY": CREATIFY_API_KEY,
        "Content-Type": "application/json",
    }


def creatify_submit_link(website_url: str, description: str = "", media: list[str] = None) -> str | None:
    """Step 1: Submit URL to Creatify and get link_id."""
    resp = requests.post(
        f"{CREATIFY_API_BASE}/links/",
        headers=_creatify_headers(),
        json={"url": website_url},
        timeout=30,
    )
    resp.raise_for_status()
    link_id = resp.json().get("id")

    # Step 1b: Update metadata if provided
    if link_id and (description or media):
        patch_body = {}
        if description:
            patch_body["description"] = description
        if media:
            patch_body["media"] = media
        requests.patch(
            f"{CREATIFY_API_BASE}/links/{link_id}/",
            headers=_creatify_headers(),
            json=patch_body,
            timeout=30,
        )

    return link_id


def creatify_generate_video(
    link_id: str,
    script: dict,
    aspect_ratio: str = "9x16",
    video_length: int = 15,
) -> str | None:
    """Step 2: Generate video from link + script."""
    on_screen_text = script.get("on_screen_text", [])
    script_text = " ".join(on_screen_text) if on_screen_text else script.get("full_narration", "")

    body = {
        "link": link_id,
        "visual_style": "DynamicProductTemplate",
        "script_style": "custom",
        "script": script_text,
        "aspect_ratio": aspect_ratio,
        "video_length": video_length,
        "language": "en",
        "target_platform": script.get("target_platform", "Meta"),
    }

    resp = requests.post(
        f"{CREATIFY_API_BASE}/link_to_videos/",
        headers=_creatify_headers(),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("id")


def creatify_poll_video(video_id: str) -> str | None:
    """Step 3: Poll until video is done. Returns video URL."""
    start = time.time()

    while time.time() - start < POLL_TIMEOUT:
        resp = requests.get(
            f"{CREATIFY_API_BASE}/link_to_videos/{video_id}/",
            headers=_creatify_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")

        if status == "done":
            url = data.get("generated_video_url") or data.get("video_url")
            logger.info("Video %s completed: %s", video_id, url)
            return url
        elif status in ("failed", "error"):
            logger.error("Video %s failed: %s", video_id, data.get("error", "unknown"))
            return None

        time.sleep(POLL_INTERVAL)

    logger.error("Video %s timed out after %ds", video_id, POLL_TIMEOUT)
    return None


def creatify_avatar_video(script: dict, avatar_id: str = "default") -> str | None:
    """Generate avatar (lipsync) video via Creatify Aurora."""
    body = {
        "text": script.get("full_narration", ""),
        "avatar_id": avatar_id,
    }

    resp = requests.post(
        f"{CREATIFY_API_BASE}/lipsyncs/",
        headers=_creatify_headers(),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    video_id = resp.json().get("id")
    if video_id:
        return creatify_poll_video(video_id)
    return None


def heygen_generate_video(script: dict) -> str | None:
    """Generate avatar video via HeyGen API."""
    if not HEYGEN_API_KEY:
        logger.warning("HeyGen API key not configured")
        return None

    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }

    body = {
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": "default"},
            "voice": {"type": "text", "input_text": script.get("full_narration", "")},
        }],
        "dimension": {"width": 1080, "height": 1920} if script.get("aspect_ratio") == "9x16"
        else {"width": 1920, "height": 1080},
    }

    resp = requests.post(
        "https://api.heygen.com/v2/video/generate",
        headers=headers,
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    video_id = resp.json().get("data", {}).get("video_id")

    if not video_id:
        return None

    # Poll HeyGen
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        resp = requests.get(
            f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
            headers=headers,
            timeout=30,
        )
        data = resp.json().get("data", {})
        if data.get("status") == "completed":
            return data.get("video_url")
        elif data.get("status") in ("failed", "error"):
            logger.error("HeyGen video %s failed", video_id)
            return None
        time.sleep(POLL_INTERVAL)

    logger.error("HeyGen video %s timed out", video_id)
    return None


def generate_single_video(
    script: dict,
    website_url: str,
    property_data: dict,
) -> dict | None:
    """Generate a single video variant. Returns video result dict."""
    script_id = script.get("script_id", "unknown")
    aspect_ratio = script.get("aspect_ratio", "9x16")
    video_length = script.get("video_length", 15)

    logger.info("Generating video for %s (%ds, %s)", script_id, video_length, aspect_ratio)

    try:
        if VIDEO_STYLE == "avatar":
            if AVATAR_PLATFORM == "heygen":
                video_url = heygen_generate_video(script)
            else:
                video_url = creatify_avatar_video(script)
        else:
            # Motion graphics path via Creatify URL-to-Video
            description = " | ".join(filter(None, [
                property_data.get("property_taglines"),
                property_data.get("selling_points_vs_competitors"),
            ]))
            link_id = creatify_submit_link(website_url, description=description)

            if not link_id:
                logger.error("Failed to create Creatify link for %s", script_id)
                return None

            video_id = creatify_generate_video(link_id, script, aspect_ratio, video_length)
            if not video_id:
                logger.error("Failed to submit video generation for %s", script_id)
                return None

            video_url = creatify_poll_video(video_id)

        if video_url:
            return {
                "url": video_url,
                "video_length": video_length,
                "aspect_ratio": aspect_ratio,
                "target_platform": script.get("target_platform", "Meta"),
                "script_id": script_id,
            }

    except requests.HTTPError as e:
        if e.response and e.response.status_code == 429:
            logger.warning("Rate limited on %s — waiting 120s", script_id)
            time.sleep(120)
            return generate_single_video(script, website_url, property_data)
        # Retry once on other errors
        logger.warning("API error for %s: %s — retrying after 10s", script_id, e)
        time.sleep(10)
        try:
            return generate_single_video(script, website_url, property_data)
        except Exception:
            pass
    except Exception as e:
        logger.error("Video generation failed for %s: %s", script_id, e)

    return None


def run(property_data: dict, scripts: list[dict]) -> list[dict]:
    """Execute Phase 6: generate all video variants for a property."""
    website_url = property_data.get("website") or property_data.get("domain") or ""
    results = []

    for script in scripts:
        result = generate_single_video(script, website_url, property_data)
        if result:
            results.append(result)
        else:
            logger.warning("Skipping failed video: %s", script.get("script_id"))

    logger.info(
        "Generated %d/%d videos for %s",
        len(results),
        len(scripts),
        property_data.get("name"),
    )
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Video generator module loaded. Use run(property_data, scripts) to generate.")
