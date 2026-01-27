#!/usr/bin/env python3
"""Cultură la plic: Weekly event aggregator for Bucharest cultural events."""

import json
import os

from dotenv import load_dotenv
load_dotenv()
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from types import ModuleType

from models import Event
from services.email import ScraperError
from scrapers.culture import arcub, elvirepopescu, improteca, mare, mnac
from scrapers.music import ateneul, bfh, control, enescu, expirat, garana, jazzinthepark, jazzx, jfr, operanb, quantic, rockstadt
from scrapers.theatre import bulandra, cuibul, godot, grivita53, metropolis, nottara, teatrulmic, tnb
from services.dedup import llm_dedup, stage1_dedup
from services.enrichment import enrich_events
from services.spotify import search_artist

DATA_DIR = Path(__file__).parent / "web" / "public" / "data"
EVENTS_FILE = DATA_DIR / "events.json"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ERRORS_FILE = ARTIFACTS_DIR / "scraper_errors.json"
FESTIVAL_SCRAPERS = {bfh, garana, jazzinthepark, jfr, rockstadt}


def should_run_festival_scrapers() -> bool:
    """Run festival scrapers only on the 1st of each month (annual events don't change often)."""
    return datetime.now().day == 1


scraper_errors: list[ScraperError] = []


def run_scraper_safely(scraper: ModuleType) -> list[Event]:
    """Run a single scraper, catching and recording any errors."""
    import traceback
    scraper_name = scraper.__name__.split(".")[-1]
    category = scraper.__name__.split(".")[1]  # e.g., "music" from "scrapers.music.control"
    events_url = getattr(scraper, "EVENTS_URL", None)
    try:
        events = scraper.scrape()
        if len(events) == 0:
            print(f"⚠️  Scraper '{scraper_name}' returned 0 events")
            scraper_errors.append(ScraperError(
                scraper_name=scraper_name,
                error_message="Scraper returned 0 events",
                traceback="",
                category=category,
                events_url=events_url,
            ))
        return events
    except Exception as e:
        print(f"⚠️  Scraper '{scraper_name}' failed: {e}")
        scraper_errors.append(ScraperError(
            scraper_name=scraper_name,
            error_message=str(e),
            traceback=traceback.format_exc(),
            category=category,
            events_url=events_url,
        ))
        return []


def run_music_scrapers() -> list[Event]:
    """Run all music scrapers and collect events."""
    events: list[Event] = []
    all_scrapers = [ateneul, bfh, control, enescu, expirat, operanb, quantic, jfr, garana, jazzinthepark, jazzx, rockstadt]
    run_festivals = should_run_festival_scrapers()
    
    for scraper in all_scrapers:
        if scraper in FESTIVAL_SCRAPERS and not run_festivals:
            continue
        events.extend(run_scraper_safely(scraper))
    
    if not run_festivals:
        print("  (skipping festival scrapers - only run on 1st of month)")
    return events


def run_theatre_scrapers() -> list[Event]:
    """Run all theatre scrapers and collect events."""
    events: list[Event] = []
    for scraper in [bulandra, cuibul, godot, grivita53, metropolis, nottara, teatrulmic, tnb]:
        events.extend(run_scraper_safely(scraper))
    return events


def run_culture_scrapers() -> list[Event]:
    """Run all culture scrapers and collect events."""
    events: list[Event] = []
    for scraper in [arcub, elvirepopescu, improteca, mare, mnac]:
        events.extend(run_scraper_safely(scraper))
    return events


def enrich_with_spotify(events: list[Event]) -> list[Event]:
    """Add Spotify URLs to music events where artist is found."""
    if not os.environ.get("SPOTIFY_CLIENT_ID"):
        print("  SPOTIFY_CLIENT_ID not set, skipping Spotify enrichment")
        return events
    
    enriched: list[Event] = []
    for event in events:
        if event.category == "music" and event.artist:
            spotify_url = search_artist(event.artist)
            enriched.append(replace(event, spotify_url=spotify_url))
        else:
            enriched.append(event)
    return enriched


def load_existing_events() -> dict[str, list[dict]]:
    """Load existing events from events.json."""
    DATA_DIR.mkdir(exist_ok=True)
    
    if not EVENTS_FILE.exists():
        return {"music_events": [], "theatre_events": [], "culture_events": []}
    
    with open(EVENTS_FILE) as f:
        data = json.load(f)
    
    return {
        "music_events": data.get("music_events", []),
        "theatre_events": data.get("theatre_events", []),
        "culture_events": data.get("culture_events", []),
    }


def get_event_key(event: dict | Event) -> str:
    """Generate a unique key for an event (artist|date|venue)."""
    if isinstance(event, Event):
        date_str = event.date.strftime("%Y-%m-%d")
        return f"{event.artist}|{date_str}|{event.venue}"
    else:
        date_str = event["date"][:10] if event.get("date") else ""
        return f"{event.get('artist')}|{date_str}|{event.get('venue')}"


def load_previous_event_keys(existing_events: dict[str, list[dict]]) -> set[str]:
    """Get event keys from existing events dict."""
    keys: set[str] = set()
    for event in existing_events["music_events"] + existing_events["theatre_events"] + existing_events["culture_events"]:
        keys.add(get_event_key(event))
    return keys


