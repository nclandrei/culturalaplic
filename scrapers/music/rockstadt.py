import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

SCHEDULE_URL = (
    "https://bilete.rockstadtextremefest.ro/"
    "bilete-rockstadt-extreme-fest-2026-118254/?direct=true"
)
ALLOW_EMPTY_RESULTS = True  # Annual festival; its next lineup may be unpublished.


def scrape() -> list[Event]:
    """Fetch explicitly scheduled Rockstadt Extreme Fest occurrences."""
    events: list[Event] = []
    seen: set[tuple[str, datetime, str]] = set()
    
    try:
        html = fetch_page(SCHEDULE_URL, needs_js=False)
    except Exception as e:
        print(f"Failed to fetch Rockstadt schedule: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")

    for day in soup.select("[data-role='lineup'][id]"):
        try:
            festival_day = datetime.strptime(day.get("id", ""), "%Y-%m-%d")
        except ValueError:
            continue

        for panel in day.select(".panel"):
            stage_elem = panel.select_one(".panel-title")
            table = panel.select_one("table")
            if not stage_elem or not table:
                continue
            stage = stage_elem.get_text(" ", strip=True)

            for row in table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                artist = cells[0].get_text(" ", strip=True)
                interval = cells[1].get_text(" ", strip=True)
                time_match = re.match(r"(\d{1,2}):(\d{2})", interval)
                if not artist or not time_match:
                    continue

                hour, minute = map(int, time_match.groups())
                try:
                    event_date = festival_day.replace(hour=hour, minute=minute)
                except ValueError:
                    continue
                if hour < 5:
                    event_date += timedelta(days=1)

                key = (artist, event_date, stage)
                if key in seen:
                    continue
                seen.add(key)

                events.append(
                    Event(
                        title=f"{artist} @ Rockstadt Extreme Fest",
                        artist=artist,
                        venue=f"Rockstadt Extreme Fest, Ghimbav – {stage}",
                        date=event_date,
                        url=SCHEDULE_URL,
                        source="rockstadt",
                        category="music",
                        price=None,
                    )
                )

    events.sort(key=lambda e: (e.date, e.title))
    return events
