import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://oveit.com"
EVENTS_URL = f"{BASE_URL}/hub/org/l7PDAr7y"


def parse_date(date_text: str) -> datetime | None:
    """Parse date from text like 'Jan 21, 2026, 19:00 - 21:00'."""
    match = re.search(
        r"(\w+)\s+(\d{1,2}),\s*(\d{4}),\s*(\d{1,2}):(\d{2})",
        date_text,
    )
    if not match:
        return None

    month_abbr = match.group(1)
    day = int(match.group(2))
    year = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))

    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    month = months.get(month_abbr)
    if not month:
        return None

    return datetime(year, month, day, hour, minute)


def parse_price(text: str) -> str | None:
    """Extract price from text like 'From 60 lei'."""
    match = re.search(r"(?:From\s+)?(\d+)\s*lei", text, re.IGNORECASE)
    if match:
        amount = match.group(1)
        if "From" in text or "from" in text:
            return f"de la {amount} lei"
        return f"{amount} lei"
    return None


def parse_venue(text: str) -> str:
    """Parse venue from text like 'Ateneul Roman / sala mare'."""
    if "sala mare" in text.lower():
        return "Ateneul Român - Sala Mare"
    elif "sala mica" in text.lower():
        return "Ateneul Român - Sala Mică"
    return "Ateneul Român"


def scrape() -> list[Event]:
    """Fetch upcoming events from Ateneul Român via Oveit."""
    events: list[Event] = []
    seen_urls: set[str] = set()

    try:
        html = fetch_page(
            EVENTS_URL,
            needs_js=True,
            scroll_count=50,
            scroll_item_selector='a[href*="/hub/event/"]',
        )
    except Exception as e:
        print(f"Failed to fetch Ateneul Român events: {e}")
        return events

    soup = BeautifulSoup(html, "html.parser")

    for link in soup.find_all("a", href=lambda h: h and "/hub/event/" in h):
        href = link.get("href", "")
        url = BASE_URL + href if href.startswith("/") else href

        if url in seen_urls:
            continue

        title = link.get_text(strip=True)
        if not title or title == "Buy now":
            continue

        parent = link.find_parent("div")
        if not parent:
            continue

        grandparent = parent.find_parent("div")
        text = grandparent.get_text(separator=" | ", strip=True) if grandparent else ""

        event_date = parse_date(text)
        if not event_date:
            continue

        venue = parse_venue(text)
        price = parse_price(text)

        seen_urls.add(url)
        events.append(
            Event(
                title=title,
                artist=None,
                venue=venue,
                date=event_date,
                url=url,
                source="Ateneul Român",
                category="music",
                price=price,
            )
        )

    events.sort(key=lambda e: e.date)
    return events