def merge_events(existing: list[dict], new_events: list[Event]) -> list[dict]:
    """Merge new events with existing, deduplicating by key."""
    existing_keys = {get_event_key(e) for e in existing}
    merged = list(existing)
    
    for event in new_events:
        key = get_event_key(event)
        if key not in existing_keys:
            merged.append(asdict(event))
            existing_keys.add(key)
    
    return merged


def cleanup_past_events(events: list[dict]) -> list[dict]:
    """Remove events with date < today."""
    today = datetime.now().date()
    future_events = []
    
    for event in events:
        event_date_val = event.get("date")
        if event_date_val:
            if isinstance(event_date_val, datetime):
                event_date = event_date_val.date()
            elif isinstance(event_date_val, str):
                event_date = datetime.strptime(event_date_val[:10], "%Y-%m-%d").date()
            else:
                continue
            if event_date >= today:
                future_events.append(event)
    
    return future_events


def save_results(
    music_events: list[Event],
    theatre_events: list[Event],
    culture_events: list[Event],
    existing_events: dict[str, list[dict]],
) -> None:
    """Merge new events with existing and save to events.json."""
    DATA_DIR.mkdir(exist_ok=True)
    
    merged_music = merge_events(existing_events["music_events"], music_events)
    merged_theatre = merge_events(existing_events["theatre_events"], theatre_events)
    merged_culture = merge_events(existing_events["culture_events"], culture_events)
    
    merged_music = cleanup_past_events(merged_music)
    merged_theatre = cleanup_past_events(merged_theatre)
    merged_culture = cleanup_past_events(merged_culture)

    data = {
        "scraped_at": datetime.now().isoformat(),
        "music_events": merged_music,
        "theatre_events": merged_theatre,
        "culture_events": merged_culture,
    }

    with open(EVENTS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)





def get_new_events(
    events: list[Event], previous_keys: set[str]
) -> list[Event]:
    """Filter to only new events not seen in previous run."""
    new_events: list[Event] = []
    for event in events:
        key = get_event_key(event)
        if key not in previous_keys:
            new_events.append(event)
    return new_events


def save_scraper_errors(errors: list[ScraperError]) -> None:
    """Save scraper errors to JSON for the fix-scrapers workflow."""
    from dataclasses import asdict
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    
    error_dicts = [asdict(e) for e in errors]
    with open(ERRORS_FILE, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "errors": error_dicts,
        }, f, indent=2)


def main() -> None:
    """Main orchestrator."""
    print("Loading existing events...")
    existing_events = load_existing_events()
    previous_keys = load_previous_event_keys(existing_events)
    print(f"Loaded {len(previous_keys)} existing events")

    print("Running music scrapers...")
    music_events = run_music_scrapers()
    print(f"Found {len(music_events)} music events")

    print("Running theatre scrapers...")
    theatre_events = run_theatre_scrapers()
    print(f"Found {len(theatre_events)} theatre events")

    print("Running culture scrapers...")
    culture_events = run_culture_scrapers()
    print(f"Found {len(culture_events)} culture events")

    print("Deduplicating events...")
    deduped_music = stage1_dedup(music_events)
    deduped_music = llm_dedup(deduped_music)
    deduped_theatre = stage1_dedup(theatre_events)
    deduped_culture = stage1_dedup(culture_events)
    print(f"After dedup: {len(deduped_music)} music, {len(deduped_theatre)} theatre, {len(deduped_culture)} culture")

    print("Enriching music events with Spotify links...")
    deduped_music = enrich_with_spotify(deduped_music)
    spotify_count = sum(1 for e in deduped_music if e.spotify_url)
    print(f"Found {spotify_count} artists on Spotify")

    print("Enriching theatre/culture events with details...")
    deduped_theatre = enrich_events(deduped_theatre)
    deduped_culture = enrich_events(deduped_culture)
    theatre_enriched = sum(1 for e in deduped_theatre if e.description or e.image_url)
    culture_enriched = sum(1 for e in deduped_culture if e.description or e.image_url)
    print(f"Enriched {theatre_enriched} theatre, {culture_enriched} culture events")

    new_music = get_new_events(deduped_music, previous_keys)
    new_theatre = get_new_events(deduped_theatre, previous_keys)
    new_culture = get_new_events(deduped_culture, previous_keys)
    print(f"New events: {len(new_music)} music, {len(new_theatre)} theatre, {len(new_culture)} culture")

    print("Saving results (merging new events and removing past events)...")
    save_results(deduped_music, deduped_theatre, deduped_culture, existing_events)

    if scraper_errors:
        print(f"\n⚠️  {len(scraper_errors)} scraper(s) had issues:")
        for err in scraper_errors:
            print(f"  - {err.scraper_name}: {err.error_message}")
        save_scraper_errors(scraper_errors)
        print(f"Errors saved to {ERRORS_FILE}")
        print("Done with errors!")
        exit(2)  # Signal to GH Actions that scrapers need fixing
    else:
        print("Done!")


if __name__ == "__main__":
    main()
