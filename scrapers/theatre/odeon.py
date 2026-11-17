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
    """Read the dated performances used by the official programme widget."""
    match = re.search(r"\b(?:let|const|var)\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Odeon programme widget contains no performances data")
    records, _ = json.JSONDecoder().raw_decode(program[match.end():])
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for row in records:
        if row.get("status") != "active" or row.get("isListed") is False:
            continue
        try:
            event_date = datetime.fromisoformat(f"{row['date']}T{row['startTime']}")
        except (KeyError, ValueError):
            continue
        title = row.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        hall = row.get("venue", "").strip()
        subtitle = row.get("subtitle", "").split("|", 1)[0].strip()
        url = row.get("detailsUrl") or row.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=subtitle or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=event_date,
            url=urljoin(BASE_URL, url),
            source="odeon",
            category="theatre",
            price=row.get("ticketPrices") or None,
        ))
        seen.add((title, event_date))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Follow the official calendar's embed, including its current public key."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    script = soup.select_one('script[src*="/api/embed/program.js"]')
    if not script:
        raise ValueError("Odeon programme embed not found")
    program = fetch_page(
        urljoin(EVENTS_URL, script["src"]),
        headers={"Referer": EVENTS_URL},
    )
    return parse_events(program)
