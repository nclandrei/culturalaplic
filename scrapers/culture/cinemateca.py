from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from scrapers.culture.elvirepopescu import parse_event
from services.http import fetch_page

BASE_URL = "https://eventbook.ro"
HALLS = {
    "cinema-eforie": "Cinemateca Eforie",
    "cinema-union": "Cinema Union",
}
EVENTS_URL = f"{BASE_URL}/hall/cinema-eforie"
MAX_PAGES = 50


def scrape() -> list[Event]:
    """Fetch dated screenings from both Cinemateca halls on Eventbook."""
    events: list[Event] = []
    seen: set[tuple[str, datetime, str]] = set()
    today = datetime.now().date()

    for hall, venue in HALLS.items():
        for page in range(1, MAX_PAGES + 1):
            path = f"/hall/{hall}"
            url = f"{BASE_URL}{path}" + (f"?page={page}" if page > 1 else "")
            soup = BeautifulSoup(fetch_page(url), "html.parser")

            for card in soup.select("div.row.shadow.border"):
                event = parse_event(card, venue=venue, source="cinemateca")
                if not event or event.date.date() < today:
                    continue
                key = (event.url, event.date, event.venue)
                if key not in seen:
                    seen.add(key)
                    events.append(event)

            if not soup.select_one(f'a[href="{path}?page={page + 1}"]'):
                break

    return sorted(events, key=lambda event: event.date)
