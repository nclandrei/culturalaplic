import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.tnb.ro"
CALENDAR_URL = f"{BASE_URL}/ro/calendar"

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
        html = fetch_page(url, needs_js=False, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch TNB calendar for {year}/{month}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for day_elem in soup.select("div.day"):
        events.extend(parse_day(day_elem))
    
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
    
    for year, month in months_to_scrape:
        month_events = scrape_month(year, month)
        for event in month_events:
            key = (event.title, event.date.isoformat(), event.venue)
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events = [e for e in events if e.date >= now.replace(hour=0, minute=0, second=0, microsecond=0)]
    events.sort(key=lambda e: e.date)
    
    return events
