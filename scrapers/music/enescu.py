import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import HttpError, fetch_page

BASE_URL = "https://festivalenescu.ro"
FESTIVAL_EVENTS_URL = f"{BASE_URL}/ro/festivalul-george-enescu/concerte"
COMPETITION_EVENTS_URL = (
    f"{BASE_URL}/ro/concursul-international-george-enescu/evenimente"
)
EVENTS_URL = COMPETITION_EVENTS_URL
EVENTS_URLS = (FESTIVAL_EVENTS_URL, COMPETITION_EVENTS_URL)
ALLOW_EMPTY_RESULTS = True  # An accessible, completed festival has no future shows.
READER_BASE_URL = "https://r.jina.ai/"
READER_HEADERS = {"X-Return-Format": "html"}

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def reader_url(url: str) -> str:
    """Route the official page through a CI-accessible HTML reader."""
    return f"{READER_BASE_URL}{url}"


def parse_date(element: Tag) -> datetime | None:
    """Parse date from concert-details element."""
    day_el = element.select_one(".concert-day")
    month_el = element.select_one(".concert-month")
    year_el = element.select_one(".concert-year")
    hour_el = element.select_one(".concert-hour")

    if not day_el or not month_el or not year_el:
        return None

    try:
        day = int(day_el.get_text(strip=True))
        month_text = month_el.get_text(strip=True).lower()
        year = int(year_el.get_text(strip=True))
        month = ROMANIAN_MONTHS.get(month_text)
        if not month:
            return None

        hour, minute = 19, 0
        if hour_el:
            time_match = re.search(r"(\d{1,2}):(\d{2})", hour_el.get_text())
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))

        return datetime(year, month, day, hour, minute)
    except (ValueError, TypeError):
        return None


def parse_venue(element: Tag) -> str:
    """Extract venue from concert-location element."""
    location_el = element.select_one(".concert-location")
    if location_el:
        text = location_el.get_text(strip=True)
        text = re.sub(r"^[^\w]+", "", text)
        if text:
            return text
    return "Festivalul George Enescu"


def parse_event(element: Tag) -> Event | None:
    """Parse a single event from the concert container."""
    details = element.select_one(".concert-details")
    preview = element.select_one(".concert-preview")

    if not details or not preview:
        return None

    title_link = preview.select_one("h2 a")
    if not title_link:
        return None

    title = title_link.get_text(strip=True)
    href = title_link.get("href", "")
    url = BASE_URL + href if href.startswith("/") else href

    event_date = parse_date(details)
    if not event_date:
        return None

    venue = parse_venue(details)

    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="Festivalul Enescu",
        category="music",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch Festival and International Competition events."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    valid_listings = 0
    blocked_listings: list[str] = []
    today = datetime.now().date()

    for events_url in EVENTS_URLS:
        try:
            for attempt in range(2):
                try:
                    html = fetch_page(
                        reader_url(events_url),
                        needs_js=False,
                        timeout=30000,
                        headers=READER_HEADERS if attempt == 0 else {
                            **READER_HEADERS, "X-No-Cache": "true",
                        },
                        record_failure=attempt == 1,
                    )
                except HttpError:
                    if attempt == 1:
                        raise
                    continue
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                if not any(marker in title.casefold() for marker in (
                    "just a moment", "attention required",
                )):
                    break
        except Exception as e:
            print(f"Failed to fetch Festivalul Enescu events from {events_url}: {e}")
            continue

        if "just a moment" in title.casefold() or "attention required" in title.casefold():
            blocked_listings.append(events_url)
            continue

        items = soup.select(".item[itemprop='blogPost']")
        if items or "evenimente" in title.casefold():
            valid_listings += 1
        for item in items:
            event = parse_event(item)
            if event and event.date.date() >= today:
                key = (event.title, event.date.isoformat())
                if key not in seen:
                    seen.add(key)
                    events.append(event)

    if blocked_listings:
        raise ValueError(f"Festivalul Enescu programme blocked: {', '.join(blocked_listings)}")
    if not valid_listings:
        raise ValueError("Festivalul Enescu returned no verifiable programme markup")
    events.sort(key=lambda e: e.date)
    return events
