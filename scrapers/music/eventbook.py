import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://eventbook.ro"
BUCHAREST_URL = f"{BASE_URL}/city/bucuresti"
MAX_PAGES = 15


def parse_date(date_str: str) -> datetime | None:
    """Parse eventbook date format (e.g., '19 Jan 202618:00')."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    if date_str.lower().startswith("valabil") or date_str.lower().startswith("colectia"):
        return None
    
    time_text = None
    match = re.match(
        r"(\d{1,2})\s+(\w+)\s+(\d{4})(?:\s*(\d{2}:\d{2}))?",
        date_str,
    )
    if not match:
        match = re.match(r"(\w+),\s+(\d{1,2})\s+(\w+)\s+(\d{2})", date_str)
        if match:
            day = int(match.group(2))
            month_str = match.group(3)
            year = 2000 + int(match.group(4))
        else:
            return None
    else:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        time_text = match.group(4)
    
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
        "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
        "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
        "iulie": 7, "august": 8, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
    }
    
    month = months.get(month_str.lower())
    if not month:
        return None
    
    try:
        hour, minute = (0, 0)
        if time_text:
            hour, minute = map(int, time_text.split(":"))
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    title = re.sub(r"\d+\+$", "", title).strip()
    
    separators = [" - ", " – ", " | ", " / ", ": "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def get_category_from_url(url: str) -> str | None:
    """Determine category from URL path."""
    if "/music/" in url:
        return "music"
    elif "/theater/" in url:
        return "theatre"
    return None


def parse_event_card(event_row: BeautifulSoup) -> Event | None:
    """Parse a single event card from the HTML."""
    link = event_row.select_one("a.event-title")
    if not link:
        return None
    
    title_elem = link.select_one("h5")
    if not title_elem:
        return None
    
    title = re.sub(r"\d+\+$", "", title_elem.get_text(strip=True)).strip()
    url = BASE_URL + link.get("href", "")
    
    date_elem = event_row.select_one(".text-danger h5")
    if not date_elem:
        return None
    
    date_text = date_elem.get_text(strip=True)
    event_date = parse_date(date_text)
    if not event_date:
        return None
    
    venue_elem = event_row.select_one('a[href*="/hall/"]')
    venue = venue_elem.get_text(strip=True) if venue_elem else "Unknown"
    
    price = None
    price_elem = event_row.select_one("h5.text-uppercase")
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        price_match = re.search(r"(\d+(?:[.,]\d+)?)\s*lei", price_text, re.I)
        if price_match:
            price = f"{price_match.group(1)} LEI"
    
    category = get_category_from_url(url)
    if not category:
        return None
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue=venue,
        date=event_date,
        url=url,
        source="eventbook",
        category=category,
        price=price,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Eventbook."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    
    for page in range(1, MAX_PAGES + 1):
        url = BUCHAREST_URL if page == 1 else f"{BUCHAREST_URL}?page={page}"
        
        try:
            html = fetch_page(url)
        except Exception as e:
            print(f"Failed to fetch Eventbook page {page}: {e}")
            break
        
        soup = BeautifulSoup(html, "html.parser")
        
        event_links = soup.select("a.event-title")
        if not event_links:
            break
        
        for link in event_links:
            event_row = link.find_parent("div", class_="shadow") or link.find_parent("div", class_="mb-4")
            if not event_row:
                continue
            
            event = parse_event_card(event_row)
            if event and event.url not in seen_urls:
                seen_urls.add(event.url)
                events.append(event)
    
    return events
