import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from models import Event
from services.http import (
    HTML_READER_BASE_URL,
    HTML_READER_HEADERS,
    HttpError,
    fetch_page,
    fetch_page_with_reader_fallback,
)

BASE_URL = "https://tnb.ro"
CALENDAR_URL = f"{BASE_URL}/ro/calendar"
EVENTS_URL = CALENDAR_URL
TICKETS_URL = "https://www.bilet.ro/venue/tnb"

MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def get_calendar_url(year: int, month: int) -> str:
    """Build calendar URL for given year and month."""
    return f"{CALENDAR_URL}?year={year}&month={month}&view=list"


def parse_time(time_text: str) -> tuple[int, int]:
    """Parse time like 'Ora: 19:00' or 'Ora:  18:30'."""
    match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 19, 0


def parse_event(event_elem: BeautifulSoup, event_date: datetime) -> Event | None:
    """Parse a single event from an official list-view day."""
    title_elem = event_elem.select_one("a.ev_title")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    if not title:
        return None
    
    url = title_elem.get("href", "")
    if url and not url.startswith("http"):
        url = BASE_URL + url
    
    hour_elem = event_elem.select_one(".time")
    hour, minute = 19, 0
    if hour_elem:
        hour, minute = parse_time(hour_elem.get_text(strip=True))
    
    event_datetime = event_date.replace(hour=hour, minute=minute)
    
    location_elem = event_elem.select_one(".location")
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

    month = MONTHS.get(month_name.get_text(strip=True).lower()[:3])
    if not month:
        return []

    try:
        event_date = datetime(
            int(year_number.get_text(strip=True)),
            month,
            int(day_number.get_text(strip=True)),
        )
    except ValueError:
        return []

    events: list[Event] = []
    for event_elem in day_elem.select(".right_items .item"):
        event = parse_event(event_elem, event_date)
        if event:
            events.append(event)
    return events


def scrape_month(year: int, month: int) -> list[Event]:
    """Scrape events for a specific month."""
    events: list[Event] = []
    
    url = get_calendar_url(year, month)
    try:
        try:
            html = fetch_page(
                f"{HTML_READER_BASE_URL}{url}",
                headers=HTML_READER_HEADERS,
                timeout=60000,
                record_failure=False,
            )
            if "right_items" not in html:
                raise HttpError("TNB reader returned no calendar list")
        except HttpError:
            html = fetch_page_with_reader_fallback(
                url, expected_text="right_items", timeout=60000,
            )
    except Exception as e:
        print(f"Failed to fetch TNB calendar for {year}/{month}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for day_elem in soup.select("div.day"):
        events.extend(parse_day(day_elem))
    
    return events


def scrape_ticket_programme() -> list[Event]:
    """Read the full TNB programme, not just the first 16 visible ticket cards."""
    html = fetch_page(TICKETS_URL, record_failure=False)
    soup = BeautifulSoup(html, "html.parser")
    state_script = next((
        script.get_text() for script in soup.select("script:not([src])")
        if "window.__INITIAL_STATE__=" in script.get_text()
    ), None)
    if not state_script:
        raise ValueError("TNB ticket programme has no initial state")
    state, _ = json.JSONDecoder().raw_decode(state_script.split("window.__INITIAL_STATE__=", 1)[1])
    events: list[Event] = []
    for item in state["instances"]["instances"]:
        venue = item["venue"]["name"]
        if not venue.startswith("TNB - "):
            continue
        date = datetime.fromtimestamp(
            item["dateStart"] / 1000, ZoneInfo("Europe/Bucharest"),
        ).replace(tzinfo=None)
        # The provider resolves these stable IDs to the canonical titled URL.
        url = f"https://www.bilet.ro/eveniment/tnb-{item['event']['id']}-{item['id']}"
        events.append(Event(item["title"], None, venue, date, url, "tnb", "theatre", None))
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Național București."""
    events: list[Event] = []
    seen: set[tuple[str, str, str]] = set()
    
    now = datetime.now()
    months_to_scrape = [
        (now.year, now.month),
        (now.year if now.month < 12 else now.year + 1, (now.month % 12) + 1),
    ]
    
    try:
        events = scrape_ticket_programme()
    except (HttpError, ValueError, KeyError) as e:
        print(f"Failed to fetch TNB ticket programme, trying official calendar: {e}")

    if not events:
        for year, month in months_to_scrape:
            events.extend(scrape_month(year, month))

    unique_events: list[Event] = []
    for event in events:
        if (event.date.year, event.date.month) in months_to_scrape:
            key = (event.title, event.date.isoformat(), event.venue)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
    
    events = [e for e in unique_events if e.date >= now.replace(hour=0, minute=0, second=0, microsecond=0)]
    events.sort(key=lambda e: e.date)
    
    return events
