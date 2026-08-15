from datetime import datetime

from main import get_event_key
from models import Event


def test_artistless_event_keys_fall_back_to_title():
    first = Event(
        title="Boite, Box, Brancusi",
        artist=None,
        venue="MNAC",
        date=datetime(2026, 8, 15, 11, 0),
        url="https://mnac.ro/boite",
        source="mnac",
        category="culture",
    )
    second = {
        "title": "Seeing History",
        "artist": None,
        "venue": "MNAC",
        "date": "2026-08-15T11:00:00",
        "url": "https://mnac.ro/seeing-history",
        "source": "mnac",
        "category": "culture",
    }

    assert get_event_key(first) != get_event_key(second)


def test_artistless_duplicate_title_has_the_same_key_for_dict_and_event():
    event = Event(
        title="Boite, Box, Brancusi",
        artist=None,
        venue="MNAC",
        date=datetime(2026, 8, 15, 11, 0),
        url="https://mnac.ro/boite",
        source="mnac",
        category="culture",
    )
    serialized = {
        "title": event.title,
        "artist": None,
        "venue": event.venue,
        "date": event.date.isoformat(),
    }

    assert get_event_key(event) == get_event_key(serialized)

    serialized["date"] = "2026-08-15 11:00:00"
    assert get_event_key(event) == get_event_key(serialized)


def test_event_keys_keep_separate_same_day_showtimes():
    morning = Event(
        title="Amintiri din copilărie",
        artist=None,
        venue="TNB",
        date=datetime(2026, 9, 5, 11, 0),
        url="https://tnb.ro/morning",
        source="tnb",
        category="theatre",
    )
    evening = Event(
        title=morning.title,
        artist=None,
        venue=morning.venue,
        date=datetime(2026, 9, 5, 19, 0),
        url="https://tnb.ro/evening",
        source="tnb",
        category="theatre",
    )

    assert get_event_key(morning) != get_event_key(evening)
