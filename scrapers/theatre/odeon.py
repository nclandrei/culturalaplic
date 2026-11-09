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
    """Parse the performance data embedded in Odeon's programme widget."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    match = re.search(r"\b(?:let|const|var)\s+PERFORMANCES\s*=\s*", script)
    if not match:
        raise ValueError("Odeon programme widget is missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(script[match.end():])
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") in {"cancelled", "suspended", "postponed"}:
            continue
        if performance.get("hiddenFromPublic") or performance.get("isListed") is False:
            continue
        try:
            event_date = datetime.strptime(
                f"{performance['date']} {performance['startTime']}", "%Y-%m-%d %H:%M"
            )
        except (KeyError, ValueError):
            continue
        title = performance.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))
        hall = performance.get("venue", "").strip()
        venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"
        url = performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=venue,
            date=event_date,
            url=urljoin(BASE_URL, url),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official programme."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one("script[src*='/hub/api/embed/program.js']")
    if not embed:
        raise ValueError("Odeon programme embed script not found")
    script = fetch_page(urljoin(EVENTS_URL, embed["src"]), headers={"Referer": EVENTS_URL})
    return parse_events(script)
