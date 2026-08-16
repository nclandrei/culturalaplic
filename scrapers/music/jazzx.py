import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://plai.ro/jazz"
ALLOW_EMPTY_RESULTS = True  # The current festival program is already in the past.


def get_program_url() -> str | None:
    """Get the current edition's program URL.
    
    Festival URLs change yearly (program-2025.html, program-2026.html, etc.).
    Try current year first, then next year.
    """
    current_year = datetime.now().year
    for year in [current_year, current_year + 1, current_year - 1]:
        url = f"{BASE_URL}/program-{year}.html"
        try:
            html = fetch_page(url, needs_js=False)
            if html and "JAZZx" in html:
                return url, year, html
        except Exception:
            continue
    return None, None, None


def parse_jamzz_line(line: str, year: int) -> Event | None:
    """Parse JAMzz format: 'DD.MM | HH:MM – Venue – Artist'."""
    match = re.match(
        r"(\d{1,2})\.(\d{2})\s*\|\s*(\d{1,2}):(\d{2})\s*[–-]\s*(.+?)\s*[–-]\s*(.+)",
        line.strip()
    )
    if not match:
        return None
    
    day, month, hour, minute, venue, artist = match.groups()
    try:
        event_date = datetime(year, int(month), int(day), int(hour), int(minute))
    except ValueError:
        return None
    
    return Event(
        title=f"{artist.strip()} @ JAZZx JAMzz",
        artist=artist.strip(),
        venue=f"JAZZx JAMzz – {venue.strip()}",
        date=event_date,
        url=f"{BASE_URL}/program-{year}.html",
        source="jazzx",
        category="music",
        price=None,
    )


def parse_showcase_events(text: str, year: int) -> list[Event]:
    """Parse all JAZZx Showcase events from the full text."""
    events = []
    
    showcase_match = re.search(
        r"JAZZx Showcase.*?(?=\d+\s*[–-]\s*\d+\.\d+\s+JAZZx Festival|$)",
        text, re.DOTALL
    )
    if not showcase_match:
        return events
    
    showcase_text = showcase_match.group(0)
    
    current_day = None
    current_month = None
    
    for line in showcase_text.split("\n"):
        line = line.strip()
        
        date_match = re.match(r"(\d{1,2})\.(\d{2})\s*\|", line)
        if date_match:
            current_day = int(date_match.group(1))
            current_month = int(date_match.group(2))
        
        for match in re.finditer(r"(\d{1,2}):(\d{2}):\s*([^|]+?)(?=\s*\||$)", line):
            hour, minute, artist = match.groups()
            artist = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", artist.strip())
            if not artist or not current_day:
                continue
            
            try:
                event_date = datetime(year, current_month, current_day, int(hour), int(minute))
            except ValueError:
                continue
            
            events.append(Event(
                title=f"{artist} @ JAZZx Showcase",
                artist=artist,
                venue="JAZZx Showcase – Iulius Town Timișoara",
                date=event_date,
                url=f"{BASE_URL}/program-{year}.html",
                source="jazzx",
                category="music",
                price=None,
            ))
    
    return events


def _parse_current_datetime(
    date_text: str, time_text: str, *, after_midnight: bool = False
) -> datetime | None:
    date_match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_text.strip())
    time_match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    if not date_match or not time_match:
        return None

    day, month, year = map(int, date_match.groups())
    hour, minute = map(int, time_match.groups())
    try:
        event_date = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    if after_midnight and hour == 0:
        event_date += timedelta(days=1)
    return event_date


