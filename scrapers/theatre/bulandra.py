import json
import re
from datetime import datetime

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.bulandra.ro"
EVENTS_URL = f"{BASE_URL}/program/"


def extract_json_data(html: str) -> list[dict]:
    """Extract event data from embedded JavaScript - events array in inline script."""
    current_year = datetime.now().year
    for year in [current_year, current_year + 1]:
        start_marker = f'"start":"{year}-'
        idx = html.find(start_marker)
        if idx != -1:
            break
    else:
        return []
    
    obj_start = html.rfind('{"title":"', 0, idx)
    if obj_start == -1:
        return []
    
    arr_start = html.rfind('[{', 0, obj_start + 5)
    if arr_start == -1:
        return []
    
    depth = 1
    i = arr_start + 1
    while i < len(html) and depth > 0:
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
        i += 1
    
    if depth != 0:
        return []
    
    try:
        json_str = html[arr_start:i]
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []


def parse_json_event(data: dict) -> Event | None:
    """Parse event from JSON data."""
    try:
        title = data.get("title", "")
        if not title:
            return None
        
        start_str = data.get("start", "")
        if not start_str:
            return None
        
        try:
            event_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S+00:00")
        except ValueError:
            try:
                event_date = datetime.fromisoformat(start_str.replace("+00:00", ""))
            except ValueError:
                return None
        
        terms = data.get("terms", {})
        room_info = terms.get("wcs_room", [])
        if room_info and isinstance(room_info, list) and len(room_info) > 0:
            sala_name = room_info[0].get("name", "Unknown")
        else:
            sala_name = "Unknown"
        
        venue = f"Teatrul Bulandra - {sala_name}"
        
        permalink = data.get("permalink", "")
        buttons = data.get("buttons", {})
        main_btn = buttons.get("main", {})
        custom_url = main_btn.get("custom_url")
        if custom_url:
            url = custom_url
        elif permalink:
            url = permalink
        else:
            url = f"{BASE_URL}/{title.lower().replace(' ', '-')}/"
        
        excerpt = data.get("excerpt", "")
        author = None
        if excerpt:
            author_match = re.search(r'de\s+([^•<]+)', excerpt)
            if author_match:
                author = author_match.group(1).strip()
        
        duration = data.get("duration")
        
        return Event(
            title=title,
            artist=author,
            venue=venue,
            date=event_date,
            url=url,
            source="bulandra",
            category="theatre",
            price=None,
        )
    except (KeyError, ValueError, TypeError):
        return None


def scrape() -> list[Event]:
    """Fetch upcoming events from Teatrul Bulandra."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch Bulandra events: {e}")
        return events
    
    json_events = extract_json_data(html)
    
    for data in json_events:
        event = parse_json_event(data)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
