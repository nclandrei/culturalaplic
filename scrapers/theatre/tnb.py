import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import (
    HTML_READER_BASE_URL,
    HTML_READER_HEADERS,
    HttpError,
    fetch_page,
    fetch_page_with_reader_fallback,
)

BASE_URL = "https://www.tnb.ro"
EVENTS_URL = f"{BASE_URL}/ro/bilete-online"


def parse_time(time_text: str) -> tuple[int, int]:
    """Parse time like 'Ora: 19:00' or 'Ora:  18:30'."""
    match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 19, 0


def parse_event(event_elem: BeautifulSoup, event_date: datetime) -> Event | None:
    """Parse one row from the official online ticket programme."""
    title_elem = event_elem.select_one(".title a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    if not title:
        return None
    
    url = title_elem.get("href", "")
    if url and not url.startswith("http"):
        url = BASE_URL + url
    
    hour_elem = event_elem.select_one("td.c3")
    hour, minute = 19, 0
    if hour_elem:
        hour, minute = parse_time(hour_elem.get_text(strip=True))
    
    event_datetime = event_date.replace(hour=hour, minute=minute)
    
    location_elem = event_elem.select_one("td.c2")
    hall = location_elem.get_text(strip=True) if location_elem else ""
    if hall == "-":
        hall = ""
    if hall.startswith("TNB - "):
        venue = hall
    elif hall:
        venue = f"TNB - {hall}"
    else:
        venue = "TNB"
    
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_datetime,
        url=url,
        source="tnb",
        category="theatre",
        price=None,
    )


def parse_day(day_elem: BeautifulSoup) -> list[Event]:
    """Parse all events nested under one list-view calendar day."""
    day_number = day_elem.select_one(".left_date .number")
    month_name = day_elem.select_one(".left_date .month")
    year_number = day_elem.select_one(".left_date .year")
    if not day_number or not month_name or not year_number:
        return []

    try:
        event_date = datetime(
            int(year_number.get_text(strip=True)),
            int(month_name.get_text(strip=True)),
            int(day_number.get_text(strip=True)),
        )
    except ValueError:
        return []

    events: list[Event] = []
    for event_elem in day_elem.select(".right_date tr"):
        event = parse_event(event_elem, event_date)
        if event:
            events.append(event)
    return events


def scrape() -> list[Event]:
    """Fetch all published dates without the unavailable monthly calendar."""
    events: list[Event] = []
    seen: set[tuple[str, str, str]] = set()
    try:
        html = fetch_page(
            f"{HTML_READER_BASE_URL}{EVENTS_URL}",
            headers=HTML_READER_HEADERS,
            timeout=60000,
            record_failure=False,
        )
        if 'id="show_list"' not in html:
            raise HttpError("TNB reader returned no ticket programme")
    except HttpError:
        html = fetch_page_with_reader_fallback(
            EVENTS_URL, expected_text='id="show_list"', timeout=60000,
        )

    soup = BeautifulSoup(html, "html.parser")
    for day in soup.select("div.day"):
        for event in parse_day(day):
            key = (event.title, event.date.isoformat(), event.venue)
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    events = [e for e in events if e.date >= today]
    events.sort(key=lambda e: e.date)
    
    return events
