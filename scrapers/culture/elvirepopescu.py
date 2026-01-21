import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://eventbook.ro"
EVENTS_URL = f"{BASE_URL}/elvirepopesco"

ENGLISH_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

EXCLUDED_TITLES = {"carnet de 10 billets", "carnet de 5 billets"}


def parse_date(date_text: str) -> datetime | None:
    """Parse date like '21 Jan 202621:00' or '21 Jan 2026 21:00'."""
    date_text = date_text.strip()
    match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*(\d{1,2}):(\d{2})", date_text)
    if not match:
        return None
    
    day, month_str, year, hour, minute = match.groups()
    month = ENGLISH_MONTHS.get(month_str.lower())
    if not month:
        return None
    
    try:
        return datetime(int(year), month, int(day), int(hour), int(minute))
    except ValueError:
        return None


def parse_price(price_text: str | None) -> str | None:
    """Extract price from 'price:27 lei' format."""
    if not price_text:
        return None
    match = re.search(r"price:\s*(\d+)\s*lei", price_text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} LEI"
    return None


def clean_title(title: str) -> str:
    """Remove age ratings like 12+, 15+ from title."""
    return re.sub(r"\s*\d+\+\s*$", "", title).strip()


def parse_event(container: BeautifulSoup) -> Event | None:
    """Parse a single event from its container."""
    title_link = container.select_one("a.event-title")
    if not title_link:
        return None
    
    title = clean_title(title_link.get_text(strip=True))
    if not title:
        return None
    
    if title.lower() in EXCLUDED_TITLES:
        return None
    
    href = title_link.get("href", "")
    if not href:
        return None
    
    if "/other/carnet" in href.lower():
        return None
    
    url = href if href.startswith("http") else BASE_URL + href
    if "?hall=" in url:
        url = url.split("?hall=")[0]
    
    date_h5 = container.select_one("h5")
    if not date_h5:
        return None
    
    date_text = date_h5.get_text(strip=True)
    if "valabil" in date_text.lower():
        return None
    
    event_date = parse_date(date_text)
    if not event_date:
        return None
    
    price_h5 = None
    for h5 in container.select("h5"):
        if "price:" in h5.get_text().lower():
            price_h5 = h5
            break
    price = parse_price(price_h5.get_text() if price_h5 else None)
    
    return Event(
        title=title,
        artist=None,
        venue="Cinema Elvire Popesco",
        date=event_date,
        url=url,
        source="elvirepopescu",
        category="culture",
        price=price,
    )


def scrape_page(page_num: int = 1) -> list[Event]:
    """Scrape a single page of events."""
    events: list[Event] = []
    
    url = EVENTS_URL if page_num == 1 else f"{BASE_URL}/hall/cinema-elvire-popesco?page={page_num}"
    
    try:
        html = fetch_page(url, needs_js=False, timeout=30000)
    except Exception as e:
        print(f"Failed to fetch Elvire Popescu page {page_num}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for container in soup.select("div.row.shadow.border"):
        event = parse_event(container)
        if event:
            events.append(event)
    
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Cinema Elvire Popesco."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    for page in range(1, 9):
        page_events = scrape_page(page)
        if not page_events:
            break
        
        for event in page_events:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    return events
