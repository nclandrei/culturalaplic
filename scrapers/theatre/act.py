import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.teatrulact.ro"
EVENTS_URL = f"{BASE_URL}/program/"
ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def _parse_datetime(date_text: str, time_text: str) -> datetime | None:
    match = re.fullmatch(r"\s*(\d{1,2})\s+([a-zăâîșț]+)\s+(\d{4})\s*", date_text.lower())
    time_match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    if not match or not time_match or match.group(2) not in ROMANIAN_MONTHS:
        return None
    try:
        return datetime(
            int(match.group(3)), ROMANIAN_MONTHS[match.group(2)], int(match.group(1)),
            int(time_match.group(1)), int(time_match.group(2)),
        )
    except ValueError:
        return None


def _parse_event(row: Tag, today: datetime) -> Event | None:
    text = row.get_text(" ", strip=True)
    if re.search(r"\b(anulat|anulată|amânat|amânată)\b", text, re.IGNORECASE):
        return None
    title_link = row.select_one(".movie_title a[href]")
    date_element = row.select_one(".movies_list_date")
    time_element = row.select_one(".movie_time")
    if not title_link or not date_element or not time_element:
        return None
    event_date = _parse_datetime(
        date_element.get_text(" ", strip=True), time_element.get_text(" ", strip=True)
    )
    if not event_date or event_date < today:
        return None

    title = title_link.get_text(" ", strip=True)
    if not title:
        return None
    author = row.select_one(".event_writers, .event_country")
    artist = author.get_text(" ", strip=True) if author else None
    price_element = row.select_one(".event_box_office")
    price = price_element.get_text(" ", strip=True) if price_element else None
    return Event(
        title, artist, "Teatrul ACT", event_date,
        urljoin(BASE_URL, str(title_link.get("href"))), "act", "theatre", price,
    )


def parse_events(html: str, now: datetime | None = None) -> list[Event]:
    """Parse the AJAX-rendered program; dates include their authoritative year."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for row in soup.select("li.event_list"):
        event = _parse_event(row, today)
        if event and (event.title, event.date) not in seen:
            seen.add((event.title, event.date))
            events.append(event)
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch Teatrul ACT's JS-populated program (up to 25 upcoming entries)."""
    return parse_events(fetch_page(
        EVENTS_URL, needs_js=True, timeout=60000, wait_selector="li.event_list"
    ))