def _stage_details(stage) -> tuple[str, str, str | None]:
    heading = stage.select_one(".jazzx-program__stage-name")
    if not heading:
        return "", "", None

    direct_text = " ".join(
        text.strip() for text in heading.find_all(string=True, recursive=False) if text.strip()
    )
    if direct_text:
        stage_name = direct_text
    else:
        stage_name = ""
        for child in heading.find_all(recursive=False):
            if "jazzx-program__stage-venue" not in child.get("class", []):
                stage_name = child.get_text(" ", strip=True)
                break

    venue_elem = heading.select_one(".jazzx-program__stage-venue")
    hours_elem = heading.select_one(".jazzx-program__stage-hours")
    hours = hours_elem.get_text(" ", strip=True) if hours_elem else None
    venue = venue_elem.get_text(" ", strip=True) if venue_elem else ""
    if hours:
        venue = venue.replace(hours, "")
    return stage_name, venue.strip(" ·"), hours


def parse_current_layout(soup: BeautifulSoup, program_url: str) -> list[Event]:
    """Parse the class-based program layout currently published by JAZZx."""
    program = soup.select_one(".jazzx-program")
    if not program:
        return []

    events: list[Event] = []
    for block in program.find_all("section", class_="jazzx-program__block", recursive=False):
        title_elem = block.select_one(".jazzx-program__title")
        if not title_elem:
            continue

        section = title_elem.get_text(" ", strip=True)
        section_key = section.casefold()
        subtitle = block.select_one(".jazzx-program__subtitle")
        section_venue = subtitle.get_text(" ", strip=True) if subtitle else ""

        for day in block.find_all("article", class_="jazzx-program__day", recursive=False):
            date_elem = day.select_one(".jazzx-program__date-heading")
            if not date_elem:
                continue
            date_text = date_elem.get_text(" ", strip=True)

            stages = day.find_all("div", class_="jazzx-program__stage", recursive=False)
            if stages:
                for stage in stages:
                    stage_name, stage_venue, stage_hours = _stage_details(stage)
                    venue_parts = [part for part in [stage_name, stage_venue] if part]
                    venue = "JAZZx Festival"
                    if venue_parts:
                        venue += " – " + " – ".join(venue_parts)

                    for item in stage.select("li"):
                        artist_elem = item.select_one(".jazzx-program__artist")
                        time_elem = item.select_one(".jazzx-program__time")
                        time_text = (
                            time_elem.get_text(" ", strip=True) if time_elem else stage_hours
                        )
                        if not artist_elem or not time_text:
                            continue

                        artist = artist_elem.get_text(" ", strip=True)
                        event_date = _parse_current_datetime(
                            date_text,
                            time_text,
                            after_midnight="nocturnal" in stage_name.casefold(),
                        )
                        if not artist or not event_date:
                            continue

                        events.append(
                            Event(
                                title=f"{artist} @ JAZZx Festival",
                                artist=artist,
                                venue=venue,
                                date=event_date,
                                url=program_url,
                                source="jazzx",
                                category="music",
                                price=None,
                            )
                        )
                continue

            for item in day.select("li"):
                artist_elem = item.select_one(".jazzx-program__artist")
                time_elem = item.select_one(".jazzx-program__time")
                if not artist_elem or not time_elem:
                    continue

                artist = artist_elem.get_text(" ", strip=True)
                event_date = _parse_current_datetime(
                    date_text, time_elem.get_text(" ", strip=True)
                )
                if not artist or not event_date:
                    continue

                if section_key == "jamzz":
                    label = "JAZZx JAMzz"
                    venue_elem = item.select_one(".jazzx-program__venue")
                    item_venue = venue_elem.get_text(" ", strip=True) if venue_elem else ""
                elif section_key == "jazzx now":
                    label = "JAZZx NOW"
                    item_venue = section_venue
                else:
                    label = section
                    item_venue = section_venue

                venue = label
                if item_venue:
                    venue += f" – {item_venue}"
                events.append(
                    Event(
                        title=f"{artist} @ {label}",
                        artist=artist,
                        venue=venue,
                        date=event_date,
                        url=program_url,
                        source="jazzx",
                        category="music",
                        price=None,
                    )
                )

    return events


