import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://jazzinthepark.ro"
FESTIVAL_URL = f"{BASE_URL}/"
LINEUP_URL = f"{BASE_URL}/line-up/"
COMPETITION_URL = f"{BASE_URL}/en/jazz-in-the-park-competition/"
ALLOW_EMPTY_RESULTS = True  # Annual festival; its next lineup may be unpublished.

MONTHS = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12,
}


def parse_schedule(text: str) -> tuple[datetime | None, str | None]:
    """Parse schedule text like 'DD.MM.YYYY / HH:MM - HH:MM / Stage Name'.
    
    Returns tuple of (datetime, stage) or (None, None) if no valid schedule.
    """
    match = re.match(
        r"(\d{2})\.(\d{2})\.(\d{4})\s*/\s*(\d{1,2}):(\d{2})\s*-\s*\d{1,2}:\d{2}\s*/\s*(.+)",
        text.strip(),
    )
    if not match:
        return None, None

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))
    stage = match.group(6).strip()

    try:
        return datetime(year, month, day, hour, minute), stage
    except ValueError:
        return None, None


def parse_competition_dates(text: str) -> list[datetime]:
    """Parse every advertised competition day, preserving unknown start times."""
    match = re.search(
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Z]+)\s+(\d{4})",
        text.upper(),
    )
    if not match:
        return []

    start_day, end_day, month_name, year = match.groups()
    month = MONTHS.get(month_name)
    if not month:
        return []

    try:
        start = datetime(int(year), month, int(start_day))
        end = datetime(int(year), month, int(end_day))
    except ValueError:
        return []

    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def parse_festival_dates(text: str) -> list[datetime]:
    """Read announced edition dates; leave unknown artist set times unset."""
    match = re.search(
        r"See you next year:\s*([A-Z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not match or match.group(1).upper() not in MONTHS:
        return []
    try:
        start = datetime(int(match.group(4)), MONTHS[match.group(1).upper()], int(match.group(2)))
        end = datetime(int(match.group(4)), MONTHS[match.group(1).upper()], int(match.group(3)))
    except ValueError:
        return []
    if not start <= end or (end - start).days > 7:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def scrape() -> list[Event]:
    """Fetch upcoming events from Jazz in the Park festival."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()

    try:
        html = fetch_page(LINEUP_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Jazz in the Park lineup: {e}")
        html = ""

    soup = BeautifulSoup(html, "html.parser")

    for item in soup.select(".sc_team_item"):
        title_link = item.select_one(".sc_team_item_title a")
        subtitle = item.select_one(".sc_team_item_subtitle")

        if not title_link or not subtitle:
            continue

        artist = title_link.get_text(strip=True)
        href = title_link.get("href", "")
        url = href if href.startswith("http") else BASE_URL + href

        schedule_text = subtitle.get_text(strip=True)
        event_date, stage = parse_schedule(schedule_text)

        if not event_date:
            continue

        venue = f"Parcul Etnografic - {stage}" if stage else "Parcul Etnografic"

        key = (artist, event_date.isoformat())
        if key in seen:
            continue
        seen.add(key)

        events.append(
            Event(
                title=artist,
                artist=artist,
                venue=venue,
                date=event_date,
                url=url,
                source="Jazz in the Park",
                category="music",
                price=None,
            )
        )

    try:
        competition_html = fetch_page(COMPETITION_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Jazz in the Park Competition: {e}")
        competition_html = ""

    competition_dates = parse_competition_dates(
        BeautifulSoup(competition_html, "html.parser").get_text(" ", strip=True)
    )
    for competition_date in competition_dates:
        title = f"Jazz in the Park Competition {competition_date.year}"
        key = (title, competition_date.isoformat())
        if key not in seen:
            seen.add(key)
            events.append(
                Event(
                    title=title,
                    artist=None,
                    venue="Parcul Central, Cluj-Napoca",
                    date=competition_date,
                    url=COMPETITION_URL,
                    source="Jazz in the Park",
                    category="music",
                    price=None,
                )
            )

    try:
        festival_html = fetch_page(FESTIVAL_URL, needs_js=False)
    except Exception as e:
        print(f"Failed to fetch Jazz in the Park festival dates: {e}")
    else:
        for day in parse_festival_dates(BeautifulSoup(festival_html, "html.parser").get_text(" ", strip=True)):
            if day.date() >= datetime.now().date():
                events.append(Event(
                    title=f"Jazz in the Park {day.year}",
                    artist=None,
                    venue="Parcul Etnografic, Cluj-Napoca",
                    date=day,
                    url=FESTIVAL_URL,
                    source="Jazz in the Park",
                    category="music",
                ))

    events.sort(key=lambda e: e.date)
    return events
