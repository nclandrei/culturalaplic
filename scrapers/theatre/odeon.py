import html as html_lib
import json
import re
from datetime import datetime

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"
PROGRAM_SCRIPT_PATTERN = re.compile(
    r"https://projects\.doimih\.net/hub/api/embed/program\.js[^\"'<>\s]*"
)
PERFORMANCES_PATTERN = re.compile(r"\bPERFORMANCES\s*=\s*(\[.*?\]);\s*\n", re.S)


def _parse_performance(item: dict, today: datetime) -> Event | None:
    if str(item.get("status", "active")).lower() != "active" or item.get("isListed") is False:
        return None

    title = " ".join(str(item.get("title") or "").split())
    date_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(item.get("date") or ""))
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(item.get("startTime") or ""))
    if not title or not date_match or not time_match:
        return None
    try:
        event_date = datetime(
            *(int(value) for value in date_match.groups()),
            *(int(value) for value in time_match.groups()),
        )
    except ValueError:
        return None
    if event_date < today:
        return None

    hall = str(item.get("venue") or "").strip()
    venue = f"Teatrul Odeon - {hall}" if hall.lower().startswith("sala") else "Teatrul Odeon"
    subtitle = str(item.get("subtitle") or "").strip()
    return Event(
        title=title,
        artist=subtitle or None,
        venue=venue,
        date=event_date,
        url=item.get("detailsUrl") or item.get("ticketUrl") or EVENTS_URL,
        source="odeon",
        category="theatre",
        price=str(item.get("ticketPrices") or "").strip() or None,
    )


def parse_performances(items: list[dict], now: datetime | None = None) -> list[Event]:
    """Parse the programme widget's performances, which carry explicit dates."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for item in items:
        event = _parse_performance(item, today) if isinstance(item, dict) else None
        if event and (event.title, event.date) not in seen:
            seen.add((event.title, event.date))
            events.append(event)
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official programme widget."""
    page_html = fetch_page(EVENTS_URL)
    script_match = PROGRAM_SCRIPT_PATTERN.search(page_html)
    if not script_match:
        raise ValueError("Teatrul Odeon programme widget not found")
    script = fetch_page(
        html_lib.unescape(script_match.group(0)),
        headers={"Referer": EVENTS_URL},
    )
    data_match = PERFORMANCES_PATTERN.search(script)
    if not data_match:
        raise ValueError("Teatrul Odeon programme widget has no performances data")
    return parse_performances(json.loads(data_match.group(1)))
