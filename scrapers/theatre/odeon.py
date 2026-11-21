import json
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"


def parse_events(data: dict, now: datetime | None = None) -> list[Event]:
    """Parse the official embedded programme's explicit dates and show details."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for row in data["performances"]:
        if row.get("status") != "active":
            continue
        try:
            event_date = datetime.fromisoformat(f"{row['date']}T{row['startTime']}")
        except (KeyError, ValueError):
            continue
        title = row.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))
        hall = row.get("venue", "").strip()
        events.append(Event(
            title=title,
            artist=row.get("subtitle") or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=event_date,
            url=urljoin(BASE_URL, row.get("detailsUrl") or row.get("ticketUrl") or EVENTS_URL),
            source="odeon",
            category="theatre",
            price=row.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official calendar."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one('script[src*="/api/embed/program.js?"]')
    if not embed:
        raise ValueError("Teatrul Odeon programme embed not found")
    # Discover the current public embed key instead of hard-coding it.
    data_url = urljoin(EVENTS_URL, embed["src"]).replace("/program.js?", "/program-data?")
    data = json.loads(fetch_page(data_url, headers={"Referer": EVENTS_URL}))
    return parse_events(data)
