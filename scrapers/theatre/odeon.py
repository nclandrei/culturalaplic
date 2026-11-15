import json
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official calendar."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one("script[src*='/api/embed/program.js']")
    if not embed:
        raise ValueError("Teatrul Odeon programme embed not found")
    script = fetch_page(
        urljoin(EVENTS_URL, str(embed["src"])),
        headers={"Referer": EVENTS_URL, "Origin": BASE_URL},
    )
    return parse_events(script)


def parse_events(script: str, now: datetime | None = None) -> list[Event]:
    """Read the explicit dates and detail links used by the official programme embed."""
    match = re.search(r"\blet\s+PERFORMANCES\s*=\s*", script)
    if not match:
        raise ValueError("Teatrul Odeon programme data not found")
    performances, _ = json.JSONDecoder().raw_decode(script[match.end():])
    today = (now or datetime.now()).date()
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") in {"cancelled", "suspended", "postponed"}:
            continue
        if performance.get("isListed") is False:
            continue
        title = performance.get("title", "").strip()
        try:
            date = datetime.fromisoformat(
                f"{performance['date']}T{performance['startTime']}"
            )
        except (KeyError, ValueError):
            continue
        if not title or date.date() < today or (title, date) in seen:
            continue
        seen.add((title, date))
        hall = performance.get("venue")
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon",
            date=date,
            url=urljoin(
                BASE_URL,
                performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL,
            ),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)
