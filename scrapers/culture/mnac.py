import json
import re
from datetime import datetime, time, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.mnac.ro"
EVENTS_URL = f"{BASE_URL}/event-list/93/EVENIMENTE/67/events/1"
CURRENT_EXHIBITIONS_URL = (
    f"{BASE_URL}/public/event/getCurrentExhibitionEvent"
    "?pageNumber=1&numberOfEventPerPage=100&year=&month=-1"
)
VISITING_HOURS_URL = f"{BASE_URL}/public/text/get?nodeId=11"
MIN_EXPECTED_EVENTS = 1
EXPANSION_DAYS = 30
BUCHAREST_TZ = ZoneInfo("Europe/Bucharest")


def parse_timestamp(timestamp_ms: str) -> datetime | None:
    """Parse Unix timestamp in milliseconds to datetime."""
    try:
        ts = int(timestamp_ms)
        return (
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            .astimezone(BUCHAREST_TZ)
            .replace(tzinfo=None)
        )
    except (ValueError, TypeError, OSError):
        return None


def parse_event(container: BeautifulSoup) -> Event | None:
    """Parse a single event from listEvents container."""
    link = container.select_one("a[href^='/event/']")
    if not link:
        return None

    href = link.get("href", "")
    if not href:
        return None
    url = BASE_URL + href

    title_elem = container.select_one(".title")
    if not title_elem:
        return None
    title = title_elem.get_text(strip=True)
    if not title:
        return None

    if title.startswith("[ANULAT]"):
        return None

    date_elem = container.select_one("vbn-date-format")
    if not date_elem:
        return None
    
    start_ts = date_elem.get("ng-reflect-start-date")
    if not start_ts:
        return None
    
    event_date = parse_timestamp(start_ts)
    if not event_date:
        return None

    if event_date < datetime.now():
        return None

    event_type_elem = container.select_one(".eventType")
    event_type = event_type_elem.get_text(strip=True) if event_type_elem else None

    return Event(
        title=title,
        artist=None,
        venue="MNAC",
        date=event_date,
        url=url,
        source="mnac",
        category="culture",
        price=event_type,
    )


def parse_visiting_hours(text_html: str) -> tuple[set[int], time] | None:
    """Parse MNAC's official Wednesday–Sunday opening schedule."""
    text_content = BeautifulSoup(text_html, "html.parser").get_text(" ", strip=True)
    match = re.search(
        r"(?:miercuri|wednesday)\s*[–—-]\s*(?:duminică|duminica|sunday)"
        r"\s*[–—-]\s*(\d{1,2}):(\d{2})",
        text_content,
        re.IGNORECASE,
    )
    if not match:
        return None
    return set(range(2, 7)), time(int(match.group(1)), int(match.group(2)))


def parse_temporary_closure(
    description_html: str,
) -> tuple[datetime, datetime] | str | None:
    """Return a dated closure, ``indefinite``, or no closure notice."""
    text_content = BeautifulSoup(description_html or "", "html.parser").get_text(
        " ", strip=True
    )
    normalized = text_content.casefold()
    if not re.search(r"(?:închisă temporar|inchisa temporar|temporarily closed)", normalized):
        return None
    match = re.search(
        r"(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\s*[-–—]\s*"
        r"(\d{1,2})[./](\d{1,2})[./](\d{4})",
        normalized,
    )
    if not match:
        return "indefinite"
    end_year = int(match.group(6))
    start_year = int(match.group(3) or end_year)
    try:
        return (
            datetime(start_year, int(match.group(2)), int(match.group(1))),
            datetime(end_year, int(match.group(5)), int(match.group(4))),
        )
    except ValueError:
        return "indefinite"


