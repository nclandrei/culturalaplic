import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://expirat.iabilet.ro"
SCHEDULE_URL = f"{BASE_URL}/"
MIN_EXPECTED_EVENTS = 1

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}
CARD_DATE_PATTERN = re.compile(
    r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+'(\d{2}))?(?:,\s*ora\s+(\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    title = re.sub(r"^SOLD\s*OUT\s*[•·\-–]\s*", "", title, flags=re.I).strip()
    
    separators = [" • ", " · ", " - ", " – ", " | "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def parse_card_date(text: str, today: datetime) -> datetime | None:
    """Parse iaBilet card dates; the year is shown only outside the current year."""
    match = CARD_DATE_PATTERN.search(text)
    if not match:
        return None
    month = ROMANIAN_MONTHS.get(match.group(2).casefold())
    if not month:
        return None
    hour = int(match.group(4)) if match.group(4) else 0
    minute = int(match.group(5)) if match.group(5) else 0
    year = 2000 + int(match.group(3)) if match.group(3) else today.year
    try:
        event_date = datetime(year, month, int(match.group(1)), hour, minute)
        if not match.group(3) and event_date.date() < today.date():
            event_date = event_date.replace(year=year + 1)
    except ValueError:
        return None
    return event_date


def parse_card(card: Tag, today: datetime) -> Event | None:
    """Convert one iaBilet listing card into an Expirat event."""
    link = card.select_one(".desc a[href]") or card.select_one("a[href]")
    title_elem = card.select_one(".desc h1")
    date_location = card.select_one(".date-location")
    if not link or not title_elem or not date_location:
        return None

    title = " ".join(title_elem.get_text(" ", strip=True).split())
    lines = [p.get_text(" ", strip=True) for p in date_location.select("p")]
    if not title or len(lines) < 2:
        return None

    event_date = parse_card_date(lines[1], today)
    if not event_date:
        return None

    url = urljoin(BASE_URL, urlparse(link.get("href", "")).path)
    venue = lines[0].split(",", 1)[0].strip() or "Expirat"

    return Event(
        title=title,
        artist=extract_artist_from_title(title),
        venue=venue,
        date=event_date,
        url=url,
        source="expirat",
        category="music",
        price=None,
    )


def parse_events(html: str, now: datetime | None = None) -> list[Event]:
    """Parse upcoming events from the Expirat iaBilet listing."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    seen_urls: set[str] = set()
    for card in soup.select('[data-event-list="item"]'):
        event = parse_card(card, today)
        if event and event.url not in seen_urls:
            seen_urls.add(event.url)
            events.append(event)
    events.sort(key=lambda event: event.date)
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Expirat."""
    try:
        html = fetch_page(SCHEDULE_URL, needs_js=False)
    except Exception as e:
        print(f"Failed to fetch Expirat schedule: {e}")
        return []
    return parse_events(html)
