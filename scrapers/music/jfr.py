"""Jazz Fan Rising scraper - curated jazz concerts via Eventbook."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

JFR_URL = "https://eventbook.ro/program/jazz-fan-rising"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(date_text: str) -> datetime | None:
    """Parse date like '22 Jan 2026  19:00' or '22 Jan 202619:00'."""
    match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*(\d{1,2}):(\d{2})", date_text)
    if not match:
        return None
    
    day, month_str, year, hour, minute = match.groups()
    month = MONTHS.get(month_str.lower()[:3])
    if not month:
        return None
    
    return datetime(int(year), month, int(day), int(hour), int(minute))


def extract_artist(title: str) -> str | None:
    """Extract artist name from JFR event title."""
    title_clean = re.sub(r"\s*-\s*la\s+Jazz\s+Fan\s+Rising.*", "", title, flags=re.IGNORECASE)
    
    separators = [" - ", " – ", ": ", " la "]
    for sep in separators:
        if sep in title_clean:
            return title_clean.split(sep)[0].strip()
    
    match = re.match(r"^([A-Z\s&]+(?:\([^)]+\))?)", title_clean)
    if match:
        return match.group(1).strip()
    
    return title_clean.strip()


def scrape() -> list[Event]:
    """Fetch upcoming JFR events in București only."""
    html = fetch_page(JFR_URL, needs_js=False)
    soup = BeautifulSoup(html, "html.parser")
    
    events: list[Event] = []
    
    for card in soup.select(".shadow.border.mb-4"):
        city_link = card.select_one('a[href*="/city/"]')
        city = city_link.get_text(strip=True) if city_link else None
        
        if city != "București":
            continue
        
        title_link = card.select_one("a.event-title")
        if not title_link:
            continue
        
        title = title_link.get_text(strip=True)
        url = title_link.get("href", "")
        if not url.startswith("http"):
            url = "https://eventbook.ro" + url
        
        venue_link = card.select_one('a[href*="/hall/"]')
        venue = venue_link.get_text(strip=True) if venue_link else "Unknown"
        
        date_el = card.select_one("h5.m-0") or card.select_one("h4")
        date_text = date_el.get_text(strip=True) if date_el else ""
        event_date = parse_date(date_text)
        
        if not event_date:
            continue
        
        artist = extract_artist(title)
        
        events.append(Event(
            title=title,
            artist=artist,
            venue=venue,
            date=event_date,
            url=url,
            source="jfr",
            category="music",
        ))
    
    return events
