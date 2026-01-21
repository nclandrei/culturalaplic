import json
import os
import re

from google import genai
from rapidfuzz import fuzz

from models import Event

# Canonical venue names -> list of known aliases/variations
VENUE_ALIASES: dict[str, list[str]] = {
    "control": ["control club", "control bucuresti", "club control"],
    "expirat": ["expirat club", "club expirat", "expirat halele carol"],
    "quantic": ["quantic club", "club quantic", "quantic bucuresti"],
    "beraria h": ["beraria h bucuresti", "berăria h"],
    "arenele romane": ["arenele romane bucuresti"],
    "sala palatului": ["sala palatului bucuresti"],
    "romexpo": ["romexpo bucuresti", "pavilion romexpo"],
    "opera nationala bucuresti": ["opera nb", "opera nationala"],
    "grivita 53": ["g53", "teatrul grivita", "teatrul grivita 53"],
    "tnb": ["teatrul national bucuresti", "teatrul nb", "teatrul national"]
}

# Build reverse lookup: alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in VENUE_ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical] = canonical
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


def sanitize_venue(venue: str) -> str:
    """Normalize venue name: lowercase, remove extra whitespace, punctuation."""
    venue = venue.lower().strip()
    venue = re.sub(r"[^\w\s]", "", venue)  # remove punctuation
    venue = re.sub(r"\s+", " ", venue)  # collapse whitespace
    return venue


def normalize_venue(venue: str) -> str:
    """Sanitize and resolve to canonical venue name if known."""
    sanitized = sanitize_venue(venue)
    return _ALIAS_TO_CANONICAL.get(sanitized, sanitized)


def normalize_for_dedup(event: Event) -> str:
    """Create a normalized key for exact deduplication."""
    artist = (event.artist or "").lower().strip()
    venue = normalize_venue(event.venue)
    date_str = event.date.strftime("%Y-%m-%d")
    return f"{artist}|{date_str}|{venue}"


def stage1_dedup(events: list[Event]) -> list[Event]:
    """Deduplicate using exact match and Levenshtein similarity."""
    if not events:
        return []

    seen_keys: set[str] = set()
    deduped: list[Event] = []

    for event in events:
        key = normalize_for_dedup(event)
        if key in seen_keys:
            continue

        is_duplicate = False
        event_venue_norm = normalize_venue(event.venue)
        for existing in deduped:
            if event.date.date() != existing.date.date():
                continue

            artist_ratio = fuzz.ratio(
                (event.artist or "").lower(), (existing.artist or "").lower()
            )
            existing_venue_norm = normalize_venue(existing.venue)

            # If both resolve to same canonical venue, it's a match
            if event_venue_norm == existing_venue_norm and artist_ratio > 85:
                is_duplicate = True
                break

            # Otherwise fall back to fuzzy venue matching
            venue_ratio = fuzz.ratio(event_venue_norm, existing_venue_norm)
            if artist_ratio > 85 and venue_ratio > 80:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_keys.add(key)
            deduped.append(event)

    return deduped


def llm_dedup(events: list[Event]) -> list[Event]:
    """Use LLM to identify remaining duplicates."""
    if len(events) < 2:
        return events

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set, skipping LLM dedup")
        return events

    client = genai.Client(api_key=api_key)

    events_data = []
    for i, e in enumerate(events):
        events_data.append({
            "id": i,
            "title": e.title,
            "artist": e.artist,
            "venue": e.venue,
            "date": e.date.strftime("%Y-%m-%d"),
            "source": e.source,
        })

    prompt = f"""You are a duplicate event detector. Given this list of events, identify which ones are duplicates of each other (same concert/show listed on different sources).

Events:
{json.dumps(events_data, indent=2)}

Return a JSON object with a single key "duplicates" containing a list of lists. Each inner list contains the IDs of events that are duplicates of each other.

Rules:
- Same artist + same date + same/similar venue = duplicate
- Different spelling of artist names may still be duplicates (e.g., "The Cure" vs "Cure")
- Venue variations are common (e.g., "Control Club" vs "Control")
- If no duplicates found, return {{"duplicates": []}}
- Only group events if you're confident they're the same event

Return ONLY valid JSON, no explanation."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        duplicate_groups = result.get("duplicates", [])

        ids_to_remove: set[int] = set()
        for group in duplicate_groups:
            if len(group) > 1:
                for dup_id in group[1:]:
                    ids_to_remove.add(dup_id)

        return [e for i, e in enumerate(events) if i not in ids_to_remove]

    except Exception as e:
        print(f"LLM dedup failed: {e}")
        return events
