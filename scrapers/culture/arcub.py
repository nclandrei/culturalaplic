import re
from datetime import datetime, time, timedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://arcub.ro"
AGENDA_URL = f"{BASE_URL}/agenda"
MAX_RANGE_DAYS = 120

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
}

ROMANIAN_WEEKDAYS = {
    "luni": 0,
    "marți": 1,
    "marti": 1,
    "miercuri": 2,
    "joi": 3,
    "vineri": 4,
    "sâmbătă": 5,
    "sambata": 5,
    "duminică": 6,
    "duminica": 6,
}


def parse_date_range(
    date_text: str,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime] | None:
    """Parse ARCUB single dates and inclusive Romanian date ranges."""
    reference = now or datetime.now()
    today = reference.date()
    normalized = re.sub(r"[–—]", "-", date_text.casefold()).strip()

    cross_month = re.search(
        r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+(\d{4}))?\s*-\s*"
        r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+(\d{4}))?",
        normalized,
    )
    same_month = re.search(
        r"(\d{1,2})\s*-\s*(\d{1,2})\s+([a-zăâîșț]+)(?:\s+(\d{4}))?",
        normalized,
    )
    single = re.search(
        r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+(\d{4}))?",
        normalized,
    )

    if cross_month:
        start_day = int(cross_month.group(1))
        start_month = ROMANIAN_MONTHS.get(cross_month.group(2))
        start_year_raw = cross_month.group(3)
        end_day = int(cross_month.group(4))
        end_month = ROMANIAN_MONTHS.get(cross_month.group(5))
        end_year_raw = cross_month.group(6)
    elif same_month:
        start_day = int(same_month.group(1))
        end_day = int(same_month.group(2))
        start_month = end_month = ROMANIAN_MONTHS.get(same_month.group(3))
        start_year_raw = end_year_raw = same_month.group(4)
    elif single:
        start_day = end_day = int(single.group(1))
        start_month = end_month = ROMANIAN_MONTHS.get(single.group(2))
        start_year_raw = end_year_raw = single.group(3)
    else:
        return None

    if not start_month or not end_month:
        return None

    if end_year_raw:
        end_year = int(end_year_raw)
    else:
        end_year = reference.year
        try:
            candidate_end = datetime(end_year, end_month, end_day)
        except ValueError:
            return None
        if candidate_end.date() < today:
            end_year += 1

    if start_year_raw:
        start_year = int(start_year_raw)
    else:
        start_year = end_year if start_month <= end_month else end_year - 1

    try:
        start = datetime(start_year, start_month, start_day)
        end = datetime(end_year, end_month, end_day)
    except ValueError:
        return None
    if end < start:
        return None
    return start, end


def parse_opening_schedule(html: str) -> dict[int, time | None]:
    """Parse weekday ranges such as ``Miercuri–Vineri: 13:00``."""
    text_content = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    normalized = re.sub(r"[–—]", "-", text_content.casefold())
    schedule: dict[int, time | None] = {}
    pattern = re.compile(
        r"(luni|marți|marti|miercuri|joi|vineri|sâmbătă|sambata|duminică|duminica)"
        r"\s*-\s*"
        r"(luni|marți|marti|miercuri|joi|vineri|sâmbătă|sambata|duminică|duminica)"
        r"\s*:\s*(închis|inchis|\d{1,2}:\d{2})"
    )
    for match in pattern.finditer(normalized):
        first = ROMANIAN_WEEKDAYS[match.group(1)]
        last = ROMANIAN_WEEKDAYS[match.group(2)]
        value = match.group(3)
        opening = None
        if value not in {"închis", "inchis"}:
            hour, minute = map(int, value.split(":"))
            opening = time(hour, minute)
        day = first
        while True:
            schedule[day] = opening
            if day == last:
                break
            day = (day + 1) % 7
    return schedule


def _event(
    *,
    title: str,
    venue: str,
    event_date: datetime,
    url: str,
    description: str | None = None,
) -> Event:
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="arcub",
        category="culture",
        price=None,
        description=description,
        description_source="scraped" if description else None,
    )


def _card_metadata(card: BeautifulSoup) -> tuple[str, str, str, str] | None:
    link = card.select_one("a")
    title_elem = card.select_one("h3")
    spans = card.select(".meta span")
    if not link or not title_elem or not spans:
        return None
    href = link.get("href", "")
    if not href:
        return None
    url = href if href.startswith("http") else f"{BASE_URL}{href}"
    title = title_elem.get_text(" ", strip=True)
    date_text = spans[0].get_text(" ", strip=True)
    venue = spans[1].get_text(" ", strip=True) if len(spans) > 1 else "ARCUB"
    if not title or not date_text:
        return None
    return title, date_text, venue or "ARCUB", url


def _expand_open_days(
    *,
    title: str,
    venue: str,
    url: str,
    start: datetime,
    end: datetime,
    now: datetime,
    schedule: dict[int, time | None],
) -> list[Event]:
    events: list[Event] = []
    cursor = max(start.date(), now.date())
    last = min(end.date(), cursor + timedelta(days=MAX_RANGE_DAYS - 1))
    description = (
        f"Expoziție în desfășurare: {start:%d.%m.%Y}–{end:%d.%m.%Y}."
    )
    while cursor <= last:
        opening = schedule.get(cursor.weekday())
        if opening is not None:
            events.append(
                _event(
                    title=title,
                    venue=venue,
                    event_date=datetime.combine(cursor, opening),
                    url=url,
                    description=description,
                )
            )
        cursor += timedelta(days=1)
    return events


