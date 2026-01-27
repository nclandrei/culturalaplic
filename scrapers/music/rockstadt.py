import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://rockstadtextremefest.ro"
EVENTS_URL = f"{BASE_URL}/line-up/"

FESTIVAL_START_DAY = 27
FESTIVAL_MONTH = 7


def get_festival_year() -> int:
    """Get the festival year (current year or next if past July)."""
    now = datetime.now()
    if now.month > FESTIVAL_MONTH or (now.month == FESTIVAL_MONTH and now.day > 31):
        return now.year + 1
    return now.year


def scrape() -> list[Event]:
    """Fetch upcoming artists from Rockstadt Extreme Fest.
    
    Note: Day-by-day lineup is not yet available, so all artists are
    assigned to the first day of the festival (July 27).
    """
    events: list[Event] = []
    seen: set[str] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Rockstadt lineup: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    year = get_festival_year()
    festival_date = datetime(year, FESTIVAL_MONTH, FESTIVAL_START_DAY, 18, 0)
    
    for link in soup.select("a[href*='/team/']"):
        href = link.get("href", "")
        
        if "/team_group/" in href:
            continue
        
        if not re.search(r"/team/[\w-]+/?$", href):
            continue
        
        artist = link.get_text(strip=True)
        if not artist or len(artist) < 2:
            continue
        
        if artist in seen:
            continue
        seen.add(artist)
        
        events.append(Event(
            title=f"{artist} @ Rockstadt Extreme Fest",
            artist=artist,
            venue="Rockstadt Extreme Fest, Ghimbav",
            date=festival_date,
            url=EVENTS_URL,
            source="rockstadt",
            category="music",
            price=None,
        ))
    
    events.sort(key=lambda e: e.title)
    return events
