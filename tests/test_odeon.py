from datetime import datetime

from scrapers.theatre.odeon import parse_events


def _show(name: str, *dates: str, room: str = "Sala Studio", details: str | None = "https://teatrul-odeon.ro/spectacol/x/") -> dict:
    return {
        "name": name,
        "author": "De Autor",
        "slug": "slug",
        "detailsUrl": details,
        "rooms": [{"name": room, "representations": [{"date": d} for d in dates]}],
    }


def test_parses_every_representation_with_hall_and_skips_past_or_duplicate():
    shows = [
        _show("Macbeth", "2026-11-24T19:00:00", "2026-12-03T19:00:00", room="Sala Majestic"),
        _show("Pescărușul", "2026-11-26T19:30:00", "2026-11-26T19:30:00", "not-a-date", details=None),
    ]
    events = parse_events(shows, datetime(2026, 11, 25, 12, 0))
    assert [(e.title, e.date, e.venue) for e in events] == [
        ("Pescărușul", datetime(2026, 11, 26, 19, 30), "Teatrul Odeon - Sala Studio"),
        ("Macbeth", datetime(2026, 12, 3, 19, 0), "Teatrul Odeon - Sala Majestic"),
    ]
    assert events[0].url == "https://bilete.teatrul-odeon.ro/slug"
    assert events[1].url == "https://teatrul-odeon.ro/spectacol/x/"
    assert events[1].artist == "De Autor"