def parse_exhibition_occurrences(
    data: dict,
    now: datetime | None = None,
    *,
    opening_weekdays: set[int] | None = None,
    opening_time: time = time(11, 0),
) -> list[Event]:
    """Expand one current exhibition into bounded, source-valid visiting days."""
    title = data.get("nameRO") or data.get("nameEN")
    event_id = data.get("rid")
    if not title or event_id is None:
        return []

    now = now or datetime.now()
    opening_weekdays = opening_weekdays or set(range(2, 7))
    start_date = parse_timestamp(data.get("eventStartDate"))
    end_date = parse_timestamp(data.get("eventEndDate"))
    is_permanent = data.get("permanent") is True

    if not start_date or (not is_permanent and not end_date):
        return []
    if end_date and end_date.date() < now.date():
        return []

    closure = parse_temporary_closure(data.get("descriptionRO") or data.get("descriptionEN") or "")
    if closure == "indefinite":
        return []

    event_url = f"{BASE_URL}/event/{event_id}/{quote(title, safe='')}"
    cursor = max(start_date.date(), now.date())
    horizon_end = now.date() + timedelta(days=EXPANSION_DAYS - 1)
    last = min(end_date.date(), horizon_end) if end_date else horizon_end
    range_end = end_date.strftime("%d.%m.%Y") if end_date else "permanentă"
    description = (
        f"Expoziție în desfășurare: {start_date:%d.%m.%Y}–{range_end}; "
        f"program de vizitare de la {opening_time:%H:%M}."
    )

    events: list[Event] = []
    while cursor <= last:
        occurrence = datetime.combine(cursor, opening_time)
        is_closed = (
            isinstance(closure, tuple)
            and closure[0].date() <= cursor <= closure[1].date()
        )
        if (
            cursor.weekday() in opening_weekdays
            and occurrence >= start_date
            and not is_closed
        ):
            events.append(
                Event(
                    title=title,
                    artist=None,
                    venue="MNAC",
                    date=occurrence,
                    url=event_url,
                    source="mnac",
                    category="culture",
                    price=None,
                    description=description,
                    description_source="scraped",
                )
            )
        cursor += timedelta(days=1)
    return events


def parse_exhibition(data: dict, now: datetime | None = None) -> Event | None:
    """Return the next visit occurrence for compatibility with callers/tests."""
    events = parse_exhibition_occurrences(data, now=now)
    return events[0] if events else None


def scrape_current_exhibitions() -> list[Event]:
    """Fetch ongoing exhibitions from MNAC's public JSON API."""
    try:
        visiting_response = json.loads(
            fetch_page(VISITING_HOURS_URL, needs_js=False, timeout=30000)
        )
        visiting_hours = parse_visiting_hours(
            visiting_response.get("textRO") or visiting_response.get("textEN") or ""
        )
        if not visiting_hours:
            raise ValueError("MNAC visiting hours not found")
        response_text = fetch_page(
            CURRENT_EXHIBITIONS_URL,
            needs_js=False,
            timeout=30000,
        )
        response = json.loads(response_text)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"Failed to parse MNAC current exhibitions: {e}")
        return []
    except Exception as e:
        print(f"Failed to fetch MNAC current exhibitions: {e}")
        return []

    events: list[Event] = []
    for data in response.get("eventList") or []:
        events.extend(
            parse_exhibition_occurrences(
                data,
                opening_weekdays=visiting_hours[0],
                opening_time=visiting_hours[1],
            )
        )
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events and current exhibitions from MNAC."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()

    try:
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch MNAC events: {e}")
    else:
        soup = BeautifulSoup(html, "html.parser")

        for section_id in ["#currentEvent", "#futureEvent"]:
            section = soup.select_one(section_id)
            if not section:
                continue

            for container in section.select(".listEvents"):
                event = parse_event(container)
                if event:
                    key = (event.title, event.date.isoformat())
                    if key not in seen:
                        seen.add(key)
                        events.append(event)

    for event in scrape_current_exhibitions():
        key = (event.title, event.date.isoformat())
        if key not in seen:
            seen.add(key)
            events.append(event)

    events.sort(key=lambda e: e.date)

    return events
