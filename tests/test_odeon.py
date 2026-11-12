import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon


def _performance(title: str, date: str, **kwargs) -> dict:
    return {
        "title": title, "date": date, "startTime": "19:30", "status": "active",
        "venue": "Sala Studio", "subtitle": "de Autor, regia Regizor",
        "detailsUrl": "/spectacol/test/", "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        **kwargs,
    }


def _script(*rows: dict) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(rows)}; render(); }})();"


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    script = _script(
        _performance("Pescărușul", "2026-10-02"),
        _performance("Pescărușul", "2027-01-03", venue="Sala Majestic", startTime="18:00"),
    )
    with patch.object(odeon, "fetch_page", side_effect=[
        '<script src="https://widget.example/api/embed/program.js?tenant=odeon"></script>', script,
    ]), patch.object(odeon, "datetime") as clock:
        clock.now.return_value = datetime(2026, 9, 27)
        clock.fromisoformat.side_effect = datetime.fromisoformat
        events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 3, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_hidden_duplicate_and_malformed_entries_without_rollover():
    future = _performance("Macbeth", "2026-10-03", originalDate="2026-09-01")
    script = _script(
        _performance("Old", "2025-12-31"),
        _performance("Cancelled", "2026-10-04", status="cancelled"),
        _performance("Suspended", "2026-10-05", status="suspended"),
        _performance("Hidden", "2026-10-06", hiddenFromPublic=True),
        _performance("Broken", "not-a-date"), future, future,
    )
    events = odeon.parse_events(script, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 30))
    ]


def test_missing_widget_data_is_not_a_valid_empty_programme():
    with pytest.raises(ValueError, match="missing performance data"):
        odeon.parse_events('{"success":false,"error":"Access denied"}')
    assert odeon.parse_events(_script(), datetime(2026, 9, 27)) == []
