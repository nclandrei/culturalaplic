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
    """Parse the dated performances embedded in the official programme script."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    match = re.search(r"\blet\s+PERFORMANCES\s*=\s*", program)
    if not match:
        raise ValueError("Odeon programme is missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(program[match.end():])
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for row in performances:
        if row.get("status") != "active" or row.get("hiddenFromPublic"):
            continue
        try:
            event_date = datetime.fromisoformat(f"{row['date']}T{row['startTime']}")
        except (KeyError, ValueError):
            continue
        title = row.get("title", "").strip()
        if not title or event_date < today or (title, event_date) in seen:
            continue
        # The programme displays category as the hall; venue can be stale after a move.
        hall = row.get("category") or row.get("venue", "")
        venue = f"Teatrul Odeon - {hall}" if hall.startswith("Sala ") else "Teatrul Odeon"
        url = row.get("detailsUrl") or row.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=row.get("subtitle") or None,
            venue=venue,
            date=event_date,
            url=urljoin(BASE_URL, url),
            source="odeon",
            category="theatre",
            price=row.get("ticketPrices") or None,
        ))
        seen.add((title, event_date))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official calendar."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    script = soup.select_one("script[src*='/embed/program.js']")
    if not script:
        raise ValueError("Odeon page is missing its programme script")
    program = fetch_page(
        urljoin(EVENTS_URL, script["src"]), headers={"Referer": EVENTS_URL},
    )
    return parse_events(program)
