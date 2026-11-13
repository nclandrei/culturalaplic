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
    """Read the dated performances embedded in the official calendar script."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    match = re.search(r"\b(?:let|const)\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Odeon calendar script contains no performances")
    performances, _ = json.JSONDecoder().raw_decode(program[match.end():])
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
        hall = performance.get("venue") or performance.get("category")
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=event_date,
            url=urljoin(BASE_URL, performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch the programme script linked by Teatrul Odeon's official page."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one("script[src*='/api/embed/program.js']")
    if not embed:
        raise ValueError("Odeon programme embed not found")
    # The embed checks its allowed referring domain. Discover its URL rather
    # than hard-coding the tenant's public embed key.
    program = fetch_page(urljoin(EVENTS_URL, embed["src"]), headers={"Referer": EVENTS_URL})
    return parse_events(program)
