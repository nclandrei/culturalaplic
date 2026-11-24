from datetime import datetime

from scrapers.theatre.odeon import SHOP_URL, parse_shows


def _show(name: str, rooms: list[dict], details_url: str = "https://teatrul-odeon.ro/spectacol/test/") -> dict:
    return {
        "name": name,
        "author": "De Bernard Shaw",
        "director": "Regia Andrei Șerban",
        "detailsUrl": details_url,
        "rooms": rooms,
    }


def _room(hall: str, *dates: str) -> dict:
    return {"name": hall, "representations": [{"date": date} for date in dates]}


def test_parses_every_representation_with_its_hall_credits_and_details_url():
    shows = [
        _show("Soldatul de ciocolată", [
            _room("Sala Majestic", "2026-12-20T19:00:00", "2026-11-27T19:00:00"),
            _room("Sala Studio", "2026-12-01T19:30:00"),
        ]),
        {**_show("Tur ghidat", [_room("Sala Studio", "2026-11-28T15:00:00")], ""),
         "author": "Teatrul Odeon", "director": ""},
    ]
    events = parse_shows(shows, datetime(2026, 11, 24, 21, 0))
    assert [(e.title, e.date, e.venue) for e in events] == [
        ("Soldatul de ciocolată", datetime(2026, 11, 27, 19, 0), "Teatrul Odeon - Sala Majestic"),
        ("Tur ghidat", datetime(2026, 11, 28, 15, 0), "Teatrul Odeon - Sala Studio"),
        ("Soldatul de ciocolată", datetime(2026, 12, 1, 19, 30), "Teatrul Odeon - Sala Studio"),
        ("Soldatul de ciocolată", datetime(2026, 12, 20, 19, 0), "Teatrul Odeon - Sala Majestic"),
    ]
    assert events[0].artist == "De Bernard Shaw, Regia Andrei Șerban"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"
    assert events[1].artist is None
    assert events[1].url == SHOP_URL


def test_keeps_later_today_and_skips_past_duplicate_and_malformed_representations():
    shows = [_show("Macbeth", [_room(
        "Sala Majestic",
        "2026-11-23T19:00:00",
        "2026-11-24T19:00:00",
        "2026-11-24T19:00:00",
        "not-a-date",
    )])]
    events = parse_shows(shows, datetime(2026, 11, 24, 21, 0))
    assert [(e.title, e.date) for e in events] == [("Macbeth", datetime(2026, 11, 24, 19, 0))]
