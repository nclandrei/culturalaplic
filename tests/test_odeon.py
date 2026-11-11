import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon


def _performance(title: str, start: str, **overrides) -> dict:
    date, _, time = start.partition("T")
    return {
        "title": title, "date": date, "startTime": time, "status": "active",
        "venue": "Sala Studio", "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", "ticketUrl": "https://bilete.teatrul-odeon.ro/test",
        **overrides,
    }


def _script(*performances: dict) -> str:
    return f"let PERFORMANCES = {json.dumps(performances)}; render();"


def test_scrape_follows_embedded_programme_and_preserves_performance_details():
    script = _script(
        _performance("Pescărușul", "2027-12-31T18:00", venue="Sala Majestic"),
        _performance("Pescărușul", "2027-01-02T19:30", details="Text with ]; inside"),
    )
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon"></script>'
    with patch.object(odeon, "fetch_page", side_effect=[html, script]):
        events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2027, 1, 2, 19, 30)),
        ("Pescărușul", datetime(2027, 12, 31, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_unavailable_past_duplicate_and_malformed_entries_without_rollover():
    future = _performance("Macbeth", "2026-10-03T19:00", originalDate="2026-09-03")
    script = _script(
        _performance("Old", "2025-12-31T19:00"),
        _performance("Cancelled", "2026-10-04T19:00", status="cancelled"),
        _performance("Suspended", "2026-10-04T19:00", status="suspended"),
        _performance("Hidden", "2026-10-04T19:00", hiddenFromPublic=True),
        _performance("Unlisted", "2026-10-04T19:00", isListed=False),
        _performance("Broken", "not-a-date"),
        _performance("Yesterday", "2026-09-26T19:00"),
        _performance("Today", "2026-09-27T19:30", detailsUrl="", venue=""),
        future, future,
    )
    events = odeon.parse_events(script, datetime(2026, 9, 27, 23))
    assert [(event.title, event.date) for event in events] == [
        ("Today", datetime(2026, 9, 27, 19, 30)),
        ("Macbeth", datetime(2026, 10, 3, 19, 0)),
    ]
    assert events[0].url == "https://bilete.teatrul-odeon.ro/test"
    assert events[0].venue == "Teatrul Odeon"


def test_empty_programme_is_distinct_from_missing_widget_data():
    assert odeon.parse_events(_script()) == []
    with pytest.raises(ValueError, match="no performance data"):
        odeon.parse_events("<title>Access denied</title>")
    with patch.object(odeon, "fetch_page", return_value="<html></html>"):
        with pytest.raises(ValueError, match="no programme widget"):
            odeon.scrape()
