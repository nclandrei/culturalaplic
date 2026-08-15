import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.teatrulmic.ro"
EVENTS_URL = f"{BASE_URL}/program-spectacole/"
ALLOW_EMPTY_RESULTS = True  # The official calendar explicitly confirms no shows.

ROMANIAN_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "mart": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "noi": 11, "dec": 12,
}


def parse_date(date_text: str) -> datetime | None:
    """Parse date like 'vineri 16 ian.' or 'duminică 01 mart.'"""
    match = re.search(r"(\d{1,2})\s+(\w+)\.", date_text.lower())
    if not match:
        return None
    
    day = int(match.group(1))
    month_abbr = match.group(2)
    month = ROMANIAN_MONTHS.get(month_abbr)
    if not month:
        return None
    
    year = datetime.now().year
    try:
        event_date = datetime(year, month, day)
        if event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            event_date = datetime(year + 1, month, day)
        return event_date
    except ValueError:
        return None


def parse_time(time_text: str) -> tuple[int, int] | None:
    """Parse time like '19:00' or '18:30'."""
    match = re.match(r"(\d{1,2}):(\d{2})", time_text.strip())
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def extract_sala(sala_text: str) -> str:
    """Extract sala name from text like 'Sala Studio (Str. Gabroveni 57)'."""
    match = re.match(r"(Sala\s+\w+)", sala_text)
    if match:
        return match.group(1)
    return sala_text.split("(")[0].strip()


def parse_event(event_div: BeautifulSoup) -> Event | None:
    """Parse a single event from the calendar."""
    left = event_div.select_one(".left")
    right = event_div.select_one(".right")
    if not left or not right:
        return None
    
    date_elem = left.select_one(".date")
    time_elem = left.select_one(".time")
    if not date_elem:
        return None
    
    event_date = parse_date(date_elem.get_text(strip=True))
    if not event_date:
        return None
    
    if time_elem:
        time_parts = parse_time(time_elem.get_text(strip=True))
        if time_parts:
            event_date = event_date.replace(hour=time_parts[0], minute=time_parts[1])
    
    title_elem = right.select_one(".title a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    url = title_elem.get("href", "")
    if not url.startswith("http"):
        url = BASE_URL + url
    
    author_elem = right.select_one(".director")
    author = author_elem.get_text(strip=True) if author_elem else None
    
    sala_elem = right.select_one(".sala")
    sala = extract_sala(sala_elem.get_text(strip=True)) if sala_elem else "Unknown"
    venue = f"Teatrul Mic - {sala}"
    
    return Event(
        title=title,
        artist=author,
        venue=venue,
        date=event_date,
        url=url,
        source="teatrulmic",
        category="theatre",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Mic."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Teatrul Mic events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for event_div in soup.select(".cal"):
        if "section-title" in event_div.get("class", []):
            continue
        
        event = parse_event(event_div)
        if event and event.url not in seen_urls:
            seen_urls.add(event.url)
            events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
