import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.bilet.ro"
PROMOTER_URL = f"{BASE_URL}/promoter/green-hours"
EVENTS_URL = PROMOTER_URL
MIN_EXPECTED_EVENTS = 1

MONTHS = {
    "ian": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "mai": 5,
    "iun": 6,
    "iul": 7,
    "aug": 8,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
CATEGORIES = {"concert": "music", "teatru": "theatre", "spectacol": "theatre"}


def parse_date(date_text: str, time_text: str, now: datetime | None = None) -> datetime | None:
    """Parse Bilet's Romanian card date, including its implicit year rollover."""
    match = re.search(
        r"(\d{1,2})\s+(ian|feb|mar|apr|mai|iun|iul|aug|sept|oct|nov|dec)\.?(?:\s+(\d{4}))?",
        date_text.lower(),
    )
    time_match = re.fullmatch(r"\s*([01]?\d|2[0-3]):([0-5]\d)\s*", time_text)
    if not match or not time_match:
        return None

    reference = now or datetime.now()
    explicit_year = match.group(3)
    year = int(explicit_year) if explicit_year else reference.year
    try:
        result = datetime(
            year,
            MONTHS[match.group(2)],
            int(match.group(1)),
            int(time_match.group(1)),
            int(time_match.group(2)),
        )
    except ValueError:
        return None

    today = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    if not explicit_year and result < today:
        try:
            result = result.replace(year=year + 1)
        except ValueError:
            return None
    return result


def parse_event_card(card: Tag, now: datetime | None = None) -> Event | None:
    """Parse one server-rendered event card from the promoter page."""
    category_element = card.select_one(".absolute-top-left")
    category_label = category_element.get_text(" ", strip=True).lower() if category_element else ""
    category = CATEGORIES.get(category_label)
    labels = card.select(".q-card__actions .q-item__label")
    if not category or len(labels) < 4:
        return None

    title = labels[0].get_text(" ", strip=True)
    venue = labels[1].get_text(" ", strip=True)
    event_date = parse_date(
        labels[2].get_text(" ", strip=True),
        labels[3].get_text(" ", strip=True),
        now,
    )
    href = card.get("href")
    if not title or not venue or not event_date or not isinstance(href, str):
        return None

    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    if event_date < today:
        return None

    return Event(
        title=title,
        artist=title if category == "music" else None,
        venue=venue if "green hours" in venue.casefold() else f"Green Hours - {venue}",
        date=event_date,
        url=urljoin(BASE_URL, href),
        source="greenhours",
        category=category,
        price=None,
    )


def scrape_all() -> list[Event]:
    """Fetch all upcoming Green Hours concerts and theatre performances."""
    html = fetch_page(EVENTS_URL)
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()

    for card in soup.select('a[href^="/eveniment/"]'):
        event = parse_event_card(card, now)
        if event and (event.url, event.date) not in seen:
            seen.add((event.url, event.date))
            events.append(event)

    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming Green Hours concerts."""
    return [event for event in scrape_all() if event.category == "music"]
