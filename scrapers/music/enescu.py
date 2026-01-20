import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://festivalenescu.ro"
EVENTS_URL = f"{BASE_URL}/ro/festivalul-george-enescu/concerte"

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


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
    """Fetch upcoming events from Festivalul George Enescu."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()

    try:
        html = fetch_page(
            EVENTS_URL,
            needs_js=True,
            click_selector="button.inftabs-more",
            click_count=20,
        )
    except Exception as e:
        print(f"Failed to fetch Festivalul Enescu events: {e}")
        return events

    soup = BeautifulSoup(html, "html.parser")

    for item in soup.select(".item[itemprop='blogPost']"):
        event = parse_event(item)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)

    events.sort(key=lambda e: e.date)
    return events
