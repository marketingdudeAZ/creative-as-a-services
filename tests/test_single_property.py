"""Test: Run pipeline for a single property with mock data."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phases.script_engine import build_creative_brief, generate_scripts


MOCK_PROPERTY = {
    "name": "The Modern at Art Place",
    "domain": "themodernartplace.com",
    "website": "https://themodernartplace.com",
    "sfid": "SF001",
    "uuid": "abc-123-def",
    "ninjacat_system_id": "NC001",
    "rpmmarket": "Dallas",
    "plestatus": "Stable",
    "property_tone_and_voice": "Modern, upscale, vibrant — speak to young professionals",
    "property_taglines": "Live Artfully. Your Canvas Awaits.",
    "units_offered": "Studio, 1BR, 2BR — 500-1200 sqft",
    "neighborhoods_to_target": "Deep Ellum, Uptown, Knox-Henderson",
    "landmarks_near_property": "AT&T Discovery District, Klyde Warren Park, Dallas Arts District",
    "unique_solutions": "First smart-home enabled community in Deep Ellum",
    "amenities_to_call_out": "Resort-style pool, coworking spaces with private offices, rooftop lounge with skyline views",
    "selling_points_vs_competitors": "Only community with dedicated coworking; newer build than all comps",
    "community_adjectives": "Vibrant, connected, design-forward",
    "overarching_goals": "Reach 95% occupancy by Q3, increase lease conversion rate",
    "challenges_next_6_8_months": "New comp opening 2 blocks away in June; need to lock in leases before",
    "competitors_outside_aptiq": "The Hamilton, AMLI Design District",
    "video_creative_package_tier": "Starter",
    "video_creative_enrollment": "Active",
    "video_creative_client_email": "test@example.com",
    "hs_object_id": "12345",
}

MOCK_MARKET_CONTEXT = {
    "competitor_names": ["Canvas Apartments", "The Loft at Elm", "Urban 1800"],
    "average_market_rents": [1450, 1520, 1380],
    "occupancy_rates": ["94%", "91%", "96%"],
    "concessions": ["None", "1 month free", "Look & lease $500"],
    "competitor_amenities": ["Pool, gym", "Pool, dog park, cowork", "Gym, rooftop"],
    "leasing_velocity": ["12/month", "8/month", "15/month"],
    "recent_pricing_changes": ["+3%", "-2%", "flat"],
    "additional_competitors": "The Hamilton, AMLI Design District",
}


def test_brief_assembly():
    """Test that creative brief is assembled correctly."""
    brief = build_creative_brief(MOCK_PROPERTY, MOCK_MARKET_CONTEXT, None, None)

    assert brief["property_name"] == "The Modern at Art Place"
    assert brief["package_tier"] == "Starter"
    assert len(brief["requested_variants"]) == 2  # Starter = 2 variants
    assert brief["market_context"] is not None
    assert brief["performance_context"] is None  # Starter doesn't get NinjaCat
    assert brief["website_amenities"] is None  # Starter doesn't get scrape

    print("Brief assembly: PASS")
    print(f"  Variants requested: {len(brief['requested_variants'])}")
    for v in brief["requested_variants"]:
        print(f"    {v['script_id']} — {v['video_length']}s {v['aspect_ratio']}")


def test_script_generation():
    """Test AI script generation with mock data (requires ANTHROPIC_API_KEY)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Script generation: SKIP (no ANTHROPIC_API_KEY)")
        return

    brief = build_creative_brief(MOCK_PROPERTY, MOCK_MARKET_CONTEXT, None, None)
    result = generate_scripts(brief)

    assert result is not None, "Script generation returned None"
    assert "scripts" in result, "Missing 'scripts' key"
    assert "rationale" in result, "Missing 'rationale' key"
    assert len(result["scripts"]) > 0, "No scripts generated"

    print("Script generation: PASS")
    print(f"  Rationale: {result['rationale'][:100]}...")
    print(f"  Scripts: {len(result['scripts'])}")
    for s in result["scripts"]:
        print(f"    {s['script_id']}: hook={s['hook'][:50]}...")


def test_tier_configs():
    """Test that tier configs produce correct variant counts."""
    from config import VIDEO_TIER_CONFIG

    for tier_name, config in VIDEO_TIER_CONFIG.items():
        prop = {**MOCK_PROPERTY, "video_creative_package_tier": tier_name}
        brief = build_creative_brief(prop, None, None, None)
        assert len(brief["requested_variants"]) == config["variant_count"], \
            f"{tier_name}: expected {config['variant_count']}, got {len(brief['requested_variants'])}"
        print(f"Tier {tier_name}: {len(brief['requested_variants'])} variants — PASS")


if __name__ == "__main__":
    print("=== Single Property Tests ===\n")
    test_tier_configs()
    print()
    test_brief_assembly()
    print()
    test_script_generation()
