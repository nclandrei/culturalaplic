import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://cafe.hardrock.com/bucharest"
EVENTS_URL = f"{BASE_URL}/event-calendar.aspx"
MAX_PAGES = 5


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    title = re.sub(r"\s*(Live\s*)?Concert\s*$", "", title, flags=re.IGNORECASE)
    
    separators = [" - ", " – ", " | ", " @ ", ": "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def parse_date(event_div: BeautifulSoup) -> datetime | None:
    """Parse date from event card's h3 data attributes."""
    date_elem = event_div.select_one("h3.calListDay")
    if not date_elem:
        return None
    
    year = date_elem.get("data-date-year-number")
    month = date_elem.get("data-date-month-number")
    day = date_elem.get("data-date-day-number")
    
    if year and month and day:
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    
    return None


def parse_price(event_div: BeautifulSoup) -> str | None:
    """Extract price from event description."""
    desc_elem = event_div.select_one(".calListDayEventDescription")
    if not desc_elem:
        return None
    
    desc_text = desc_elem.get_text(strip=True)
    
    if "free" in desc_text.lower():
        return "Free"
    
    price_match = re.search(r"(\d+)\s*lei", desc_text, re.IGNORECASE)
    if price_match:
        return f"from {price_match.group(1)} lei"
    
    if "donation" in desc_text.lower():
        return desc_text
    
    return None


def parse_event(event_div: BeautifulSoup) -> Event | None:
    """Parse a single event from HTML."""
    title_elem = event_div.select_one(".calListDayEventTitle")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    
    link_elem = event_div.select_one("a.calListDayEventLink")
    if not link_elem:
        return None
    
    href = link_elem.get("href", "")
    url = EVENTS_URL + href if href.startswith("?") else href
    
    event_date = parse_date(event_div)
    if not event_date:
        return None
    
    artist = extract_artist_from_title(title)
    price = parse_price(event_div)
    
    category_elem = event_div.select_one(".calListDayEventCategory")
    category_text = category_elem.get_text(strip=True) if category_elem else ""
    event_category = "music" if "live" in category_text.lower() else "music"
    
    return Event(
        title=title,
        artist=artist,
        venue="Hard Rock Cafe Bucharest",
        date=event_date,
        url=url,
        source="hardrock",
        category=event_category,
        price=price,
    )


def scrape_page(page_num: int = 1) -> tuple[list[Event], bool]:
    """Scrape a single page of events. Returns events and whether there's a next page."""
    url = EVENTS_URL if page_num == 1 else f"{EVENTS_URL}?pagenumber={page_num}"
    
    try:
        html = fetch_page(url, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Hard Rock Cafe page {page_num}: {e}")
        return [], False
    
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    
    for event_div in soup.select(".calListDayEvent"):
        event = parse_event(event_div)
        if event:
            events.append(event)
    
    next_page_link = soup.select_one(".calPagingNextPage a")
    has_next = next_page_link is not None
    
    return events, has_next


def scrape() -> list[Event]:
    """Fetch upcoming events from Hard Rock Cafe Bucharest."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    
    for page in range(1, MAX_PAGES + 1):
        page_events, has_next = scrape_page(page)
        
        for event in page_events:
            if event.url not in seen_urls:
                seen_urls.add(event.url)
                events.append(event)
        
        if not has_next:
            break
    
    events.sort(key=lambda e: e.date)
    
    return events
