import json
from datetime import datetime

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"
# The site's calendar links to this official ticket shop, which holds the
# programme even when the WordPress calendar says it will be announced later.
SHOP_URL = "https://bilete.teatrul-odeon.ro/"
SHOWS_API_URL = f"{SHOP_URL}api/shop/shows"
# Tenant header hard-coded in the shop's JavaScript bundle; the API rejects
# requests without it.
SHOP_HEADERS = {"T": "73b5407e-d8ef-4c3a-9a59-f15430386000"}


def parse_shows(shows: list[dict], now: datetime | None = None) -> list[Event]:
    """Turn the ticket shop's shows, rooms, and representations into events."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for show in shows:
        title = (show.get("name") or "").strip()
        if not title:
            continue
        credits = [
            text.strip()
            for text in (show.get("author"), show.get("director"))
            if text and text.strip() and text.strip() != "Teatrul Odeon"
        ]
        artist = ", ".join(credits) or None
        url = (show.get("detailsUrl") or "").strip() or SHOP_URL
        for room in show.get("rooms") or []:
            hall = (room.get("name") or "").strip()
            venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"
            for representation in room.get("representations") or []:
                try:
                    event_date = datetime.fromisoformat(representation["date"])
                except (KeyError, TypeError, ValueError):
                    continue
                if event_date < today or (title, event_date) in seen:
                    continue
                seen.add((title, event_date))
                events.append(
                    Event(title, artist, venue, event_date, url, "odeon", "theatre", None)
                )
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official ticket shop."""
    return parse_shows(json.loads(fetch_page(SHOWS_API_URL, headers=SHOP_HEADERS)))
