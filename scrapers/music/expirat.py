import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

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


def normalize_url_path(url: str) -> str:
    """Return a stable path for matching cards to their JSON-LD event."""
    return urlparse(urljoin(BASE_URL, url)).path.rstrip("/")


def extract_card_times(soup: BeautifulSoup) -> dict[str, tuple[int, int]]:
    """Extract advertised start times from iaBilet event cards."""
    times: dict[str, tuple[int, int]] = {}
    for card in soup.select('[data-event-list="item"]'):
        link = card.select_one("a[href]")
        if not link:
            continue
        match = re.search(
            r"\bora\s+(\d{1,2}):(\d{2})",
            card.get_text(" ", strip=True),
            re.IGNORECASE,
        )
        if match:
            times[normalize_url_path(link.get("href", ""))] = (
                int(match.group(1)),
                int(match.group(2)),
            )
    return times


def extract_json_ld_events(soup: BeautifulSoup) -> list[dict]:
    """Extract event records embedded by iaBilet."""
    records: list[dict] = []
    for script in soup.select('script[type="application/ld+json"]'):
        text = script.string
        if not text:
            continue
        text = text.replace("/*<![CDATA[*/", "").replace("/*]]>*/", "").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            records.append(data)
    return records


def parse_json_ld_event(
    data: dict,
    start_time: tuple[int, int] | None = None,
) -> Event | None:
    """Convert an iaBilet JSON-LD record into an Expirat event."""
    title = data.get("name", "").strip()
    url = data.get("url", "")
    start_date = data.get("startDate", "")
    if not title or not url or not start_date:
        return None

    try:
        event_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    event_date = event_date.replace(tzinfo=None)
    if start_time:
        event_date = event_date.replace(hour=start_time[0], minute=start_time[1])

    location = data.get("location", {})
    venue = location.get("name", "Expirat") if isinstance(location, dict) else "Expirat"

    offers = data.get("offers", {})
    if isinstance(offers, list):
        offers = next((offer for offer in offers if isinstance(offer, dict)), {})
    price = None
    if isinstance(offers, dict) and offers.get("price") not in (None, ""):
        price = f"{offers['price']} {offers.get('priceCurrency', 'RON')}"

    return Event(
        title=title,
        artist=extract_artist_from_title(title),
        venue=venue,
        date=event_date,
        url=url,
        source="expirat",
        category="music",
        price=price,
    )


ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def parse_card_event(card, now: datetime | None = None) -> Event | None:
    """Parse an iaBilet whitelabel card when the page has no JSON-LD."""
    link = card.select_one(".desc a[href]") or card.select_one("a[href]")
    title_elem = card.select_one("h1")
    date_location = card.select_one(".date-location")
    if not link or not title_elem or not date_location:
        return None

    title = title_elem.get_text(" ", strip=True)
    text = " ".join(date_location.get_text(" ", strip=True).split())
    match = re.search(
        r"\b(\d{1,2})\s+([a-zăâîșț]+)(?:\s+'(\d{2}))?",
        text.casefold(),
    )
    if not title or not match:
        return None
    month = ROMANIAN_MONTHS.get(match.group(2))
    if not month:
        return None

    now = now or datetime.now()
    if match.group(3):
        year = 2000 + int(match.group(3))
    else:
        year = now.year
        if (month, int(match.group(1))) < (now.month, now.day):
            year += 1
    time_match = re.search(r"\bora\s+(\d{1,2}):(\d{2})", text) or re.search(
        r"\bacces de la\s+(\d{1,2}):(\d{2})", text
    )
    hour, minute = (
        (int(time_match.group(1)), int(time_match.group(2)))
        if time_match else (20, 0)
    )
    try:
        event_date = datetime(year, month, int(match.group(1)), hour, minute)
    except ValueError:
        return None

    venue_elem = date_location.select_one("p")
    venue = venue_elem.get_text(" ", strip=True).split(",")[0] if venue_elem else "Expirat"
    path = urlparse(urljoin(BASE_URL, link.get("href", ""))).path
    return Event(
        title=title,
        artist=(
            title_elem.strong.get_text(" ", strip=True)
            if title_elem.strong else extract_artist_from_title(title)
        ),
        venue=venue or "Expirat",
        date=event_date,
        url=urljoin(BASE_URL, path),
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
    
    card_times = extract_card_times(soup)
    for data in extract_json_ld_events(soup):
        event_url = data.get("url", "")
        event = parse_json_ld_event(
            data,
            card_times.get(normalize_url_path(event_url)),
        )
        if event and event.url not in seen_urls:
            seen_urls.add(event.url)
            events.append(event)

    if not events:
        for card in soup.select('[data-event-list="item"]'):
            event = parse_card_event(card)
            if event and event.url not in seen_urls:
                seen_urls.add(event.url)
                events.append(event)

    events.sort(key=lambda event: event.date)
    return events
