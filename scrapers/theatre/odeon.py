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
    """Read the dated performances embedded in the official programme widget."""
    match = re.search(r"\b(?:let|const|var)\s+PERFORMANCES\s*=\s*", script)
    if not match:
        raise ValueError("Teatrul Odeon widget missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(script[match.end():])
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") in {"cancelled", "suspended", "postponed"}:
            continue
        if performance.get("isListed") is False:
            continue
        try:
            event_date = datetime.fromisoformat(
                f"{performance['date']}T{performance['startTime']}"
            )
        except (KeyError, ValueError):
            continue
        title = BeautifulSoup(performance.get("title", ""), "html.parser").get_text(
            " ", strip=True
        )
        if not title or event_date < today or (title, event_date) in seen:
            continue
        seen.add((title, event_date))
        # The card's hall category can differ from the show's default venue.
        category = performance.get("category", "")
        hall = category if category.startswith("Sala ") else performance.get("venue")
        link = performance.get("detailsUrl")
        if not link or link == "#":
            link = performance.get("ticketUrl") or EVENTS_URL
        if link == "#":
            link = EVENTS_URL
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
    """Follow the programme embed URL, including its current public widget key."""
    soup = BeautifulSoup(fetch_page(EVENTS_URL), "html.parser")
    embed = soup.select_one("script[src*='/api/embed/program.js']")
    if not embed:
        raise ValueError("Teatrul Odeon programme widget not found")
    script = fetch_page(
        urljoin(EVENTS_URL, str(embed["src"])),
        headers={"Referer": EVENTS_URL},
    )
    return parse_events(script)
