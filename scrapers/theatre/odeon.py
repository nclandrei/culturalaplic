import json
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"


def parse_events(program: str, now: datetime | None = None) -> list[Event]:
    """Read the dated performance data embedded in the official calendar script."""
    match = re.search(r"\b(?:let|const|var)\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Teatrul Odeon calendar missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(program[match.end():])
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") in {"cancelled", "suspended", "postponed"}:
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
        # Category is the hall displayed on the card; venue can be stale.
        hall = performance.get("category") or performance.get("venue")
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
    """Fetch the calendar embed linked by Teatrul Odeon's official programme."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    script = soup.select_one("script[src*='/embed/program.js']")
    if not script:
        raise ValueError("Teatrul Odeon programme missing calendar embed")
    program = fetch_page(
        urljoin(EVENTS_URL, script["src"]),
        headers={"Referer": EVENTS_URL},
    )
    return parse_events(program)
