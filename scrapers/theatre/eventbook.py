from models import Event
from scrapers.music.eventbook import BUCHAREST_URL as EVENTS_URL
from scrapers.music.eventbook import scrape as scrape_eventbook

MIN_EXPECTED_EVENTS = 1


def scrape() -> list[Event]:
    """Fetch Bucharest theatre events from Eventbook."""
    return [event for event in scrape_eventbook() if event.category == "theatre"]
