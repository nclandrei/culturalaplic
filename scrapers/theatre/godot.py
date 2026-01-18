import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.teatrulgodot.ro"
EVENTS_URL = f"{BASE_URL}/spectacole/"

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def parse_date(day_text: str, month_text: str, year_text: str) -> datetime | None:
    """Parse date from separate day, month, year elements."""
    try:
        day = int(day_text.strip())
    except ValueError:
        return None
    
    month_name = month_text.strip().lower()
    month = ROMANIAN_MONTHS.get(month_name)
    if not month:
        return None
    
    try:
        year = int(year_text.strip())
    except ValueError:
        year = datetime.now().year
    
    try:
        return datetime(year, month, day, 19, 0)
    except ValueError:
        return None


def parse_event(card: BeautifulSoup) -> Event | None:
    """Parse a single event card."""
    title_elem = card.select_one("h2.title a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    url = title_elem.get("href", "")
    if not url.startswith("http"):
        url = BASE_URL + url
    
    date_box = card.select_one(".home-show-box")
    if not date_box:
        return None
    
    day_elem = date_box.select_one(".hsb-box-1")
    month_elem = date_box.select_one(".hsb-box-2")
    if not day_elem or not month_elem:
        return None
    
    day_text = day_elem.get_text(strip=True)
    box2_text = month_elem.get_text(" ", strip=True)
    
    parts = box2_text.split()
    if len(parts) < 3:
        return None
    
    month_text = parts[0]
    year_text = parts[-1]
    
    event_date = parse_date(day_text, month_text, year_text)
    if not event_date:
        return None
    
    label_elem = card.select_one(".show-label")
    category_label = label_elem.get_text(strip=True).lower() if label_elem else "teatru"
    
    if category_label in ("concert", "concerte"):
        category = "music"
    else:
        category = "theatre"
    
    return Event(
        title=title,
        artist=None,
        venue="Teatrul Godot",
        date=event_date,
        url=url,
        source="godot",
        category=category,
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Godot."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    page = 1
    max_pages = 10
    
    while page <= max_pages:
        url = EVENTS_URL if page == 1 else f"{EVENTS_URL}page/{page}/"
        
        try:
            html = fetch_page(url, needs_js=True, timeout=60000)
        except Exception as e:
            print(f"Failed to fetch Teatrul Godot page {page}: {e}")
            break
        
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".show-item .about-col")
        
        if not cards:
            break
        
        for card in cards:
            event = parse_event(card)
            if event and event.date >= today:
                key = (event.title, event.date.isoformat())
                if key not in seen:
                    seen.add(key)
                    events.append(event)
        
        next_link = soup.select_one('link[rel="next"]')
        if not next_link:
            break
        
        page += 1
    
    events.sort(key=lambda e: e.date)
    return events
