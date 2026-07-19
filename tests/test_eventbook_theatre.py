from datetime import datetime
from importlib import import_module
from unittest.mock import patch

from models import Event


def make_event(title: str, category: str) -> Event:
    return Event(
        title=title,
        artist=None,
        venue="Test venue",
        date=datetime(2026, 7, 15, 19, 0),
        url=f"https://eventbook.ro/{category}/{title}",
        source="eventbook",
        category=category,
        price=None,
    )


def test_theatre_adapter_filters_mixed_eventbook_results():
    eventbook = import_module("scrapers.theatre.eventbook")
    upstream = [make_event("Concert", "music"), make_event("Play", "theatre")]

    with patch.object(eventbook, "scrape_eventbook", return_value=upstream):
        events = eventbook.scrape()

    assert [event.title for event in events] == ["Play"]
