import json
import re
from datetime import datetime
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page, fetch_page_with_reader_fallback

BASE_URL = "https://quantic.pub"
EVENTS_URL = f"{BASE_URL}/evenimente/"
TICKET_HOSTS = (
    "bilete.quantic.pub",
    "iabilet.ro",
    "ticketbox.ro",
    "entertix.ro",
    "ambilet.ro",
    "bilet.ro",
)

ROMANIAN_MONTHS = {
    "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iunie": 6,
    "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
    "ian": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "iun": 6,
    "iul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "noi": 11,
    "nov": 11,
    "dec": 12,
}


def get_month_url(year: int, month: int) -> str:
    """Get the URL for a specific month's calendar."""
    return f"{BASE_URL}/evenimente/month/{year}-{month:02d}/"


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    separators = [" – ", " - ", " | ", " @ ", ": "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def find_ticket_url(html: str) -> str | None:
    """Find the first recognized ticketing link on a Quantic detail page."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        host = urlparse(href).hostname or ""
        if any(host == suffix or host.endswith(f".{suffix}") for suffix in TICKET_HOSTS):
            return href
    return None


def _json_ld_event_start(soup: BeautifulSoup) -> datetime | None:
    def find_event(value):
        if isinstance(value, dict):
            if value.get("@type") == "Event" and value.get("startDate"):
                return value.get("startDate")
            for child in value.values():
                result = find_event(child)
                if result:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = find_event(child)
                if result:
                    return result
        return None

    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        raw = raw.replace("/*<![CDATA[*/", "").replace("/*]]>*/", "").strip()
        try:
            start_value = find_event(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue
        if not start_value:
            continue
        try:
            parsed = datetime.fromisoformat(str(start_value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def parse_ticket_datetime(html: str, ticket_url: str) -> datetime | None:
    """Parse only an unambiguous show datetime from a linked ticket page."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    event_date = _json_ld_event_start(soup)

    if event_date is None:
        time_elem = soup.select_one("time[datetime]")
        raw_datetime = time_elem.get("datetime", "") if time_elem else ""
        try:
            event_date = datetime.fromisoformat(
                raw_datetime.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            event_date = None

    if event_date is None:
        date_match = re.search(
            r"\b(\d{1,2})\s+([a-zăâîșț]+)(?:\s+(\d{4}))?\b",
            text.casefold(),
        )
        if date_match:
            month = ROMANIAN_MONTHS.get(date_match.group(2))
            if month:
                year = int(date_match.group(3) or datetime.now().year)
                try:
                    event_date = datetime(year, month, int(date_match.group(1)))
                except ValueError:
                    event_date = None

    if event_date is None:
        return None

    show_patterns = (
        r"\bSTART\s+SHOW\s*:\s*([01]?\d|2[0-3]):([0-5]\d)\b",
        r"\bEvent\s+hour\s*:?\s*([01]?\d|2[0-3]):([0-5]\d)\b",
        r"\bora\s*([01]?\d|2[0-3]):([0-5]\d)\b",
    )
    for pattern in show_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return event_date.replace(
                hour=int(match.group(1)), minute=int(match.group(2))
            )

    if event_date.hour or event_date.minute:
        return event_date
    return None


def enrich_event_from_ticket(event: Event) -> None:
    """Override a calendar access time when its ticket page states a show time."""
    detail_html = fetch_page_with_reader_fallback(
        event.url,
        expected_text="tribe-events",
    )
    ticket_url = find_ticket_url(detail_html)
    if not ticket_url:
        return
    ticket_html = fetch_page(ticket_url)
    ticket_datetime = parse_ticket_datetime(ticket_html, ticket_url)
    if ticket_datetime:
        event.date = ticket_datetime


def parse_datetime(
    time_elem: BeautifulSoup,
    visible_start_elem: BeautifulSoup | None = None,
) -> datetime | None:
    """Combine the tooltip's calendar date with its explicit start time."""
    if not time_elem:
        return None
    
    datetime_attr = time_elem.get("datetime")
    if not datetime_attr:
        return None

    try:
        event_date = datetime.strptime(datetime_attr, "%Y-%m-%d")
    except ValueError:
        return None

    if visible_start_elem:
        start_attr = visible_start_elem.get("datetime", "")
        try:
            start_time = datetime.strptime(start_attr, "%H:%M").time()
            return datetime.combine(event_date.date(), start_time)
        except ValueError:
            pass

    match = re.search(
        r"@\s*(\d{1,2}):(\d{2})\s*(am|pm)",
        time_elem.get_text(" ", strip=True),
        re.IGNORECASE,
    )
    if match:
        hour = int(match.group(1)) % 12
        if match.group(3).lower() == "pm":
            hour += 12
        return event_date.replace(hour=hour, minute=int(match.group(2)))

    return event_date


def parse_event(event_article: BeautifulSoup, soup: BeautifulSoup) -> Event | None:
    """Parse a single event from the calendar."""
    link = event_article.select_one("a.tribe-events-calendar-month__calendar-event-title-link")
    if not link:
        return None
    
    title = link.get_text(strip=True)
    url = link.get("href", "")
    
    tooltip_selector = event_article.select_one("[data-tooltip-content]")
    if not tooltip_selector:
        return None
    
    tooltip_id = tooltip_selector.get("data-tooltip-content")
    if not tooltip_id:
        return None
    
    tooltip = soup.select_one(tooltip_id)
    if not tooltip:
        return None
    
    time_elem = tooltip.select_one("time[datetime]")
    visible_start_elem = event_article.select_one(
        ".tribe-events-calendar-month__calendar-event-datetime time[datetime]"
    )
    event_date = parse_datetime(time_elem, visible_start_elem)
    if not event_date:
        return None
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue="Quantic",
        date=event_date,
        url=url,
        source="quantic",
        category="music",
        price=None,
    )


def parse_multiday_event(event_article: BeautifulSoup, soup: BeautifulSoup) -> Event | None:
    """Parse a multiday event from the calendar."""
    link = event_article.select_one("a[data-js='tribe-events-tooltip']")
    if not link:
        return None
    
    title_elem = event_article.select_one(".tribe-events-calendar-month__multiday-event-bar-title")
    if not title_elem:
        title_elem = event_article.select_one(".tribe-events-calendar-month__multiday-event-hidden-title")
    
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    url = link.get("href", "")
    
    tooltip_id = link.get("data-tooltip-content")
    if not tooltip_id:
        return None
    
    tooltip = soup.select_one(tooltip_id)
    if not tooltip:
        return None
    
    time_elem = tooltip.select_one("time[datetime]")
    event_date = parse_datetime(time_elem)
    if not event_date:
        return None
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue="Quantic",
        date=event_date,
        url=url,
        source="quantic",
        category="music",
        price=None,
    )


