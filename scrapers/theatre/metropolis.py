import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrulmetropolis.ro"
EVENTS_URL = f"{BASE_URL}/program/"


def parse_date(date_text: str, time_text: str | None) -> datetime | None:
    """Parse date like '16.01' and time like '19:00'."""
    match = re.match(r"(\d{1,2})\.(\d{2})", date_text.strip())
    if not match:
        return None
    
    day = int(match.group(1))
    month = int(match.group(2))
    year = datetime.now().year
    
    hour, minute = 19, 0
    if time_text:
        time_match = re.match(r"(\d{1,2}):(\d{2})", time_text.strip())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
    
    try:
        event_date = datetime(year, month, day, hour, minute)
        if event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            event_date = datetime(year + 1, month, day, hour, minute)
        return event_date
    except ValueError:
        return None


def parse_event(row: BeautifulSoup) -> Event | None:
    """Parse a single event row."""
    date_elem = row.select_one(".cal-date")
    if not date_elem:
        return None
    
    title_elem = row.select_one(".cboxtitle a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    url = title_elem.get("href", "")
    if not url.startswith("http"):
        url = BASE_URL + url
    
    time_elem = row.select_one(".show-ora")
    time_text = time_elem.get_text(strip=True) if time_elem else None
    
    event_date = parse_date(date_elem.get_text(strip=True), time_text)
    if not event_date:
        return None
    
    sala_elem = row.select_one(".show-sala")
    sala = sala_elem.get_text(strip=True) if sala_elem else "Unknown"
    venue = f"Teatrul Metropolis - {sala}"
    
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="metropolis",
        category="theatre",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Metropolis."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Metropolis events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for row in soup.select("div.row"):
        if not row.select_one(".cal-date"):
            continue
        
        event = parse_event(row)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
