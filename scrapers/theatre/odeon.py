import json
from datetime import datetime

from models import Event
from services.http import fetch_page

TICKETS_URL = "https://bilete.teatrul-odeon.ro"
EVENTS_URL = f"{TICKETS_URL}/"
SHOWS_API_URL = f"{TICKETS_URL}/api/shop/shows"
# Static theatre identifier the official ticketing app sends with every API call.
API_HEADERS = {"T": "73b5407e-d8ef-4c3a-9a59-f15430386000", "Accept": "application/json"}


def parse_events(shows: list[dict], now: datetime | None = None) -> list[Event]:
    """Convert the ticketing app's shows/rooms/representations into events."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for show in shows:
        title = " ".join(str(show.get("name") or "").split())
        if not title:
            continue
        url = show.get("detailsUrl") or f"{TICKETS_URL}/{show.get('slug', '')}"
        artist = " ".join(str(show.get("author") or "").split()) or None
        for room in show.get("rooms") or []:
            hall = " ".join(str(room.get("name") or "").split())
            venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"
            for representation in room.get("representations") or []:
                try:
                    event_date = datetime.fromisoformat(str(representation.get("date")))
                except ValueError:
                    continue
                event_date = event_date.replace(tzinfo=None)
                if event_date < today or (title, event_date) in seen:
                    continue
                seen.add((title, event_date))
                events.append(
                    Event(title, artist, venue, event_date, url, "odeon", "theatre", None)
                )
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official ticketing app."""
    return parse_events(json.loads(fetch_page(SHOWS_API_URL, headers=API_HEADERS)))
