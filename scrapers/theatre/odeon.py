import json
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"


def parse_events(script: str, now: datetime | None = None) -> list[Event]:
    """Parse the performance data used by Odeon's official programme widget."""
    match = re.search(r"\blet\s+PERFORMANCES\s*=\s*", script)
    if not match:
        raise ValueError("Teatrul Odeon programme widget has no performance data")
    performances, _ = json.JSONDecoder().raw_decode(script[match.end():])
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()

    for performance in performances:
        if (
            performance.get("status") != "active"
            or performance.get("hiddenFromPublic")
            or performance.get("isListed") is False
        ):
            continue
        try:
            event_date = datetime.fromisoformat(
                f"{performance['date']}T{performance['startTime']}"
            )
        except (KeyError, ValueError):
            continue
        title = performance.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))
        hall = performance.get("venue", "").strip()
        link = performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=event_date,
            url=urljoin(BASE_URL, link),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch the embedded programme, preserving its explicit dates and status."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    widget = soup.select_one('script[src*="/api/embed/program.js"]')
    if not widget:
        raise ValueError("Teatrul Odeon page has no programme widget")
    script = fetch_page(
        urljoin(EVENTS_URL, widget["src"]), headers={"Referer": EVENTS_URL},
    )
    return parse_events(script)
