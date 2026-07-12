#!/usr/bin/env python3
"""Integration test: runs all scrapers and optionally sends test alert.

Usage:
    python scripts/test_full_flow.py              # Run scrapers only
    python scripts/test_full_flow.py --alert      # Run scrapers + send test alert
    python scripts/test_full_flow.py --alert-only # Send test alert without scraping
"""

import argparse
import os
import sys
from pathlib import Path
from types import ModuleType

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Event
from main import FESTIVAL_SCRAPERS, SCRAPER_GROUPS
from services.email import ScraperError, send_scraper_alert


def registered_scrapers(category: str) -> list[ModuleType]:
    """Return each scheduled scraper once, preserving group order."""
    scrapers = SCRAPER_GROUPS[1][category] + SCRAPER_GROUPS[2][category]
    if category == "music":
        scrapers += sorted(FESTIVAL_SCRAPERS, key=lambda scraper: scraper.__name__)
    return list(dict.fromkeys(scrapers))


SCRAPERS = {
    category: registered_scrapers(category)
    for category in ("music", "theatre", "culture")
}


def test_scrapers() -> tuple[dict[str, list[Event]], list[ScraperError]]:
    """Run all scrapers and collect results/errors."""
    results: dict[str, list[Event]] = {"music": [], "theatre": [], "culture": []}
    errors: list[ScraperError] = []

    for category, scrapers in SCRAPERS.items():
        for scraper in scrapers:
            name = scraper.__name__.split(".")[-1]
            print(f"  Testing {name}...", end=" ", flush=True)

            try:
                events = scraper.scrape()
                results[category].extend(events)
                print(f"✓ {len(events)} events")
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                errors.append(ScraperError(name, str(e), tb))
                print(f"✗ {e}")

    return results, errors


def send_test_alert(errors: list[ScraperError] | None = None) -> None:
    """Send a test alert email."""
    to_email = os.environ.get("NOTIFY_EMAIL")
    if not to_email:
        print("✗ NOTIFY_EMAIL not set, cannot send alert")
        return

    if not os.environ.get("RESEND_API_KEY"):
        print("✗ RESEND_API_KEY not set, cannot send alert")
        return

    if errors is None:
        errors = [
            ScraperError(
                scraper_name="test_scraper",
                error_message="This is a test error",
                traceback="Traceback (test):\n  File 'test.py', line 1\nTestError: This is a test",
            )
        ]

    print(f"Sending test alert to {to_email}...")
    send_scraper_alert(errors, to_email)
    print("✓ Alert sent!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test GigRadar scrapers and alerts")
    parser.add_argument("--alert", action="store_true", help="Send alert after scraping")
    parser.add_argument("--alert-only", action="store_true", help="Only send test alert")
    args = parser.parse_args()

    if args.alert_only:
        send_test_alert()
        return

    print("=" * 50)
    print("GigRadar Integration Test")
    print("=" * 50)

    print("\nRunning all scrapers...")
    results, errors = test_scrapers()

    print("\n" + "-" * 50)
    print("Summary:")
    print(f"  Music events:   {len(results['music'])}")
    print(f"  Theatre events: {len(results['theatre'])}")
    print(f"  Culture events: {len(results['culture'])}")
    print(f"  Errors:         {len(errors)}")

    if errors:
        print("\nFailed scrapers:")
        for err in errors:
            print(f"  - {err.scraper_name}: {err.error_message}")

    if args.alert and errors:
        print("\n" + "-" * 50)
        send_test_alert(errors)
    elif args.alert and not errors:
        print("\nNo errors to report, skipping alert.")

    print("\n" + "=" * 50)
    if errors:
        print("RESULT: PARTIAL SUCCESS (some scrapers failed)")
        sys.exit(1)
    else:
        print("RESULT: SUCCESS (all scrapers working)")
        sys.exit(0)


if __name__ == "__main__":
    main()