def parse_festival_section(soup: BeautifulSoup, year: int) -> list[Event]:
    """Parse the main festival section with days, stages, and artists."""
    events = []
    content = soup.select_one(".entry-content")
    if not content:
        return events
    
    current_date = None
    current_stage = None
    
    for p in content.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not text:
            continue
        
        day_match = re.search(r"(?:Friday|Saturday|Sunday),?\s*(\d{1,2})\.(\d{2})", text, re.IGNORECASE)
        if day_match:
            day, month = int(day_match.group(1)), int(day_match.group(2))
            current_date = (month, day)
        
        stage_match = re.search(
            r"(Main Stage|Nocturnal Stage|Spoken Word Stage|Masterclasses)\s*[–-]\s*([^0-9|]+)",
            text
        )
        if stage_match:
            stage_name = stage_match.group(1)
            location = stage_match.group(2).strip()
            current_stage = f"{stage_name} – {location}"
            
            nocturnal_match = re.search(r"\|\s*(\d{1,2}):(\d{2})\s*\|\s*(.+)$", text)
            if nocturnal_match and current_date:
                hour, minute, artist = nocturnal_match.groups()
                month, day = current_date
                hour_int = int(hour)
                event_day = day + 1 if hour_int == 0 else day
                try:
                    event_date = datetime(year, month, event_day, hour_int, int(minute))
                except ValueError:
                    continue
                
                events.append(Event(
                    title=f"{artist.strip()} @ JAZZx Festival",
                    artist=artist.strip(),
                    venue=f"JAZZx Festival – {current_stage}",
                    date=event_date,
                    url=f"{BASE_URL}/program-{year}.html",
                    source="jazzx",
                    category="music",
                    price=None,
                ))
                continue
        
        for time_match in re.finditer(r"(\d{1,2}):(\d{2})\s+([^0-9]+?)(?=\s*\d{1,2}:\d{2}\s|$)", text):
            if not current_date or not current_stage:
                continue
            hour, minute, artist = time_match.groups()
            artist = artist.strip()
            if not artist:
                continue
            month, day = current_date
            hour_int = int(hour)
            event_day = day + 1 if hour_int == 0 else day
            try:
                event_date = datetime(year, month, event_day, hour_int, int(minute))
            except ValueError:
                continue
            
            events.append(Event(
                title=f"{artist} @ JAZZx Festival",
                artist=artist,
                venue=f"JAZZx Festival – {current_stage}",
                date=event_date,
                url=f"{BASE_URL}/program-{year}.html",
                source="jazzx",
                category="music",
                price=None,
            ))
    
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from JAZZx Festival (Timișoara)."""
    events: list[Event] = []
    seen: set[str] = set()
    
    program_url, year, html = get_program_url()
    if not html or not year:
        print("Failed to find JAZZx program page")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".entry-content")
    if not content:
        return events
    
    full_text = content.get_text("\n", strip=True)

    for event in parse_current_layout(soup, program_url):
        key = f"{event.artist}:{event.date.isoformat()}"
        if key not in seen:
            seen.add(key)
            events.append(event)
    
    for line in full_text.split("\n"):
        if re.match(r"\d{1,2}\.\d{2}\s*\|\s*\d{1,2}:\d{2}\s*[–-]", line):
            event = parse_jamzz_line(line, year)
            if event:
                key = f"{event.artist}:{event.date.isoformat()}"
                if key not in seen:
                    seen.add(key)
                    events.append(event)
    
    for event in parse_showcase_events(full_text, year):
        key = f"{event.artist}:{event.date.isoformat()}"
        if key not in seen:
            seen.add(key)
            events.append(event)
    
    festival_events = parse_festival_section(soup, year)
    for event in festival_events:
        key = f"{event.artist}:{event.date.isoformat()}"
        if key not in seen:
            seen.add(key)
            events.append(event)
    
    events.sort(key=lambda e: e.date)
    return events
