import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://jazzinthepark.ro"
LINEUP_URL = f"{BASE_URL}/line-up/"


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


def scrape() -> list[Event]:
    """Fetch upcoming events from Jazz in the Park festival."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()

    try:
        html = fetch_page(LINEUP_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Jazz in the Park events: {e}")
        return events

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

    events.sort(key=lambda e: e.date)
    return events
