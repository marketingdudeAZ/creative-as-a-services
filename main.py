"""RPM Living AI Video Creative Pipeline — Main Entry Point.

Usage:
    python main.py                        # Full monthly run (all enrolled)
    python main.py --test                  # Single property pilot
    python main.py --phase 1              # HubSpot roster only
    python main.py --phase 2              # Apt IQ pull only
    python main.py --phase 3              # NinjaCat pull only
    python main.py --phase 4              # Website scrape only
    python main.py --phase 5              # Script generation only
    python main.py --phase 6              # Video gen + delivery only
    python main.py --property {SFID}      # Full pipeline for one property
"""

from __future__ import annotations


import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BATCH_SIZE, VIDEO_TIER_CONFIG
from phases import hubspot_roster, aptiq_market, ninjacat_performance, website_scraper, script_engine, video_generator
from delivery import hubspot_write, notification_email, sheets_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("pipeline")


def process_single_property(property_data: dict) -> dict:
    """Run the full pipeline for a single property. Returns result summary."""
    name = property_data.get("name", "Unknown")
    tier = (property_data.get("video_creative_package_tier") or "Starter").strip()
    result = {"property": name, "tier": tier, "status": "success", "errors": []}

    logger.info("=== Processing: %s (%s) ===", name, tier)

    # Phase 2: Apartment IQ
    try:
        market_context = aptiq_market.run(property_data)
        if market_context:
            sheets_logger.log_audit(name, "phase2", "OK", f"{len(market_context.get('competitor_names', []))} comps")
    except Exception as e:
        market_context = None
        result["errors"].append(f"Phase 2: {e}")
        sheets_logger.log_error(name, "phase2", "APTIQ_FAIL", str(e))

    # Phase 3: NinjaCat (Standard/Premium)
    performance_context = None
    if tier in ("Standard", "Premium"):
        try:
            performance_context = ninjacat_performance.run(property_data)
            if performance_context:
                sheets_logger.log_audit(name, "phase3", "OK", "Report parsed")
            else:
                sheets_logger.log_error(name, "phase3", "NO_REPORT", "No NinjaCat email found")
        except Exception as e:
            result["errors"].append(f"Phase 3: {e}")
            sheets_logger.log_error(name, "phase3", "NINJACAT_FAIL", str(e))

    # Phase 4: Website scrape (Premium)
    website_amenities = None
    if tier == "Premium":
        try:
            website_amenities = website_scraper.run(property_data)
            if website_amenities:
                sheets_logger.log_audit(name, "phase4", "OK", "Amenities scraped")
        except Exception as e:
            result["errors"].append(f"Phase 4: {e}")
            sheets_logger.log_error(name, "phase4", "SCRAPE_FAIL", str(e))

    # Phase 5: AI Script Generation
    try:
        ai_output = script_engine.run(
            property_data,
            market_context=market_context,
            performance_context=performance_context,
            website_amenities=website_amenities,
        )
        if not ai_output:
            result["status"] = "failed"
            result["errors"].append("Phase 5: Script generation returned None")
            sheets_logger.log_error(name, "phase5", "SCRIPT_FAIL", "No output")
            return result
        sheets_logger.log_audit(name, "phase5", "OK", f"{len(ai_output['scripts'])} scripts")
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Phase 5: {e}")
        sheets_logger.log_error(name, "phase5", "SCRIPT_FAIL", str(e))
        return result

    # Phase 6: Video Generation
    try:
        video_results = video_generator.run(property_data, ai_output["scripts"])
        if not video_results:
            result["status"] = "partial"
            result["errors"].append("Phase 6: No videos generated")
            sheets_logger.log_error(name, "phase6", "NO_VIDEOS", "All video generations failed")
        else:
            sheets_logger.log_audit(name, "phase6", "OK", f"{len(video_results)} videos")
            for v in video_results:
                sheets_logger.log_video_credit(name, v["script_id"], "creatify", v["video_length"])
    except Exception as e:
        video_results = []
        result["status"] = "partial"
        result["errors"].append(f"Phase 6: {e}")
        sheets_logger.log_error(name, "phase6", "VIDEO_FAIL", str(e))

    # HubSpot Write-Back
    if video_results:
        try:
            hubspot_write.write_video_results(
                property_data, video_results, ai_output, performance_context
            )
            sheets_logger.log_audit(name, "writeback", "OK", "HubSpot updated")
        except Exception as e:
            result["errors"].append(f"Write-back: {e}")
            sheets_logger.log_error(name, "writeback", "HUBSPOT_FAIL", str(e))

    # Notification Email
    if video_results:
        try:
            notification_email.send_new_creative_notification(property_data, len(video_results))
            sheets_logger.log_audit(name, "email", "OK", "Notification sent")
        except Exception as e:
            result["errors"].append(f"Email: {e}")
            sheets_logger.log_error(name, "email", "SMTP_FAIL", str(e))

    result["videos_generated"] = len(video_results)
    result["scripts_generated"] = len(ai_output.get("scripts", []))
    return result


