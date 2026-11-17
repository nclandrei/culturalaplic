import json
from datetime import datetime

import pytest

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_events


def _row(title: str, start: str, status: str = "active", hall: str = "Sala Studio") -> dict:
    date, _, time = start.partition("T")
    return {
        "title": title, "date": date, "startTime": time, "status": status,
        "venue": hall, "subtitle": "de Autor, regia Regizor | În cadrul unui festival",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", "ticketUrl": "/tickets/test/",
    }


def _program(*rows: dict) -> str:
    return "let PERFORMANCES = " + json.dumps(rows) + "; render();"


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    program = _program(
        _row("Pescărușul", "2026-10-02T19:30"),
        _row("Pescărușul", "2026-12-31T18:00", hall="Sala Majestic"),
    )
    events = parse_events(program, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30)),
        ("Pescărușul", datetime(2026, 12, 31, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries_without_rollover():
    future = _row("Macbeth", "2026-10-03T19:00")
    program = _program(
        _row("Old", "2025-12-31T19:00"),
        _row("Cancelled", "2026-10-04T19:00", "cancelled"),
        _row("Broken", "not-a-date"),
        dict(_row("Unlisted", "2026-10-05T19:00"), isListed=False),
        future, future,
    )
    events = parse_events(program, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]


def test_scrape_follows_official_embed(monkeypatch):
    def fetch(url, **kwargs):
        if url == odeon.EVENTS_URL:
            return '<script src="https://calendar.example/api/embed/program.js?tenant=odeon"></script>'
        if url == "https://calendar.example/api/embed/program.js?tenant=odeon":
            assert kwargs["headers"]["Referer"] == odeon.EVENTS_URL
            return _program(_row("Polyxena", "2099-11-18T19:30"))
        raise AssertionError(url)

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    assert [(event.title, event.date) for event in odeon.scrape()] == [
        ("Polyxena", datetime(2099, 11, 18, 19, 30))
    ]


def test_missing_programme_data_is_not_a_successful_empty_calendar():
    with pytest.raises(ValueError, match="no performances data"):
        parse_events("Access denied")
