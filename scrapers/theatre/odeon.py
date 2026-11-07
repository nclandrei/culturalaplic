import json
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from models import Event
from services.http import fetch_page

BASE_URL = "https://teatrul-odeon.ro"
EVENTS_URL = f"{BASE_URL}/programul-teatrului-odeon-pe-zile/"


def _clean_title(value: str) -> str:
    """Remove the age recommendation appended to EventON titles."""
    return re.sub(r"\s*\|\s*\d+\s*\+?\s*$", "", value).strip()


def _parse_event(row: Tag, today: datetime) -> Event | None:
    classes = {str(value).lower() for value in row.get("class", [])}
    if classes & {"cancelled", "canceled", "postponed"}:
        return None

    status = row.select_one("meta[itemprop='eventStatus']")
    if status and not str(status.get("content", "")).endswith("EventScheduled"):
        return None

    start = row.select_one("meta[itemprop='startDate']")
    title_element = row.select_one(".evcal_event_title")
    if not start or not title_element:
        return None
    date_match = re.match(
        r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2})",
        str(start.get("content", "")),
    )
    if not date_match:
        return None
    try:
        event_date = datetime(*(int(value) for value in date_match.groups()))
    except ValueError:
        return None
    if event_date < today:
        return None

    title = _clean_title(title_element.get_text(" ", strip=True))
    if not title:
        return None

    detail = row.select_one("a.evo_cusmeta_btn[href]")
    schema_url = row.select_one(".evo_event_schema a[itemprop='url'][href]")
    link = detail or schema_url
    url = urljoin(BASE_URL, str(link.get("href"))) if link else EVENTS_URL

    subtitle = row.select_one(".evcal_event_subtitle")
    artist = subtitle.get_text(" ", strip=True).split("|", 1)[0].strip() if subtitle else None

    location = row.select_one(".event_location_name")
    location_text = location.get_text(" ", strip=True) if location else ""
    hall_match = re.search(r"\bSala\s+[^,:]+", location_text, re.IGNORECASE)
    hall = hall_match.group(0).strip() if hall_match else None
    venue = f"Teatrul Odeon - {hall}" if hall else "Teatrul Odeon"

    price_match = re.search(r"Preț\s+bilete\s*[:]?\s*(.+)$", location_text, re.IGNORECASE)
    price = price_match.group(1).strip().rstrip(".") if price_match else None

    return Event(title, artist, venue, event_date, url, "odeon", "theatre", price)


def parse_events(html: str, now: datetime | None = None) -> list[Event]:
    """Parse the server-rendered EventON calendar, which contains explicit years."""
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for row in soup.select(".eventon_list_event"):
        event = _parse_event(row, today)
        if event and (event.title, event.date) not in seen:
            seen.add((event.title, event.date))
            events.append(event)
    return sorted(events, key=lambda event: event.date)


def parse_program(script: str, now: datetime | None = None) -> list[Event]:
    """Read the explicit performance data supplied by the official calendar embed."""
    match = re.search(r"\b(?:let|const|var)\s+PERFORMANCES\s*=\s*", script)
    if not match:
        raise ValueError("Odeon calendar embed is missing performance data")
    performances, _ = json.JSONDecoder().raw_decode(script[match.end():])
    today = (now or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[Event] = []
    seen: set[tuple[str, datetime]] = set()
    for performance in performances:
        if performance.get("status") in {"cancelled", "suspended", "postponed"}:
            continue
        if performance.get("hiddenFromPublic") or performance.get("isListed") is False:
            continue
        try:
            event_date = datetime.fromisoformat(
                f"{performance['date']}T{performance['startTime']}"
            )
        except (KeyError, ValueError):
            continue
        title = performance.get("title", "").strip()
        key = (title, event_date)
        if not title or event_date < today or key in seen:
            continue
        seen.add(key)
        # The displayed category is authoritative: some records have a stale venue.
        hall = performance.get("category") or performance.get("venue", "")
        venue = f"Teatrul Odeon - {hall}" if hall.startswith("Sala ") else "Teatrul Odeon"
        url = performance.get("detailsUrl") or performance.get("ticketUrl") or EVENTS_URL
        events.append(Event(
            title=title,
            artist=performance.get("subtitle") or None,
            venue=venue,
            date=event_date,
            url=urljoin(BASE_URL, url),
            source="odeon",
            category="theatre",
            price=performance.get("ticketPrices") or None,
        ))
    return sorted(events, key=lambda event: event.date)


def scrape() -> list[Event]:
    """Fetch upcoming performances from Teatrul Odeon's official calendar."""
    html = fetch_page(EVENTS_URL)
    soup = BeautifulSoup(html, "html.parser")
    embed = soup.select_one("script[src*='/hub/api/embed/program.js']")
    if embed:
        script = fetch_page(
            urljoin(EVENTS_URL, str(embed["src"])),
            headers={"Referer": f"{BASE_URL}/", "Origin": BASE_URL},
        )
        return parse_program(script)
    return parse_events(html)