def scrape_month(year: int, month: int) -> list[Event]:
    """Scrape events for a specific month."""
    events: list[Event] = []
    
    url = get_month_url(year, month)
    try:
        html = fetch_page_with_reader_fallback(
            url,
            expected_text="tribe-events-calendar-month__calendar-event",
        )
    except Exception as e:
        print(f"Failed to fetch Quantic {year}-{month:02d}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for event_article in soup.select("article.tribe-events-calendar-month__calendar-event"):
        event = parse_event(event_article, soup)
        if event:
            events.append(event)
    
    for event_article in soup.select("article.tribe-events-calendar-month__multiday-event"):
        if "tribe-events-calendar-month__multiday-event--start" not in event_article.get("class", []):
            continue
        event = parse_multiday_event(event_article, soup)
        if event:
            events.append(event)
    
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Quantic for current and next month."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    
    now = datetime.now()
    current_month = now.replace(day=1)
    next_month = current_month + relativedelta(months=1)
    
    for date in [current_month, next_month]:
        month_events = scrape_month(date.year, date.month)
        for event in month_events:
            if event.url not in seen_urls:
                seen_urls.add(event.url)
                events.append(event)

    for event in events:
        try:
            enrich_event_from_ticket(event)
        except Exception as e:
            print(f"Failed to verify Quantic ticket time for {event.url}: {e}")
    
    events.sort(key=lambda e: e.date)
    
    return events
