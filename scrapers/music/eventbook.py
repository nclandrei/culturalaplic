import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://eventbook.ro"
BUCHAREST_URL = f"{BASE_URL}/city/bucuresti"
MAX_PAGES = 50
DATE_ICON_LABELS = {"calendar_month", "schedule"}
MIN_EXPECTED_EVENTS = 1


def parse_date(date_str: str) -> datetime | None:
    """Parse an Eventbook performance date, preferring the final listed time."""
    if not date_str:
        return None

    date_str = " ".join(date_str.split())
    date_lower = date_str.lower()

    if date_lower.startswith("valabil") or date_lower.startswith("colectia"):
        return None

    match = re.search(
        r"(?:[^\W\d_]+,\s*)?(\d{1,2})\s+([^\W\d_]+)(?:\s+(\d{4}|\d{2}))?",
        date_str,
        re.UNICODE,
    )
    if not match:
        return None

    day = int(match.group(1))
    month_str = match.group(2)
    year_text = match.group(3)

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

    now = datetime.now()
    year = int(year_text) if year_text else now.year
    if year < 100:
        year += 2000

    # Some cards show both doors and show times. The final value is the actual
    # performance time; a simple card has only one value.
    time_matches = re.findall(
        r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)",
        date_str[match.end():],
    )
    hour, minute = map(int, time_matches[-1]) if time_matches else (0, 0)

    try:
        event_date = datetime(year, month, day, hour, minute)
        if not year_text and event_date < now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ):
            event_date = datetime(year + 1, month, day, hour, minute)
        return event_date
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
    
    date_text = " ".join(
        text
        for text in date_elem.stripped_strings
        if text not in DATE_ICON_LABELS
    )
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


def scrape_all() -> list[Event]:
    """Fetch upcoming music and theatre performances from Eventbook."""
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    
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
            if event and (event.url, event.date) not in seen:
                seen.add((event.url, event.date))
                events.append(event)

    return events


def scrape() -> list[Event]:
    """Fetch Bucharest music performances from Eventbook."""
    return [event for event in scrape_all() if event.category == "music"]