def run_full_pipeline(properties: list[dict]) -> dict:
    """Run the pipeline for all enrolled properties with batching."""
    start_time = datetime.now()
    results = []
    total = len(properties)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = properties[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        logger.info("--- Batch %d (%d properties) ---", batch_num, len(batch))

        for prop in batch:
            try:
                result = process_single_property(prop)
                results.append(result)
            except Exception as e:
                logger.error("Unhandled error for %s: %s", prop.get("name"), e)
                results.append({
                    "property": prop.get("name", "Unknown"),
                    "status": "failed",
                    "errors": [str(e)],
                })

        # Sleep between batches (except last)
        if batch_start + BATCH_SIZE < total:
            logger.info("Batch complete. Waiting 60s before next batch...")
            time.sleep(60)

    # Summary
    summary = {
        "run_date": start_time.isoformat(),
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "total_properties": total,
        "successful": sum(1 for r in results if r["status"] == "success"),
        "partial": sum(1 for r in results if r["status"] == "partial"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "total_videos": sum(r.get("videos_generated", 0) for r in results),
        "results": results,
    }

    sheets_logger.write_run_summary(summary)
    logger.info(
        "Pipeline complete: %d/%d successful, %d videos generated in %.0fs",
        summary["successful"], total, summary["total_videos"], summary["duration_seconds"],
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="RPM Living AI Video Creative Pipeline")
    parser.add_argument("--test", action="store_true", help="Single property pilot mode")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5, 6], help="Run a single phase only")
    parser.add_argument("--property", type=str, help="Run full pipeline for one property by SFID")
    args = parser.parse_args()

    # Phase 1 always runs first
    if args.phase and args.phase > 1:
        logger.info("Running Phase %d only (requires pre-loaded data)", args.phase)
        # For isolated phase runs, just demonstrate the module
        if args.phase == 1:
            results = hubspot_roster.run()
            print(json.dumps([{"name": r.get("name"), "tier": r.get("video_creative_package_tier")} for r in results], indent=2))
        return

    # Phase 1: HubSpot Roster Pull
    logger.info("Phase 1: Fetching HubSpot roster...")
    enrolled = hubspot_roster.run()

    if not enrolled:
        logger.warning("No enrolled properties found. Exiting.")
        return

    logger.info("Found %d enrolled properties", len(enrolled))

    if args.phase == 1:
        print(json.dumps([{"name": r.get("name"), "tier": r.get("video_creative_package_tier")} for r in enrolled], indent=2))
        return

    # Single property mode
    if args.property:
        prop = next((p for p in enrolled if p.get("sfid") == args.property), None)
        if not prop:
            logger.error("Property with SFID %s not found in enrolled list", args.property)
            return
        result = process_single_property(prop)
        print(json.dumps(result, indent=2, default=str))
        return

    # Test mode: first property only
    if args.test:
        logger.info("Test mode: processing first enrolled property only")
        result = process_single_property(enrolled[0])
        print(json.dumps(result, indent=2, default=str))
        return

    # Full run
    summary = run_full_pipeline(enrolled)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
