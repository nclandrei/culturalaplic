import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon


def _performance(title: str, date: str, **overrides) -> dict:
    return {
        "title": title, "date": date, "startTime": "19:30", "status": "active",
        "category": "Sala Studio", "venue": "Sala Majestic",
        "subtitle": "de Autor, regia Regizor", "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", **overrides,
    }


def _program(*performances: dict) -> str:
    return "(() => { let PERFORMANCES = " + json.dumps(performances) + "; render(); })();"


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    program = _program(
        _performance("Pescărușul", "2027-01-02", startTime="18:00", category="Sala Majestic"),
        _performance("Pescărușul", "2026-12-31"),
    )
    events = odeon.parse_events(program, datetime(2026, 12, 30))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 2, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries_without_rollover():
    future = _performance("Macbeth", "2026-10-03", startTime="19:00")
    program = _program(
        _performance("Old", "2025-12-31"),
        _performance("Cancelled", "2026-10-04", status="cancelled"),
        _performance("Suspended", "2026-10-05", status="suspended"),
        _performance("Broken", "not-a-date"), future, future,
        _performance("Today", "2026-09-27", startTime="18:15"),
    )
    events = odeon.parse_events(program, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Today", datetime(2026, 9, 27, 18, 15)),
        ("Macbeth", datetime(2026, 10, 3, 19, 0)),
    ]


def test_scrape_discovers_the_current_calendar_embed():
    html = '<script src="https://calendar.example/embed/program.js?tenant=odeon"></script>'
    program = _program(_performance("Lysistrata", "2099-11-20"))
    with patch.object(odeon, "fetch_page", side_effect=[html, program]):
        events = odeon.scrape()
    assert len(events) == 1
    assert events[0].title == "Lysistrata"
    assert events[0].date == datetime(2099, 11, 20, 19, 30)


def test_missing_calendar_data_is_not_an_empty_programme():
    with pytest.raises(ValueError, match="missing performance data"):
        odeon.parse_events('{"success": false}')
