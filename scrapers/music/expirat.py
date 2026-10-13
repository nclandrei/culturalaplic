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


def scrape() -> list[Event]:
    """Fetch upcoming events from Expirat."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    seen_pages: set[str] = set()
    page_url = SCHEDULE_URL

    while page_url and page_url not in seen_pages:
        seen_pages.add(page_url)
        soup = BeautifulSoup(fetch_page(page_url, needs_js=False), "html.parser")
        card_times = extract_card_times(soup)
        records = extract_json_ld_events(soup)
        record_paths = {normalize_url_path(data.get("url", "")) for data in records}

        # The listing no longer embeds JSON-LD; detail pages still provide
        # explicit years, prices and start times, unlike the visible cards.
        for card in soup.select('[data-event-list="item"]'):
            link = card.select_one("a[href]")
            if not link:
                continue
            path = normalize_url_path(link["href"])
            if path in record_paths or path in seen_urls:
                continue
            detail_url = urljoin(BASE_URL, path + "/")
            detail = BeautifulSoup(fetch_page(detail_url), "html.parser")
            detail_records = extract_json_ld_events(detail)
            matching = [data for data in detail_records
                        if normalize_url_path(data.get("url", "")) == path]
            if not matching:
                raise ValueError(f"Expirat event missing structured data: {detail_url}")
            records.extend(matching)
            record_paths.add(path)

        for data in records:
            path = normalize_url_path(data.get("url", ""))
            event = parse_json_ld_event(data, card_times.get(path))
            if event and path not in seen_urls:
                seen_urls.add(path)
                events.append(event)

        more = soup.select_one('[data-event-list="more"] a[href]')
        page_url = urljoin(page_url, more["href"]) if more else ""

    events.sort(key=lambda event: event.date)
    return events
