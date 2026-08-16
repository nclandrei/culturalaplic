import json
import os
import re
from collections import Counter
from datetime import date, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from google import genai
from rapidfuzz import fuzz

from models import Event

SOURCE_PRIORITY = {
    "eventbook": 10,
    "jfr": 20,
    "control": 20,
}
TRACKING_QUERY_KEYS = {"fbclid", "gclid"}
CONTROL_TICKET_SOURCES = frozenset({"control", "eventbook"})
MAX_DOOR_SHOW_DELTA_SECONDS = 90 * 60
ControlScheduleKey = tuple[str, date, str, str]

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
    identity = (event.artist or event.title).lower().strip()
    venue = normalize_venue(event.venue)
    date_str = event.date.strftime("%Y-%m-%dT%H:%M")
    return f"{event.source}|{identity}|{date_str}|{venue}"


def canonicalize_url(url: str) -> str:
    """Normalize URL spelling without discarding identity-bearing query params."""
    try:
        parsed = urlsplit(url.strip())
        hostname = parsed.hostname
        if not hostname:
            return url.strip()

        hostname = hostname.casefold().removeprefix("www.")
        port = parsed.port
        if port and not (
            (parsed.scheme.casefold() == "http" and port == 80)
            or (parsed.scheme.casefold() == "https" and port == 443)
        ):
            hostname = f"{hostname}:{port}"

        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        if path != "/":
            path = path.rstrip("/")

        query = urlencode(sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in TRACKING_QUERY_KEYS
        ))
        return urlunsplit(("https", hostname, path, query, ""))
    except ValueError:
        return url.strip()


def source_priority(event: Event) -> int:
    """Prefer curated or first-party records over the generic ticket feed."""
    return SOURCE_PRIORITY.get(event.source, 0)


def normalize_control_title(title: str) -> str:
    """Remove known Control/Eventbook packaging while retaining artist identity."""
    title = re.sub(
        r"\s*\|\s*(?:live at control|control club)\s*\|.*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(
        r"^\s*(?:ctrl\s+)?live\s*:\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(
        r"\[(?:[A-Z]{2,3}(?:/[A-Z]{2,3})*|Algeria)\]",
        " ",
        title,
    )
    title = re.sub(r"\((?:[A-Z]{2,3}(?:/[A-Z]{2,3})*)\)", " ", title)
    title = re.sub(
        r"\blive(?=\s*\+\s*special guests\b)",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"[^\w]+", " ", title.casefold(), flags=re.UNICODE)
    return " ".join(title.split())


def control_venue_family(venue: str) -> str:
    """Map Control room-qualified names to the ticket feed's venue root."""
    sanitized = sanitize_venue(venue)
    if normalize_venue(venue) == "control" or sanitized.startswith("control club "):
        return "control"
    return normalize_venue(venue)


def control_schedule_key(event: Event) -> ControlScheduleKey | None:
    """Build the coarse key used only for the Control/Eventbook source pair."""
    if event.source not in CONTROL_TICKET_SOURCES:
        return None

    title = normalize_control_title(event.title)
    venue = control_venue_family(event.venue)
    if not title or venue != "control":
        return None
    return event.source, event.date.date(), title, venue


def is_unique_control_ticket_overlap(
    event: Event,
    existing: Event,
    schedule_counts: Counter[ControlScheduleKey],
) -> bool:
    """Match a unique first-party/ticket pair without guessing among showtimes."""
    if {event.source, existing.source} != CONTROL_TICKET_SOURCES:
        return False
    if event.date.date() != existing.date.date():
        return False
    if abs((event.date - existing.date).total_seconds()) > MAX_DOOR_SHOW_DELTA_SECONDS:
        return False

    event_key = control_schedule_key(event)
    existing_key = control_schedule_key(existing)
    if not event_key or not existing_key:
        return False
    if event_key[1:] != existing_key[1:]:
        return False

    # A coarse day-level match is safe only when both feeds have one candidate.
    return schedule_counts[event_key] == schedule_counts[existing_key] == 1


def dedup_preferred_cross_source(events: list[Event]) -> list[Event]:
    """Apply deterministic cross-source rules and retain the preferred record."""
    schedule_counts = Counter(
        key for event in events if (key := control_schedule_key(event)) is not None
    )
    deduped: list[Event] = []

    for event in events:
        canonical_url = canonicalize_url(event.url)
        is_duplicate = False
        for existing_index, existing in enumerate(deduped):
            same_canonical_occurrence = (
                event.date == existing.date
                and canonical_url
                and canonical_url == canonicalize_url(existing.url)
            )
            if same_canonical_occurrence or is_unique_control_ticket_overlap(
                event,
                existing,
                schedule_counts,
            ):
                if source_priority(event) > source_priority(existing):
                    deduped[existing_index] = event
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(event)

    return deduped


def event_from_serialized(record: dict) -> Event | None:
    """Build a matching-only Event while leaving the serialized record intact."""
    date_value = record.get("date")
    try:
        if isinstance(date_value, datetime):
            event_date = date_value
        elif isinstance(date_value, str):
            event_date = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        else:
            return None
    except ValueError:
        return None
    event_date = event_date.replace(tzinfo=None)

    title = record.get("title")
    venue = record.get("venue")
    url = record.get("url")
    source = record.get("source")
    category = record.get("category")
    artist = record.get("artist")
    if not all(isinstance(value, str) for value in (title, venue, url, source)):
        return None
    if category not in {"music", "theatre", "culture"}:
        return None
    if artist is not None and not isinstance(artist, str):
        return None

    return Event(
        title=title,
        artist=artist,
        venue=venue,
        date=event_date,
        url=url,
        source=source,
        category=category,
    )


def dedup_serialized_cross_source(records: list[dict]) -> list[dict]:
    """Apply deterministic cross-source rules without losing serialized fields."""
    events: list[Event] = []
    records_by_event_id: dict[int, dict] = {}
    unparsed_records: list[dict] = []

    for record in records:
        event = event_from_serialized(record)
        if event is None:
            unparsed_records.append(record)
            continue
        events.append(event)
        records_by_event_id[id(event)] = record

    preferred = dedup_preferred_cross_source(events)
    return [records_by_event_id[id(event)] for event in preferred] + unparsed_records


def stage1_dedup(events: list[Event]) -> list[Event]:
    """Deduplicate using exact match and Levenshtein similarity."""
    if not events:
        return []

    events = dedup_preferred_cross_source(events)
    seen_keys: set[str] = set()
    deduped: list[Event] = []

    for event in events:
        key = normalize_for_dedup(event)
        if key in seen_keys:
            continue

        is_duplicate = False
        event_venue_norm = normalize_venue(event.venue)
        for existing in deduped:
            if event.source == existing.source:
                if event.date != existing.date:
                    continue
            else:
                if event.date.date() != existing.date.date():
                    continue
                event_time = event.date.time()
                existing_time = existing.date.time()
                midnight = datetime.min.time()
                if (
                    event_time != midnight
                    and existing_time != midnight
                    and event_time != existing_time
                ):
                    continue

            identity_ratio = fuzz.ratio(
                (event.artist or event.title).lower(),
                (existing.artist or existing.title).lower(),
            )
            existing_venue_norm = normalize_venue(existing.venue)

            # If both resolve to same canonical venue, it's a match
            if event_venue_norm == existing_venue_norm and identity_ratio > 85:
                is_duplicate = True
                break

            # Otherwise fall back to fuzzy venue matching
            venue_ratio = fuzz.ratio(event_venue_norm, existing_venue_norm)
            if identity_ratio > 85 and venue_ratio > 80:
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