def _festival_events(
    *,
    title: str,
    url: str,
    html: str,
    start: datetime,
    end: datetime,
    now: datetime,
) -> list[Event]:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".content") or soup
    series_title = re.sub(
        r"^Program artistic\s*•\s*", "", title, flags=re.IGNORECASE
    )
    events: list[Event] = []
    for heading in content.find_all(["h2", "h3", "h4"]):
        parsed = parse_date_range(heading.get_text(" ", strip=True), now=now)
        if not parsed or parsed[0].date() != parsed[1].date():
            continue
        day = parsed[0].date()
        if day < now.date() or day < start.date() or day > end.date():
            continue
        sibling = heading.find_next_sibling()
        while sibling and sibling.name not in {"h2", "h3", "h4"}:
            if sibling.name == "ul":
                for item in sibling.find_all("li", recursive=False):
                    item_text = " ".join(item.get_text(" ", strip=True).split())
                    match = re.match(
                        r"(\d{1,2}):(\d{2})\s*[–—-]\s*\d{1,2}:\d{2}"
                        r"\s*\|\s*(.+)",
                        item_text,
                    )
                    if not match:
                        continue
                    parts = re.split(r"\s+[–—-]\s+", match.group(3), maxsplit=1)
                    if len(parts) != 2:
                        continue
                    venue, item_title = (part.strip() for part in parts)
                    events.append(
                        _event(
                            title=f"{series_title} — {item_title}",
                            venue=venue,
                            event_date=datetime(
                                day.year,
                                day.month,
                                day.day,
                                int(match.group(1)),
                                int(match.group(2)),
                            ),
                            url=url,
                        )
                    )
            sibling = sibling.find_next_sibling()
    return events


def parse_card_events(
    card: BeautifulSoup,
    detail_html: str,
    *,
    now: datetime | None = None,
    ticket_html: str | None = None,
) -> list[Event]:
    """Turn one ARCUB card into its source-advertised occurrences."""
    metadata = _card_metadata(card)
    reference = now or datetime.now()
    if not metadata:
        return []
    title, date_text, venue, url = metadata
    date_range = parse_date_range(date_text, now=reference)
    if not date_range:
        return []
    start, end = date_range

    if "program artistic" in title.casefold():
        return _festival_events(
            title=title,
            url=url,
            html=detail_html,
            start=start,
            end=end,
            now=reference,
        )

    title_times = re.findall(
        r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)",
        title,
    )
    if start.date() == end.date() and title_times:
        clean_title = re.sub(
            r"\s*\|\s*ora\b.*$", "", title, flags=re.IGNORECASE
        ).strip()
        if start.date() < reference.date():
            return []
        return [
            _event(
                title=clean_title,
                venue=venue,
                event_date=start.replace(hour=int(hour), minute=int(minute)),
                url=url,
            )
            for hour, minute in title_times
        ]

    schedule = parse_opening_schedule(detail_html)
    if schedule:
        return _expand_open_days(
            title=title,
            venue=venue,
            url=url,
            start=start,
            end=end,
            now=reference,
            schedule=schedule,
        )

    if ticket_html:
        interval_match = re.search(
            r"Intervale\s*:\s*([01]?\d|2[0-3]):([0-5]\d)",
            BeautifulSoup(ticket_html, "html.parser").get_text(" ", strip=True),
            re.IGNORECASE,
        )
        if interval_match:
            opening = time(int(interval_match.group(1)), int(interval_match.group(2)))
            return _expand_open_days(
                title=title,
                venue=venue,
                url=url,
                start=start,
                end=end,
                now=reference,
                schedule={day: opening for day in range(7)},
            )

    if start.date() == end.date() and start.date() >= reference.date():
        detail_text = BeautifulSoup(detail_html, "html.parser").get_text(" ", strip=True)
        match = re.search(
            r"\b(?:de la\s+)?ora\s+([01]?\d|2[0-3]):([0-5]\d)\b",
            detail_text,
            re.IGNORECASE,
        )
        if match:
            return [
                _event(
                    title=title,
                    venue=venue,
                    event_date=start.replace(
                        hour=int(match.group(1)), minute=int(match.group(2))
                    ),
                    url=url,
                )
            ]
    return []


def scrape() -> list[Event]:
    """Fetch source-derived ARCUB occurrences without defaulting to 19:00."""
    try:
        html = fetch_page(AGENDA_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch ARCUB events: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    seen: set[tuple[str, str, str]] = set()
    for card in soup.select(".project-box"):
        metadata = _card_metadata(card)
        if not metadata:
            continue
        _, _, _, detail_url = metadata
        try:
            detail_html = fetch_page(detail_url)
        except Exception as e:
            print(f"Failed to fetch ARCUB detail {detail_url}: {e}")
            continue

        detail_soup = BeautifulSoup(detail_html, "html.parser")
        ticket_link = detail_soup.select_one('a[href*="hubproedus.ro"]')
        ticket_html = None
        if ticket_link:
            try:
                ticket_html = fetch_page(ticket_link.get("href", ""))
            except Exception as e:
                print(f"Failed to fetch ARCUB ticket schedule: {e}")

        for event in parse_card_events(
            card,
            detail_html,
            ticket_html=ticket_html,
        ):
            key = (event.title, event.date.isoformat(), event.venue)
            if key not in seen:
                seen.add(key)
                events.append(event)

    events.sort(key=lambda event: event.date)
    return events
