import json
import re
from datetime import datetime

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.bulandra.ro"
EVENTS_URL = f"{BASE_URL}/program/"


def extract_feed_data(html: str) -> list[dict]:
    """Extract event data from embedded 'feed' JSON array in inline script."""
    marker = '"feed":['
    idx = html.find(marker)
    if idx == -1:
        return []
    
    start = idx + len(marker) - 1  # Position of [
    depth = 1
    i = start + 1
    while i < len(html) and depth > 0:
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
        i += 1
    
    if depth != 0:
        return []
    
    try:
        json_str = html[start:i]
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
            event_date = datetime.fromisoformat(start_str.replace("+00:00", "+02:00"))
            event_date = event_date.replace(tzinfo=None)
        except ValueError:
            return None
        
        terms = data.get("terms", {})
        room_info = terms.get("wcs_room", [])
        if room_info and isinstance(room_info, list) and len(room_info) > 0:
            sala_name = room_info[0].get("name", "Unknown")
            # Clean up room name - remove address in parentheses
            sala_name = re.sub(r'\s*\([^)]+\)', '', sala_name).strip()
        else:
            sala_name = "Unknown"
        
        venue = f"Teatrul Bulandra - {sala_name}"
        
        buttons = data.get("buttons", {})
        if isinstance(buttons, dict):
            main_btn = buttons.get("main", {})
            custom_url = main_btn.get("custom_url") if isinstance(main_btn, dict) else None
        else:
            custom_url = None
        permalink = data.get("permalink", "")
        
        if custom_url:
            url = custom_url
        elif permalink:
            url = permalink
        else:
            url = EVENTS_URL
        
        excerpt = data.get("excerpt", "")
        author = None
        if excerpt:
            # Match "de Author Name" pattern
            author_match = re.search(r'de\s+([^•<\n]+)', excerpt)
            if author_match:
                author = author_match.group(1).strip()
                # Clean HTML entities and extra whitespace
                author = re.sub(r'\s+', ' ', author).strip()
        
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
        html = fetch_page(EVENTS_URL, needs_js=True, timeout=60000)
    except Exception as e:
        print(f"Failed to fetch Bulandra events: {e}")
        return events
    
    feed_events = extract_feed_data(html)
    
    for data in feed_events:
        event = parse_json_event(data)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
