"""Phase 5 — AI Script Generation.

Assembles creative brief from all data sources.
Sends to Claude for script generation + strategic rationale.
"""

from __future__ import annotations


import json
import logging
from datetime import datetime

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, VIDEO_TIER_CONFIG

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Role: You are a senior performance marketing copywriter specializing in multifamily apartment advertising.

NEVER use language implying vacancy, desperation, or discounting — even if concession data suggests it.
NEVER reference internal RPM data, scores, or data sources by name.
MATCH the tone_and_voice field exactly. Incorporate taglines naturally. Do not invent new taglines.
Use market_context for positioning but present as value proposition, not data point.
Use performance_context to weight creative style but never reference it.
If any context field is null, write effective scripts without it. Do not mention missing data.
If revision_context is present, this is a revision request. Apply the requested changes to the specified variants while maintaining brand consistency. Only change what was requested.

Output instruction: Respond with ONLY valid JSON. No markdown, no backticks. The JSON object must have two keys: "scripts" (array of script objects) and "rationale" (string).

Each script object must have these fields:
- script_id: string ({SFID}_{length}s_{format}_{YYYYMM})
- video_length: int (6, 15, or 30)
- aspect_ratio: string ("9x16" or "16x9")
- hook: string (first 3 seconds — the attention grabber)
- body: string (main message, middle section)
- cta: string (call to action, final seconds)
- full_narration: string (complete spoken script if avatar is used)
- on_screen_text: list of strings (text overlay sequence for motion graphic style)
- visual_direction: string (mood, pacing, photo emphasis notes)
- target_platform: string ("Meta", "YouTube", or "TikTok")

The rationale must be 3-5 sentences explaining the strategic reasoning behind the creative decisions. Write it as if speaking to a property owner: confident, data-informed, jargon-light. Reference market position, competitive landscape, and performance trends without naming internal tools or data sources."""


def build_creative_brief(
    property_data: dict,
    market_context: dict | None,
    performance_context: dict | None,
    website_amenities: dict | None,
    revision_context: dict | None = None,
) -> dict:
    """Assemble the creative brief from all data sources."""
    tier = (property_data.get("video_creative_package_tier") or "Starter").strip()
    tier_config = VIDEO_TIER_CONFIG.get(tier, VIDEO_TIER_CONFIG["Starter"])
    now = datetime.now()

    # Build variant requests based on tier config
    requested_variants = []
    variant_idx = 0
    sfid = property_data.get("sfid", "UNKNOWN")
    month_str = now.strftime("%Y%m")

    for length in tier_config["lengths"]:
        for fmt in tier_config["formats"]:
            if variant_idx >= tier_config["variant_count"]:
                break
            requested_variants.append({
                "script_id": f"{sfid}_{length}s_{fmt.replace(':', 'x')}_{month_str}",
                "video_length": length,
                "aspect_ratio": fmt,
            })
            variant_idx += 1
        if variant_idx >= tier_config["variant_count"]:
            break

    brief = {
        "property_name": property_data.get("name", ""),
        "website_url": property_data.get("website") or property_data.get("domain", ""),
        "tone_and_voice": property_data.get("property_tone_and_voice", ""),
        "taglines": property_data.get("property_taglines", ""),
        "unit_mix": property_data.get("units_offered", ""),
        "target_neighborhoods": property_data.get("neighborhoods_to_target", ""),
        "nearby_landmarks": property_data.get("landmarks_near_property", ""),
        "unique_differentiators": property_data.get("unique_solutions", ""),
        "featured_amenities": property_data.get("amenities_to_call_out", ""),
        "competitive_advantages": property_data.get("selling_points_vs_competitors", ""),
        "community_adjectives": property_data.get("community_adjectives", ""),
        "strategic_goals": property_data.get("overarching_goals", ""),
        "current_challenges": property_data.get("challenges_next_6_8_months", ""),
        "market_context": market_context,
        "performance_context": performance_context if tier in ("Standard", "Premium") else None,
        "website_amenities": website_amenities if tier == "Premium" else None,
        "requested_variants": requested_variants,
        "package_tier": tier,
    }

    if revision_context:
        brief["revision_context"] = revision_context

    return brief


def generate_scripts(brief: dict, retry: bool = True) -> dict | None:
    """Send creative brief to Claude and get scripts + rationale."""
    user_message = json.dumps(brief, indent=2)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text.strip()

        # Parse JSON response
        result = json.loads(text)

        # Validate structure
        if "scripts" not in result or "rationale" not in result:
            raise ValueError("Response missing 'scripts' or 'rationale' keys")

        if not isinstance(result["scripts"], list):
            raise ValueError("'scripts' must be an array")

        logger.info(
            "Generated %d scripts for %s",
            len(result["scripts"]),
            brief.get("property_name"),
        )
        return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        if retry:
            logger.warning("Script generation parse error (%s), retrying...", e)
            return generate_scripts(brief, retry=False)
        logger.error("Script generation failed after retry: %s", e)
        return None
    except Exception as e:
        if retry:
            logger.warning("Script generation API error (%s), retrying...", e)
            return generate_scripts(brief, retry=False)
        logger.error("Script generation failed after retry: %s", e)
        return None


def run(
    property_data: dict,
    market_context: dict | None = None,
    performance_context: dict | None = None,
    website_amenities: dict | None = None,
    revision_context: dict | None = None,
) -> dict | None:
    """Execute Phase 5 for a single property."""
    brief = build_creative_brief(
        property_data, market_context, performance_context,
        website_amenities, revision_context,
    )

    logger.info("Creative brief assembled for %s (%s tier, %d variants)",
                property_data.get("name"),
                brief["package_tier"],
                len(brief["requested_variants"]))

    result = generate_scripts(brief)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_property = {
        "name": "The Modern at Art Place",
        "sfid": "SF001",
        "website": "https://example.com",
        "property_tone_and_voice": "Modern, upscale, vibrant",
        "property_taglines": "Live Artfully",
        "video_creative_package_tier": "Starter",
        "amenities_to_call_out": "Resort-style pool, coworking spaces, rooftop lounge",
    }
    result = run(test_property)
    if result:
        print(f"Rationale: {result['rationale']}")
        print(f"Scripts: {len(result['scripts'])}")
        for s in result["scripts"]:
            print(f"  - {s['script_id']}: {s['hook'][:50]}...")
