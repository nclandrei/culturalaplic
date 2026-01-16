import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://operanb.ro"
CALENDAR_URL = f"{BASE_URL}/calendar/"


def parse_event(event_div: BeautifulSoup, day: int, month: int, year: int) -> Event | None:
    """Parse a single event from the calendar event div."""
    title_elem = event_div.select_one(".calendar-event-title")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    if not title:
        return None
    
    url = title_elem.get("href", "")
    if url and not url.startswith("http"):
        url = BASE_URL + url
    
    time_elem = event_div.select_one(".calendar-event-time")
    hour, minute = 19, 0
    if time_elem:
        time_match = re.match(r"(\d{1,2}):(\d{2})", time_elem.get_text(strip=True))
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
    
    try:
        event_date = datetime(year, month, day, hour, minute)
    except ValueError:
        return None
    
    label_elem = event_div.select_one(".calendar-event-label")
    category_label = label_elem.get_text(strip=True) if label_elem else ""
    
    venue = "Opera Națională București"
    
    return Event(
        title=title,
        artist=category_label if category_label else None,
        venue=venue,
        date=event_date,
        url=url,
        source="operanb",
        category="music",
        price=None,
    )


def scrape_month(month: int, year: int) -> list[Event]:
    """Scrape events for a specific month."""
    events: list[Event] = []
    
    url = f"{CALENDAR_URL}?luna={month:02d}&anul={year}"
    try:
        html = fetch_page(url, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Opera NB calendar {month}/{year}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for day_div in soup.select(".calendar-day"):
        date_span = day_div.select_one(".calendar-date > span")
        if not date_span:
            continue
        
        day_text = date_span.get_text(strip=True)
        if not day_text:
            continue
        
        try:
            day = int(day_text)
        except ValueError:
            continue
        
        for event_div in day_div.select(".calendar-event"):
            event = parse_event(event_div, day, month, year)
            if event:
                events.append(event)
    
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Opera Națională București."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    now = datetime.now()
    
    for offset in range(4):
        month = now.month + offset
        year = now.year
        while month > 12:
            month -= 12
            year += 1
        
        month_events = scrape_month(month, year)
        for event in month_events:
            if event.date >= now.replace(hour=0, minute=0, second=0, microsecond=0):
                key = (event.title, event.date.isoformat())
                if key not in seen:
                    seen.add(key)
                    events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
