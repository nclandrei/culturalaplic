import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://garana-jazz.ro"
ALLOW_EMPTY_RESULTS = True  # Annual festival; its next lineup may be unpublished.

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def get_program_url() -> str:
    """Get the current edition's program URL.
    
    Festival URLs change yearly (gjf-2025, gjf-2026, etc.).
    We try current year first, then next year if not found.
    """
    current_year = datetime.now().year
    for year in [current_year, current_year + 1]:
        return f"{BASE_URL}/gjf-{year}/"
    return f"{BASE_URL}/gjf-{current_year}/"


def parse_date_info(info_text: str, year: int) -> tuple[datetime | None, str | None]:
    """Parse date and stage from info text like 'Joi, 10 iulie / 19.00 MAIN STAGE – Poiana Lupului'.
    
    Returns (datetime, stage_name).
    """
    info_text = info_text.replace("\n", " ").strip()
    
    date_match = re.search(r"(\d{1,2})\s+(\w+)", info_text)
    if not date_match:
        return None, None
    
    day = int(date_match.group(1))
    month_name = date_match.group(2).lower()
    month = ROMANIAN_MONTHS.get(month_name)
    if not month:
        return None, None
    
    time_match = re.search(r"(\d{1,2})[.:h](\d{2})(?:\s*AM)?", info_text)
    hour, minute = 0, 0  # Midnight represents a source date with no published time.
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
    
    try:
        event_date = datetime(year, month, day, hour, minute)
    except ValueError:
        return None, None
    
    stage = None
    stage_match = re.search(r"(MAIN STAGE|EXPERIMENTAL STAGE)[^–]*–?\s*([^,]+)?", info_text)
    if stage_match:
        stage = stage_match.group(1)
        location = stage_match.group(2)
        if location:
            stage = f"{stage} – {location.strip()}"
    
    return event_date, stage


def scrape() -> list[Event]:
    """Fetch upcoming events from Gărâna Jazz Festival.
    
    Note: Festival websites change yearly, so this scraper looks for
    the current or next year's program page with announced artists.
    """
    events: list[Event] = []
    seen: set[str] = set()
    
    current_year = datetime.now().year
    program_url = None
    html = None
    festival_year = None
    
    # Try current year, previous year, and next year - prefer pages with real artists
    for year in [current_year, current_year - 1, current_year + 1]:
        try_url = f"{BASE_URL}/gjf-{year}/"
        try:
            test_html = fetch_page(try_url, needs_js=True)
            if test_html and "Line Up" in test_html:
                # Check if this page has real artists (not just TBA)
                has_real_artists = any(
                    name in test_html 
                    for name in ["EABS", "SUPERLESS", "Quartet", "Trio", "Band"]
                )
                if has_real_artists or html is None:
                    html = test_html
                    program_url = try_url
                    festival_year = year
                    if has_real_artists:
                        break
        except Exception:
            continue
    
    if not html or not program_url:
        print("Failed to find Gărâna Jazz Festival program page")
        return events
    
    if not festival_year:
        year_match = re.search(r"gjf-(\d{4})", program_url)
        festival_year = int(year_match.group(1)) if year_match else current_year
    
    soup = BeautifulSoup(html, "html.parser")
    
    for section in soup.select("section.elementor-inner-section"):
        columns = section.select(".elementor-column")
        if len(columns) < 2:
            continue
        
        artist_elem = columns[0].select_one(".ld-fh-element")
        if not artist_elem:
            continue
        artist = artist_elem.get_text(strip=True)
        
        # Skip non-artist entries
        skip_patterns = [
            "Line Up", "TBA", "JAZZ-UL", "July", "iulie", "#garana"
        ]
        if not artist or artist.startswith("#"):
            continue
        if any(pattern in artist for pattern in skip_patterns):
            continue
        if re.match(r"^\d+\s+(July|iulie)", artist, re.IGNORECASE):
            continue
        
        info_elem = columns[1].select_one(".ld-fh-element")
        if not info_elem:
            continue
        info_text = info_elem.get_text(" ", strip=True)
        
        link = section.select_one("a.elementor-button[href*='gjf-']")
        url = link.get("href", "") if link else ""
        if not url:
            url = program_url
        elif not url.startswith("http"):
            url = BASE_URL + url
        
        event_date, stage = parse_date_info(info_text, festival_year)
        if not event_date:
            continue
        
        venue = "Gărâna Jazz Festival"
        if stage:
            venue = f"Gărâna Jazz Festival – {stage}"
        
        title = f"{artist} @ Gărâna Jazz Festival"
        
        key = f"{artist}:{event_date.isoformat()}"
        if key in seen:
            continue
        seen.add(key)
        
        events.append(Event(
            title=title,
            artist=artist,
            venue=venue,
            date=event_date,
            url=url,
            source="garana",
            category="music",
            price=None,  # Festival pass required
        ))
    
    events.sort(key=lambda e: e.date)
    return events
