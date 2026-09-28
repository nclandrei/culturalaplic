from models import Event
from scrapers.music.greenhours import PROMOTER_URL as EVENTS_URL
from scrapers.music.greenhours import scrape_all as scrape_greenhours

MIN_EXPECTED_EVENTS = 1


def scrape() -> list[Event]:
    """Fetch upcoming Green Hours theatre performances."""
    return [event for event in scrape_greenhours() if event.category == "theatre"]
