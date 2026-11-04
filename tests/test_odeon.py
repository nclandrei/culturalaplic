import json
from datetime import datetime

import pytest

from scrapers.theatre import odeon


def _row(title: str, start: str, **overrides) -> dict:
    date, time = start.split("T")
    return {
        "title": title, "date": date, "startTime": time, "status": "active",
        "category": "Sala Studio", "venue": "Sala Majestic",
        "subtitle": "de Autor, regia Regizor", "detailsUrl": "/spectacol/test/",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        **overrides,
    }


def _program(rows: list[dict]) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(rows)}; render(); }})();"


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    program = _program([
        _row("Pescărușul", "2026-12-31T18:00", category="Sala Majestic"),
        _row("Pescărușul", "2026-10-02T19:30"),
    ])
    events = odeon.parse_events(program, datetime(2026, 9, 27))
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
    program = _program([
        _row("Old", "2025-12-31T19:00"),
        _row("Cancelled", "2026-10-04T19:00", status="cancelled"),
        _row("Suspended", "2026-10-04T19:00", status="suspended"),
        _row("Hidden", "2026-10-04T19:00", hiddenFromPublic=True),
        _row("Broken", "not-a-dateT19:00"), future, future,
    ])
    events = odeon.parse_events(program, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]


def test_scrape_discovers_official_embed_and_supplies_required_referer(monkeypatch):
    def fetch(url, **kwargs):
        if url == odeon.EVENTS_URL:
            return '<script src="https://example.org/embed/program.js?tenant=odeon"></script>'
        if kwargs.get("headers", {}).get("Referer") != odeon.EVENTS_URL:
            raise ValueError("Embed host rejects requests without the official referer")
        return _program([_row("Pescărușul", "2099-11-05T19:30")])

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2099, 11, 5, 19, 30))
    ]


def test_missing_programme_is_not_an_empty_season():
    with pytest.raises(ValueError, match="missing performance data"):
        odeon.parse_events("Blocked")
    assert odeon.parse_events(_program([])) == []
