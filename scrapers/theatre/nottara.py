from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://nottara.ro"
EVENTS_URL = f"{BASE_URL}/program/"


def parse_event(row: BeautifulSoup) -> Event | None:
    """Parse a single event from the program row."""
    data_date = row.get("data-fulldate")
    if not data_date:
        return None
    
    try:
        event_datetime = datetime.fromisoformat(data_date.replace("+00:00", ""))
    except ValueError:
        return None
    
    title_elem = row.select_one(".gr-ptit a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    if not title:
        return None
    
    url = title_elem.get("href", "")
    if url and not url.startswith("http"):
        url = BASE_URL + url
    
    sala_elem = row.select_one(".gr-psalan")
    hall = ""
    if sala_elem:
        spans = sala_elem.select("span")
        if len(spans) >= 2:
            hall = spans[1].get_text(strip=True)
        else:
            hall = sala_elem.get_text(strip=True)
    
    venue = f"Teatrul Nottara - Sala {hall}" if hall else "Teatrul Nottara"
    
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_datetime,
        url=url,
        source="nottara",
        category="theatre",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Nottara."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Nottara events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    now = datetime.now()
    
    for row in soup.select(".gr-show-item"):
        event = parse_event(row)
        if event and event.date >= now.replace(hour=0, minute=0, second=0, microsecond=0):
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
