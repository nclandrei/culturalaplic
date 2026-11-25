import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://expirat.iabilet.ro"
SCHEDULE_URL = f"{BASE_URL}/"
MIN_EXPECTED_EVENTS = 1


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    title = re.sub(r"^SOLD\s*OUT\s*[•·\-–]\s*", "", title, flags=re.I).strip()
    
    separators = [" • ", " · ", " - ", " – ", " | "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}
CARD_DATE = re.compile(
    r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+'(\d{2}))?"
    r"(?:,\s*ora\s+(\d{1,2}):(\d{2}))?"
    r"(?:\s+acces\s+de\s+la\s+(\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)


def parse_card_date(text: str, now: datetime) -> datetime | None:
    """Parse "joi, 26 noiembrie, ora 21:30 acces de la 20:00" (year shown as '27)."""
    match = CARD_DATE.search(" ".join(text.split()))
    if not match:
        return None
    month = ROMANIAN_MONTHS.get(match.group(2).lower())
    if not month:
        return None
    day = int(match.group(1))
    if match.group(4):
        hour, minute = int(match.group(4)), int(match.group(5))
    elif match.group(6):
        hour, minute = int(match.group(6)), int(match.group(7))
    else:
        hour, minute = 20, 0
    try:
        if match.group(3):
            return datetime(2000 + int(match.group(3)), month, day, hour, minute)
        event_date = datetime(now.year, month, day, hour, minute)
        if event_date.date() < now.date():
            event_date = event_date.replace(year=now.year + 1)
        return event_date
    except ValueError:
        return None


def parse_card(card: Tag, now: datetime) -> Event | None:
    """Convert an iaBilet whitelabel event card into an Expirat event."""
    link = card.select_one(".desc a[href]") or card.select_one("a[href]")
    title_el = card.select_one("h1")
    paragraphs = card.select(".date-location p")
    if not link or not title_el or not paragraphs:
        return None
    title = " ".join(title_el.get_text(" ", strip=True).split())
    event_date = parse_card_date(paragraphs[-1].get_text(" ", strip=True), now)
    if not title or not event_date:
        return None
    venue = "Expirat"
    if len(paragraphs) > 1:
        venue = paragraphs[0].get_text(" ", strip=True).split(",")[0].strip() or venue
    url = urljoin(BASE_URL, urlparse(link.get("href", "")).path)
    return Event(
        title=title,
        artist=extract_artist_from_title(
            title_el.strong.get_text(" ", strip=True) if title_el.strong else title
        ),
        venue=venue,
        date=event_date,
        url=url,
        source="expirat",
        category="music",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Expirat."""
    events: list[Event] = []
    seen_urls: set[str] = set()

    try:
        html = fetch_page(SCHEDULE_URL, needs_js=False)
    except Exception as e:
        print(f"Failed to fetch Expirat schedule: {e}")
        return events

    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    for card in soup.select('[data-event-list="item"]'):
        event = parse_card(card, now)
        if event and event.url not in seen_urls:
            seen_urls.add(event.url)
            events.append(event)

    events.sort(key=lambda event: event.date)
    return events
