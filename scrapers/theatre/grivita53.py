import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.grivita53.ro"
EVENTS_URL = f"{BASE_URL}/repertoriu"

ROMANIAN_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "noi": 11, "dec": 12,
}


def parse_date(day_text: str, month_text: str, time_text: str) -> datetime | None:
    """Parse date from day number, month abbrev, and time."""
    try:
        day = int(day_text.strip())
    except ValueError:
        return None
    
    month = ROMANIAN_MONTHS.get(month_text.strip().lower())
    if not month:
        return None
    
    hour, minute = 19, 0
    time_match = re.match(r"(\d{1,2}):(\d{2})", time_text.strip())
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
    
    year = datetime.now().year
    try:
        event_date = datetime(year, month, day, hour, minute)
        if event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            event_date = datetime(year + 1, month, day, hour, minute)
        return event_date
    except ValueError:
        return None


def parse_event(card: BeautifulSoup) -> Event | None:
    """Parse a single event card from the calendar section."""
    header = card.select_one(".bg-black.text-white.p-4")
    if not header:
        return None
    
    day_elem = header.select_one(".text-3xl")
    month_elem = header.select_one(".text-xs.uppercase")
    time_elem = header.select_one(".text-sm.text-white\\/60")
    
    if not day_elem or not month_elem:
        return None
    
    day_text = day_elem.get_text(strip=True)
    month_text = month_elem.get_text(strip=True)
    time_text = time_elem.get_text(strip=True) if time_elem else "19:00"
    
    event_date = parse_date(day_text, month_text, time_text)
    if not event_date:
        return None
    
    title_elem = card.select_one("h3")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    if not title:
        return None
    
    url = card.get("href", "")
    if url and not url.startswith("http"):
        url = BASE_URL + url
    
    author_elem = card.select_one("p.text-xs.text-gray-500")
    author = author_elem.get_text(strip=True) if author_elem else None
    
    return Event(
        title=title,
        artist=author,
        venue="Teatrul Grivița 53",
        date=event_date,
        url=url,
        source="grivita53",
        category="theatre",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Grivița 53."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Grivița 53 events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for card in soup.select("a.snap-start"):
        event = parse_event(card)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
