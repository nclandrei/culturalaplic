#!/usr/bin/env python3
"""GigRadar: Weekly event aggregator matching Spotify followed artists."""

import json
import os
import traceback
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

from rapidfuzz import fuzz

from models import Event
from scrapers.culture import arcub, mnac
from scrapers.music import control, enescu, expirat, garana, jazzinthepark, jazzx, jfr, quantic
from scrapers.theatre import bulandra
from services.dedup import llm_dedup, stage1_dedup
from services.email import ScraperError, send_digest, send_scraper_alert
from services.spotify import get_followed_artists, normalize

DATA_DIR = Path(__file__).parent / "data"
RETENTION_DAYS = 7

scraper_errors: list[ScraperError] = []


def run_scraper_safely(scraper: ModuleType) -> list[Event]:
    """Run a single scraper, catching and recording any errors."""
    scraper_name = scraper.__name__.split(".")[-1]
    try:
        return scraper.scrape()
    except Exception as e:
        tb = traceback.format_exc()
        error = ScraperError(
            scraper_name=scraper_name,
            error_message=str(e),
            traceback=tb,
        )
        scraper_errors.append(error)
        print(f"⚠️  Scraper '{scraper_name}' failed: {e}")
        return []


def run_music_scrapers() -> list[Event]:
    """Run all music scrapers and collect events."""
    events: list[Event] = []
    for scraper in [control, enescu, expirat, quantic, jfr, garana, jazzinthepark, jazzx]:
        events.extend(run_scraper_safely(scraper))
    return events


def run_theatre_scrapers() -> list[Event]:
    """Run all theatre scrapers and collect events."""
    events: list[Event] = []
    for scraper in [bulandra]:
        events.extend(run_scraper_safely(scraper))
    return events


def run_culture_scrapers() -> list[Event]:
    """Run all culture scrapers and collect events."""
    events: list[Event] = []
    for scraper in [arcub, mnac]:
        events.extend(run_scraper_safely(scraper))
    return events


def match_events(events: list[Event], artists: list[str]) -> list[Event]:
    """Filter events to those matching followed artists."""
    artist_set = {normalize(a) for a in artists}

    matched: list[Event] = []
    for event in events:
        if not event.artist:
            continue

        normalized_artist = normalize(event.artist)
        if normalized_artist in artist_set:
            matched.append(event)
            continue

        for artist in artist_set:
            if fuzz.ratio(normalized_artist, artist) > 85:
                matched.append(event)
                break

    return matched


def load_previous_events() -> set[str]:
    """Load event keys from the most recent JSON file."""
    DATA_DIR.mkdir(exist_ok=True)
    files = sorted(DATA_DIR.glob("*.json"), reverse=True)

    if not files:
        return set()

    with open(files[0]) as f:
        data = json.load(f)

    keys: set[str] = set()
    for event in data.get("music_events", []) + data.get("theatre_events", []) + data.get("culture_events", []):
        key = f"{event['artist']}|{event['date']}|{event['venue']}"
        keys.add(key)

    return keys


def save_results(
    music_events: list[Event],
    theatre_events: list[Event],
    culture_events: list[Event],
    artists: list[str],
) -> None:
    """Save results to a date-prefixed JSON file."""
    DATA_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = DATA_DIR / f"{today}.json"

    data = {
        "scraped_at": datetime.now().isoformat(),
        "music_events": [asdict(e) for e in music_events],
        "theatre_events": [asdict(e) for e in theatre_events],
        "culture_events": [asdict(e) for e in culture_events],
        "spotify_artists": artists,
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def cleanup_old_files() -> None:
    """Delete JSON files older than RETENTION_DAYS."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)

    for filepath in DATA_DIR.glob("*.json"):
        try:
            date_str = filepath.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                filepath.unlink()
        except ValueError:
            pass


def get_new_events(
    events: list[Event], previous_keys: set[str]
) -> list[Event]:
    """Filter to only new events not seen in previous run."""
    new_events: list[Event] = []
    for event in events:
        key = f"{event.artist}|{event.date.strftime('%Y-%m-%d')}|{event.venue}"
        if key not in previous_keys:
            new_events.append(event)
    return new_events


def main() -> None:
    """Main orchestrator."""
    print("Fetching Spotify followed artists...")
    artists = get_followed_artists()
    print(f"Found {len(artists)} followed artists")

    print("Running music scrapers...")
    music_events = run_music_scrapers()
    print(f"Found {len(music_events)} music events")

    print("Matching events to followed artists...")
    matched_music = match_events(music_events, artists)
    print(f"Matched {len(matched_music)} events to followed artists")

    print("Running theatre scrapers...")
    theatre_events = run_theatre_scrapers()
    print(f"Found {len(theatre_events)} theatre events")

    print("Running culture scrapers...")
    culture_events = run_culture_scrapers()
    print(f"Found {len(culture_events)} culture events")

    print("Deduplicating events...")
    deduped_music = stage1_dedup(matched_music)
    deduped_music = llm_dedup(deduped_music)
    deduped_theatre = stage1_dedup(theatre_events)
    deduped_culture = stage1_dedup(culture_events)
    print(f"After dedup: {len(deduped_music)} music, {len(deduped_theatre)} theatre, {len(deduped_culture)} culture")

    print("Loading previous results...")
    previous_keys = load_previous_events()

    new_music = get_new_events(deduped_music, previous_keys)
    new_theatre = get_new_events(deduped_theatre, previous_keys)
    new_culture = get_new_events(deduped_culture, previous_keys)
    print(f"New events: {len(new_music)} music, {len(new_theatre)} theatre, {len(new_culture)} culture")

    if new_music or new_theatre or new_culture:
        print("Sending email digest...")
        to_email = os.environ.get("NOTIFY_EMAIL", "")
        if to_email:
            send_digest(new_music, new_theatre, new_culture, to_email)
            print("Email sent!")
        else:
            print("NOTIFY_EMAIL not set, skipping email")

    print("Saving results...")
    save_results(deduped_music, deduped_theatre, deduped_culture, artists)

    print("Cleaning up old files...")
    cleanup_old_files()

    if scraper_errors:
        print(f"Sending alert for {len(scraper_errors)} failed scraper(s)...")
        to_email = os.environ.get("NOTIFY_EMAIL", "")
        if to_email:
            send_scraper_alert(scraper_errors, to_email)
            print("Alert sent!")
        else:
            print("NOTIFY_EMAIL not set, skipping alert")

    print("Done!")


if __name__ == "__main__":
    main()
