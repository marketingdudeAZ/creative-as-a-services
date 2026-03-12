"""Master Setup Runner — walks through all setup steps.

    python setup/run_setup.py
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")
ENV_EXAMPLE = os.path.join(ROOT, ".env.example")


def check_env():
    """Check if .env exists and has required keys."""
    print("=" * 60)
    print("STEP 1: Environment File (.env)")
    print("=" * 60)

    if not os.path.exists(ENV_FILE):
        print(f"\n  .env not found. Copying from .env.example...")
        with open(ENV_EXAMPLE) as src, open(ENV_FILE, "w") as dst:
            dst.write(src.read())
        print(f"  Created: {ENV_FILE}")
        print(f"\n  >>> OPEN .env AND FILL IN YOUR CREDENTIALS <<<")
        print(f"  Then re-run this script.\n")
        return False

    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

    required = {
        "HUBSPOT_API_KEY": os.getenv("HUBSPOT_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GMAIL_USER": os.getenv("GMAIL_USER"),
        "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD"),
    }

    optional = {
        "CREATIFY_API_ID": os.getenv("CREATIFY_API_ID"),
        "CREATIFY_API_KEY": os.getenv("CREATIFY_API_KEY"),
        "GOOGLE_SERVICE_ACCOUNT_JSON": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        "WEBHOOK_SECRET": os.getenv("WEBHOOK_SECRET"),
    }

    all_good = True
    print("\n  Required credentials:")
    for key, val in required.items():
        has = bool(val and "your_" not in val and "TBD" not in val)
        status = "SET" if has else "MISSING"
        print(f"    {key:30s} [{status}]")
        if not has:
            all_good = False

    print("\n  Optional credentials:")
    for key, val in optional.items():
        has = bool(val and "your_" not in val and "TBD" not in val and "path/to" not in val)
        status = "SET" if has else "NOT SET (ok for now)"
        print(f"    {key:30s} [{status}]")

    if not all_good:
        print("\n  >>> Fill in missing REQUIRED credentials in .env <<<\n")
        return False

    # Auto-generate WEBHOOK_SECRET if not set
    if not optional["WEBHOOK_SECRET"] or "your_" in optional["WEBHOOK_SECRET"]:
        import secrets
        secret = secrets.token_hex(32)
        with open(ENV_FILE, "r") as f:
            content = f.read()
        content = content.replace("your_hmac_secret_key", secret)
        with open(ENV_FILE, "w") as f:
            f.write(content)
        print(f"\n  Auto-generated WEBHOOK_SECRET")

    print("\n  Environment: OK\n")
    return True


def check_dependencies():
    """Check Python dependencies."""
    print("=" * 60)
    print("STEP 2: Python Dependencies")
    print("=" * 60)

    requirements = os.path.join(ROOT, "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", requirements, "-q"],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        print("\n  All dependencies installed.\n")
        return True
    else:
        print(f"\n  Error installing dependencies:\n  {result.stderr}\n")
        return False


def create_hubspot_properties():
    """Run the HubSpot property creation script."""
    print("=" * 60)
    print("STEP 3: Create HubSpot Custom Properties")
    print("=" * 60)

    script = os.path.join(os.path.dirname(__file__), "create_hubspot_properties.py")
    result = subprocess.run([sys.executable, script], cwd=ROOT)
    print()
    return result.returncode == 0


def verify_hubspot_properties():
    """Run the HubSpot property verification script."""
    print("=" * 60)
    print("STEP 4: Verify HubSpot Property Names")
    print("=" * 60)

    script = os.path.join(os.path.dirname(__file__), "verify_hubspot_properties.py")
    result = subprocess.run([sys.executable, script], cwd=ROOT)
    print()
    return result.returncode == 0


def test_hubspot_connection():
    """Test Phase 1 — HubSpot roster pull."""
    print("=" * 60)
    print("STEP 5: Test HubSpot Connection (Phase 1)")
    print("=" * 60)

    sys.path.insert(0, ROOT)
    try:
        from phases.hubspot_roster import fetch_all_companies, filter_enrolled
        import logging
        logging.basicConfig(level=logging.INFO)

        companies = fetch_all_companies()
        enrolled = filter_enrolled(companies)

        print(f"\n  Total companies: {len(companies)}")
        print(f"  Enrolled (Active): {len(enrolled)}")

        if enrolled:
            print("\n  First 5 enrolled:")
            for p in enrolled[:5]:
                print(f"    - {p.get('name', 'N/A')} ({p.get('video_creative_package_tier', 'no tier')})")
        else:
            print("\n  No enrolled properties yet.")
            print("  Set video_creative_enrollment = 'Active' on test properties in HubSpot.")

        print()
        return True
    except Exception as e:
        print(f"\n  HubSpot connection failed: {e}\n")
        return False


def test_script_generation():
    """Test Phase 5 — AI script generation."""
    print("=" * 60)
    print("STEP 6: Test AI Script Generation (Phase 5)")
    print("=" * 60)

    sys.path.insert(0, ROOT)
    try:
        from tests.test_single_property import MOCK_PROPERTY, MOCK_MARKET_CONTEXT
        from phases.script_engine import build_creative_brief, generate_scripts

        brief = build_creative_brief(MOCK_PROPERTY, MOCK_MARKET_CONTEXT, None, None)
        print(f"\n  Brief assembled: {len(brief['requested_variants'])} variants requested")
        print(f"  Calling Claude Sonnet...")

        result = generate_scripts(brief)
        if result:
            print(f"  Scripts generated: {len(result['scripts'])}")
            print(f"  Rationale: {result['rationale'][:120]}...")
            for s in result["scripts"]:
                print(f"    - {s['script_id']}: {s['hook'][:60]}...")
            print("\n  Script generation: PASS\n")
            return True
        else:
            print("\n  Script generation returned None.\n")
            return False
    except Exception as e:
        print(f"\n  Script generation failed: {e}\n")
        return False


def print_summary(results):
    """Print setup summary."""
    print("=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)

    steps = [
        ("Environment (.env)", results.get("env", False)),
        ("Dependencies", results.get("deps", False)),
        ("HubSpot Properties Created", results.get("hs_create", False)),
        ("HubSpot Properties Verified", results.get("hs_verify", False)),
        ("HubSpot Connection (Phase 1)", results.get("hs_test", False)),
        ("Script Generation (Phase 5)", results.get("script_test", False)),
    ]

    for name, passed in steps:
        icon = "PASS" if passed else "FAIL/SKIP"
        print(f"  {name:40s} [{icon}]")

    print("\n  NEXT STEPS:")
    if not results.get("env"):
        print("  1. Fill in .env credentials")
    if not results.get("hs_test"):
        print("  2. Enroll test properties in HubSpot (set enrollment = Active)")
    print("  3. Get Creatify API credentials for video generation")
    print("  4. Run: python main.py --test")
    print()


def main():
    os.chdir(ROOT)
    results = {}

    results["env"] = check_env()
    if not results["env"]:
        print_summary(results)
        return

    results["deps"] = check_dependencies()
    if not results["deps"]:
        print_summary(results)
        return

    results["hs_create"] = create_hubspot_properties()
    results["hs_verify"] = verify_hubspot_properties()
    results["hs_test"] = test_hubspot_connection()
    results["script_test"] = test_script_generation()

    print_summary(results)


if __name__ == "__main__":
    main()
