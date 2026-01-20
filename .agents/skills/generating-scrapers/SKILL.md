---
name: generating-scrapers
description: Generates event scrapers for GigRadar. Use when adding a new venue, ticketing site, or event source. Handles HTML/JSON parsing, JS-rendered pages, date formats, and verification.
---

# Generating Scrapers

Creates scrapers for GigRadar event aggregation following established patterns.

## Required Inputs

Before starting, collect from user:
1. **URL** - The events/program page URL
2. **Category** - `music`, `theatre`, or `culture`
3. **Screenshot** - Visual reference of the page showing events
4. **Pagination** - How to access more events (if applicable)

## Workflow

### Phase 1: Reconnaissance (Chrome DevTools MCP)

**Always use Chrome DevTools MCP for page inspection** - it's more reliable than Playwright for understanding page structure.

1. Open the page in Chrome DevTools MCP:
   ```
   mcp__chrome_devtools__new_page with url: "URL"
   ```

2. Take a snapshot to see the page structure:
   ```
   mcp__chrome_devtools__take_snapshot
   ```
   This shows the accessibility tree with UIDs for each element.

3. Examine the structure:
   - Look for event containers (divs, cards, list items)
   - Identify data elements: title, date, time, venue/hall, price, URL
   - Use `mcp__chrome_devtools__take_screenshot` for visual reference
   - Check for infinite scroll or "load more" buttons

4. For infinite scroll pages, scroll to load more content:
   ```
   mcp__chrome_devtools__evaluate_script with function: "window.scrollTo(0, document.body.scrollHeight)"
   ```
   Then take another snapshot to see new elements.

5. Check for embedded JSON data:
   ```
   mcp__chrome_devtools__evaluate_script with function: "() => {
     const scripts = document.querySelectorAll('script');
     for (const s of scripts) {
       if (s.textContent.includes('feed') || s.type === 'application/ld+json') {
         return s.textContent.substring(0, 500);
       }
     }
     return null;
   }"
   ```

6. If page has no current events, check Wayback Machine:
   ```
   https://web.archive.org/web/*/URL
   ```
   Find a snapshot with events to understand the structure.

### Phase 2: Create Scraper

Create file at `scrapers/{category}/{source_name}.py`:

```python
import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://example.com"
EVENTS_URL = f"{BASE_URL}/events/"

ROMANIAN_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "noi": 11, "dec": 12,
}


def parse_date(date_text: str) -> datetime | None:
    """Parse date from site-specific format."""
    # Implement based on observed format
    pass


def parse_event(element: BeautifulSoup) -> Event | None:
    """Parse a single event from HTML element."""
    # Extract: title, date, venue, url, price
    pass


def scrape() -> list[Event]:
    """Fetch upcoming events from {Source Name}."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()  # (title, date) for dedup
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True)  # Set based on page type
    except Exception as e:
        print(f"Failed to fetch events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for element in soup.select("CSS_SELECTOR"):
        event = parse_event(element)
        if event:
            key = (event.title, event.date.isoformat())
            if key not in seen:
                seen.add(key)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    return events
```

### Phase 3: Verify

Test the scraper directly (from project root):

```bash
python3 -c "from scrapers.{category}.{name} import scrape; import json; events = scrape(); print(f'{len(events)} events'); print(json.dumps([{'title': e.title, 'date': e.date.isoformat(), 'venue': e.venue} for e in events[:5]], indent=2))"
```

Then compare against the live page using Chrome DevTools MCP:
1. Use `mcp__chrome_devtools__take_snapshot` to see current page state
2. Use `mcp__chrome_devtools__take_screenshot` for visual comparison
3. Verify event count matches visible events on page

### Phase 4: Compare & Fix

Using the screenshot and JSON output:
1. Verify event count matches visible events
2. Check titles are correctly extracted
3. Verify dates parse correctly (especially year rollover)
4. Confirm venue names include hall info where applicable
5. Check URLs are absolute and valid

Common fixes:
- Wrong CSS selector → inspect HTML more carefully
- Missing events → check if content is JS-rendered
- Wrong dates → adjust date parsing regex
- Relative URLs → prepend BASE_URL

### Phase 5: Register & Commit

1. Add scraper to `main.py` SCRAPERS dict (if not already there)

2. Add source to `web/src/app/despre/page.tsx` sources list (appropriate category)

3. Commit:
```bash
git add scrapers/{category}/{name}.py
git commit -m "Add {Source Name} scraper"
git push
```

## Scraper Patterns

### HTML with BeautifulSoup (most common)
See: `teatrulmic.py`, `metropolis.py`, `control.py`

### Embedded JSON in page source
See: `bulandra.py` - extracts `"feed":[...]` from inline script

### JSON-LD structured data
See: `iabilet.py` - parses `<script type="application/ld+json">`

### Vue/React rendered pages
Use `needs_js=True` and wait for content. See: `cuibul.py`

## Date Parsing Patterns

### Romanian abbreviated months (DD mon)
```python
ROMANIAN_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "noi": 11, "dec": 12,
}
match = re.search(r"(\d{1,2})\s+(\w+)", date_text.lower())
```

### DD.MM format
```python
match = re.match(r"(\d{1,2})\.(\d{2})", date_text)
```

### Full Romanian month names
```python
ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}
```

### Year rollover handling
```python
year = datetime.now().year
event_date = datetime(year, month, day)
if event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
    event_date = datetime(year + 1, month, day)
```

## Common Gotchas

1. **JS-rendered content**: Empty HTML containers → use `needs_js=True`
2. **Multiple halls/rooms**: Include in venue field (e.g., "Teatrul X - Sala Mare")
3. **Relative URLs**: Always check and prepend BASE_URL if needed
4. **No current events**: Use Wayback Machine to find historical structure
5. **Pagination**: Some sites load more via AJAX - may need multiple fetches
6. **Price formats**: Vary widely - extract as string, don't parse numbers
7. **Deduplication**: Use `(title, date.isoformat())` tuple as seen key
8. **Infinite scroll**: Use `scroll_count` and `scroll_item_selector` params in `fetch_page()`
9. **Alternative data sources**: If official site is hard to scrape, check ticketing platforms (Oveit, iaBilet, Eventim)

## Event Model Reference

```python
@dataclass
class Event:
    title: str           # Event/show name
    artist: str | None   # Performer (music) or author (theatre)
    venue: str           # Venue name, include hall if applicable
    date: datetime       # Event datetime
    url: str             # Absolute URL to event page
    source: str          # Scraper identifier (e.g., "metropolis")
    category: Literal["music", "theatre", "culture"]
    price: str | None    # Price as string (e.g., "50 RON", "Free")
```
