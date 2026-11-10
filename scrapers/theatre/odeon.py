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
    """Read the dated performances embedded in Odeon's programme script."""
    match = re.search(r"\blet\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Teatrul Odeon programme missing PERFORMANCES data")
    performances, _ = json.JSONDecoder().raw_decode(program[match.end():])
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
        except (KeyError, ValueError, TypeError):
            continue
        title = performance.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))

        # The category is the hall displayed on the programme cards. Some feed
        # entries retain a different, outdated value in their venue field.
        category = performance.get("category", "")
        hall = category if category.startswith("Sala ") else performance.get("venue")
        venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"
        link = performance.get("detailsUrl")
        if not link or link == "#":
            link = performance.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=venue,
            date=event_date,
            url=urljoin(BASE_URL, link),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch the programme feed used by Teatrul Odeon's official calendar."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    script = soup.select_one("script[src*='/api/embed/program.js']")
    if not script:
        raise ValueError("Teatrul Odeon programme embed not found")
    program = fetch_page(
        urljoin(EVENTS_URL, script["src"]),
        headers={"Referer": EVENTS_URL},
    )
    return parse_events(program)
