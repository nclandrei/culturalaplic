import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://mare.ro"
EXHIBITIONS_URL = f"{BASE_URL}/exhibitions-2/"
MIN_EXPECTED_EVENTS = 1

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "iun": 6, "iul": 7,
    "aug": 8, "sep": 9, "oct": 10, "noi": 11, "dec": 12,
}


def parse_date_range(date_text: str) -> tuple[datetime | None, datetime | None]:
    """Parse exhibition date range.
    
    Formats:
    - Listing page: '06.02-03.05.2026'
    - Detail page: '6 februarie - 3 mai 2026.'
    """
    date_text = date_text.lower().strip().rstrip(".")
    
    dotted_pattern = r"(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})\.(\d{4})"
    match = re.search(dotted_pattern, date_text)
    if match:
        start_day, start_month, end_day, end_month, year = match.groups()
        try:
            start_date = datetime(int(year), int(start_month), int(start_day))
            end_date = datetime(int(year), int(end_month), int(end_day))
            return start_date, end_date
        except (ValueError, TypeError):
            pass
    
    text_pattern = r"(\d{1,2})\s+(\w+)\s*-\s*(\d{1,2})\s+(\w+)\s+(\d{4})"
    match = re.search(text_pattern, date_text)
    if match:
        start_day, start_month_str, end_day, end_month_str, year_str = match.groups()
        start_month = ROMANIAN_MONTHS.get(start_month_str)
        end_month = ROMANIAN_MONTHS.get(end_month_str)
        if start_month and end_month:
            try:
                start_date = datetime(int(year_str), start_month, int(start_day))
                end_date = datetime(int(year_str), end_month, int(end_day))
                return start_date, end_date
            except (ValueError, TypeError):
                pass
    
    return None, None


def scrape() -> list[Event]:
    """Fetch current and upcoming exhibitions from MARe."""
    events: list[Event] = []
    seen: set[str] = set()
    
    try:
        html = fetch_page(EXHIBITIONS_URL, needs_js=False, timeout=30000)
    except Exception as e:
        print(f"Failed to fetch MARe exhibitions: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    
    exhibition_items = soup.select("a.current__item")
    if exhibition_items:
        for item in exhibition_items:
            href = item.get("href", "")
            if not href or "/exhibition/" not in href:
                continue
            
            if href in seen:
                continue
            seen.add(href)
            
            title_elem = item.select_one("h2, h4")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title:
                continue
            
            date_elem = item.select_one(".hero__date, .card-meta--period")
            start_date, end_date = None, None
            if date_elem:
                start_date, end_date = parse_date_range(date_elem.get_text())
            
            if not end_date or end_date < now:
                continue
            
            event_date = start_date if start_date and start_date > now else now.replace(hour=11, minute=0, second=0, microsecond=0)
            
            events.append(Event(
                title=title,
                artist=None,
                venue="MARe - Muzeul de Artă Recentă",
                date=event_date,
                url=href,
                source="mare",
                category="culture",
                price=None,
            ))
    
    events.sort(key=lambda e: e.date)
    return events
