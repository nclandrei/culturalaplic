import html
import json
import re
from datetime import datetime

from models import Event
from services.http import HttpError, fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"
EMBED_SCRIPT_PATTERN = re.compile(
    r"""<script[^>]+src=["']([^"']+/api/embed/program\.js\?[^"']+)["']"""
)


def get_data_url(page_html: str) -> str:
    """Derive the programme JSON feed from the widget embedded in the official page."""
    match = EMBED_SCRIPT_PATTERN.search(page_html)
    if not match:
        raise HttpError("Teatrul Odeon programme widget not found")
    script_url = html.unescape(match.group(1))
    return script_url.replace("/api/embed/program.js", "/api/embed/program-data", 1)


def _parse_performance(item: dict, today: datetime) -> Event | None:
    if item.get("status") != "active" or item.get("isListed") is False:
        return None

    title = " ".join(str(item.get("title") or "").split())
    date_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(item.get("date") or ""))
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(item.get("startTime") or ""))
    if not title or not date_match or not time_match:
        return None
    try:
        event_date = datetime(
            *(int(value) for value in date_match.groups()),
            *(int(value) for value in time_match.groups()),
        )
    except ValueError:
        return None
    if event_date < today:
        return None

    hall = str(item.get("venue") or "").strip()
    venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"
    url = str(item.get("detailsUrl") or item.get("ticketUrl") or EVENTS_URL)
    artist = str(item.get("subtitle") or "").strip() or None
    price = str(item.get("ticketPrices") or "").strip().rstrip(".") or None

    return Event(title, artist, venue, event_date, url, "odeon", "theatre", price)


def parse_events(data: dict, now: datetime | None = None) -> list[Event]:
    """Parse the official programme widget feed, which uses explicit ISO dates."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime, str]] = set()
    for item in data.get("performances") or []:
        event = _parse_performance(item, today) if isinstance(item, dict) else None
        if event and (event.title, event.date, event.venue) not in seen:
            seen.add((event.title, event.date, event.venue))
            events.append(event)
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official programme widget."""
    data_url = get_data_url(fetch_page(EVENTS_URL))
    data = json.loads(fetch_page(data_url, headers={"Referer": EVENTS_URL}))
    if not data.get("success"):
        raise HttpError(f"Teatrul Odeon programme feed error: {data.get('error')}")
    return parse_events(data)
