import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.rezervari.cuibulartistilor.ro"
EVENTS_URL = BASE_URL + "/program"

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def parse_date(date_text: str) -> datetime | None:
    """Parse date like 'joi, 29 ianuarie la 21:00'."""
    match = re.search(
        r"(\d{1,2})\s+(\w+)\s+la\s+(\d{1,2}):(\d{2})",
        date_text.lower()
    )
    if not match:
        return None
    
    day = int(match.group(1))
    month_name = match.group(2)
    hour = int(match.group(3))
    minute = int(match.group(4))
    
    month = ROMANIAN_MONTHS.get(month_name)
    if not month:
        return None
    
    year = datetime.now().year
    try:
        event_date = datetime(year, month, day, hour, minute)
        if event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            event_date = datetime(year + 1, month, day, hour, minute)
        return event_date
    except ValueError:
        return None


def parse_event(card: BeautifulSoup) -> Event | None:
    """Parse a single event card."""
    title_elem = card.select_one("h2.title")
    if not title_elem:
        return None
    title = title_elem.get_text(strip=True)
    
    date_elem = card.select_one(".calendar span.text-amber")
    if not date_elem:
        return None
    event_date = parse_date(date_elem.get_text(strip=True))
    if not event_date:
        return None
    
    location_elem = card.select_one(".location span.text")
    venue = location_elem.get_text(strip=True) if location_elem else "Cuibul Artiștilor"
    
    details_link = card.select_one("a[href^='/occurence/']")
    if details_link:
        url = BASE_URL + details_link.get("href", "")
    else:
        url = EVENTS_URL
    
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="cuibul",
        category="theatre",
        price=None,
    )


def parse_program_event(card: BeautifulSoup, date_text: str) -> Event | None:
    """Parse an event from the current date-grouped program markup."""
    title_link = card.select_one("h2 a[href^='/spectacol/']")
    if not title_link:
        return None

    time_button = card.select_one("button[data-testid^='time-slot-']")
    if not time_button:
        return None
    time_match = re.search(r"(\d{1,2}:\d{2})", time_button.get_text(" ", strip=True))
    if not time_match:
        return None

    event_date = parse_date(f"{date_text} la {time_match.group(1)}")
    if not event_date:
        return None

    title = title_link.get_text(strip=True)
    href = title_link.get("href", "")
    url = BASE_URL + href if href.startswith("/") else href

    venue = "Cuibul Artiștilor"
    for span in card.select("span"):
        text = span.get_text(" ", strip=True)
        if text.startswith("Cuibul Artiștilor"):
            venue = text
            break

    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="cuibul",
        category="theatre",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Cuibul Artistilor."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Cuibul Artistilor events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    old_cards = soup.select("div.v-card.occurence")
    parsed_events = [parse_event(card) for card in old_cards]

    if not old_cards:
        parsed_events = []
        for day_section in soup.select("div.mb-8"):
            date_header = day_section.select_one("div.mx-6")
            if not date_header:
                continue
            date_text = date_header.get_text(" ", strip=True)
            for card in day_section.select("div.group.relative.z-10.mb-16"):
                parsed_events.append(parse_program_event(card, date_text))

    for event in parsed_events:
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
