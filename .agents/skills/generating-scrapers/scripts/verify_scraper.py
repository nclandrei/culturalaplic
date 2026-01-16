#!/usr/bin/env python3
"""Verify scraper output against page screenshot.

Usage (run from project root):
    # Screenshot only (for reconnaissance)
    python .agents/skills/generating-scrapers/scripts/verify_scraper.py --url "https://example.com/events" --screenshot-only
    
    # Full verification (run scraper + screenshot + compare)
    python .agents/skills/generating-scrapers/scripts/verify_scraper.py --scraper scrapers/theatre/example.py --url "https://example.com/events"
"""

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Ensure project root is in path for imports
project_root = Path(__file__).resolve().parents[4]  # .agents/skills/generating-scrapers/scripts -> root
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from playwright.sync_api import sync_playwright


def take_screenshot(url: str, output_path: Path, timeout: int = 60000) -> None:
    """Take a full-page screenshot of the URL."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)  # Allow JS to render
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()
    print(f"Screenshot saved: {output_path}")


def save_html(url: str, output_path: Path, timeout: int = 60000) -> None:
    """Save rendered HTML for inspection."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML saved: {output_path}")


def run_scraper(scraper_path: Path) -> list[dict]:
    """Import and run a scraper module."""
    spec = importlib.util.spec_from_file_location("scraper", scraper_path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load scraper from {scraper_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules["scraper"] = module
    spec.loader.exec_module(module)
    
    if not hasattr(module, "scrape"):
        raise AttributeError(f"Scraper {scraper_path} has no scrape() function")
    
    events = module.scrape()
    
    # Convert to dicts, handling datetime serialization
    result = []
    for event in events:
        d = asdict(event)
        d["date"] = event.date.isoformat()
        result.append(d)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify scraper against page screenshot")
    parser.add_argument("--url", required=True, help="URL to screenshot")
    parser.add_argument("--scraper", help="Path to scraper module (e.g., scrapers/theatre/example.py)")
    parser.add_argument("--screenshot-only", action="store_true", help="Only take screenshot, don't run scraper")
    parser.add_argument("--output-dir", default="tmp", help="Output directory for files")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Derive name from scraper path or URL
    if args.scraper:
        name = Path(args.scraper).stem
    else:
        from urllib.parse import urlparse
        name = urlparse(args.url).netloc.replace("www.", "").split(".")[0]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Take screenshot
    screenshot_path = output_dir / f"{name}_screenshot_{timestamp}.png"
    take_screenshot(args.url, screenshot_path)
    
    # Save HTML for inspection
    html_path = output_dir / f"{name}_page_{timestamp}.html"
    save_html(args.url, html_path)
    
    if args.screenshot_only:
        print(f"\nReconnaissance complete for {args.url}")
        print(f"  Screenshot: {screenshot_path}")
        print(f"  HTML: {html_path}")
        return
    
    if not args.scraper:
        print("Error: --scraper required unless using --screenshot-only")
        sys.exit(1)
    
    scraper_path = Path(args.scraper)
    if not scraper_path.exists():
        print(f"Error: Scraper not found: {scraper_path}")
        sys.exit(1)
    
    # Run scraper
    print(f"\nRunning scraper: {scraper_path}")
    try:
        events = run_scraper(scraper_path)
    except Exception as e:
        print(f"Error running scraper: {e}")
        sys.exit(1)
    
    # Save events JSON
    events_path = output_dir / f"{name}_events_{timestamp}.json"
    events_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Events saved: {events_path}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Scraper: {scraper_path}")
    print(f"URL: {args.url}")
    print(f"Events found: {len(events)}")
    print(f"{'='*60}")
    
    if events:
        print("\nSample events (first 5):")
        for i, event in enumerate(events[:5], 1):
            print(f"\n  {i}. {event['title']}")
            print(f"     Date: {event['date']}")
            print(f"     Venue: {event['venue']}")
            if event.get('price'):
                print(f"     Price: {event['price']}")
    
    print(f"\nCompare against screenshot: {screenshot_path}")
    print("Verify:")
    print("  [ ] Event count matches visible events")
    print("  [ ] Titles are correctly extracted")
    print("  [ ] Dates parse correctly")
    print("  [ ] Venues include hall names where applicable")
    print("  [ ] URLs are absolute and valid")


if __name__ == "__main__":
    main()
