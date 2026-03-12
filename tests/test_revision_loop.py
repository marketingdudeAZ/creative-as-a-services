"""Test: Revision feedback loop — feedback → re-gen → portal update."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phases.script_engine import build_creative_brief, generate_scripts


MOCK_PROPERTY = {
    "name": "The Modern at Art Place",
    "sfid": "SF001",
    "website": "https://themodernartplace.com",
    "property_tone_and_voice": "Modern, upscale, vibrant",
    "property_taglines": "Live Artfully",
    "video_creative_package_tier": "Starter",
    "amenities_to_call_out": "Resort-style pool, coworking spaces, rooftop lounge",
    "selling_points_vs_competitors": "Only community with dedicated coworking",
}

MOCK_ORIGINAL_SCRIPT = {
    "script_id": "SF001_15s_9x16_202604",
    "video_length": 15,
    "aspect_ratio": "9x16",
    "hook": "Your new address has a rooftop with skyline views",
    "body": "The Modern at Art Place brings coworking, resort pool, and vibrant Deep Ellum living together.",
    "cta": "Schedule your tour today",
    "full_narration": "Your new address has a rooftop with skyline views. The Modern at Art Place brings coworking, resort pool, and vibrant Deep Ellum living together. Schedule your tour today.",
    "on_screen_text": ["Rooftop Skyline Views", "Cowork + Resort Pool", "Schedule Your Tour"],
    "visual_direction": "Fast-paced, modern interiors, warm lighting",
    "target_platform": "Meta",
}


def test_revision_brief():
    """Test that revision context is correctly assembled into the brief."""
    revision_context = {
        "variant_script_id": "SF001_15s_9x16_202604",
        "tone_shift": "more urgent-scarcity",
        "emphasis_shift": None,
        "photo_emphasis": "pool-outdoor",
        "cta_change": "apply now",
        "free_text_notes": "Our residents skew younger — make it feel more energetic",
        "original_script": MOCK_ORIGINAL_SCRIPT,
    }

    brief = build_creative_brief(MOCK_PROPERTY, None, None, None, revision_context=revision_context)

    assert "revision_context" in brief, "Brief missing revision_context"
    assert brief["revision_context"]["tone_shift"] == "more urgent-scarcity"
    assert brief["revision_context"]["cta_change"] == "apply now"
    assert brief["revision_context"]["original_script"]["hook"] == MOCK_ORIGINAL_SCRIPT["hook"]

    print("Revision brief assembly: PASS")
    print(f"  Tone shift: {brief['revision_context']['tone_shift']}")
    print(f"  CTA change: {brief['revision_context']['cta_change']}")
    print(f"  Free text: {brief['revision_context']['free_text_notes']}")


def test_revision_generation():
    """Test revision script generation (requires ANTHROPIC_API_KEY)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Revision generation: SKIP (no ANTHROPIC_API_KEY)")
        return

    revision_context = {
        "variant_script_id": "SF001_15s_9x16_202604",
        "tone_shift": "more urgent-scarcity",
        "emphasis_shift": "focus on amenities",
        "photo_emphasis": "pool-outdoor",
        "cta_change": "apply now",
        "free_text_notes": "Our residents skew younger — make it feel more energetic",
        "original_script": MOCK_ORIGINAL_SCRIPT,
    }

    brief = build_creative_brief(MOCK_PROPERTY, None, None, None, revision_context=revision_context)
    result = generate_scripts(brief)

    assert result is not None, "Revision generation returned None"
    assert "scripts" in result, "Missing 'scripts' key"
    assert "rationale" in result, "Missing 'rationale' key"
    assert len(result["scripts"]) > 0, "No revised scripts"

    revised = result["scripts"][0]
    print("Revision generation: PASS")
    print(f"  New hook: {revised.get('hook', '')[:60]}...")
    print(f"  New CTA: {revised.get('cta', '')}")
    print(f"  Rationale: {result['rationale'][:100]}...")


if __name__ == "__main__":
    print("=== Revision Loop Tests ===\n")
    test_revision_brief()
    print()
    test_revision_generation()
