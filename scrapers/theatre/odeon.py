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
    """Parse the explicit performance data used by the official programme embed."""
    match = re.search(r"\blet\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Teatrul Odeon programme missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(program[match.end():])
    today = (now or datetime.now()).date()
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") != "active" or not performance.get("isListed", True):
            continue
        try:
            event_date = datetime.fromisoformat(
                f"{performance['date']}T{performance['startTime']}"
            )
        except (KeyError, ValueError):
            continue
        title = performance.get("title", "").strip()
        if not title or event_date.date() < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))
        hall = performance.get("venue", "").strip()
        url = performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=event_date,
            url=urljoin(BASE_URL, url),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch the programme embed linked by Teatrul Odeon's official page."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one("script[src*='/embed/program.js']")
    if not embed:
        raise ValueError("Teatrul Odeon calendar missing programme embed")
    # The provider restricts this public embed to the theatre's domain.
    program = fetch_page(
        urljoin(EVENTS_URL, embed["src"]), headers={"Referer": EVENTS_URL},
    )
    return parse_events(program)
