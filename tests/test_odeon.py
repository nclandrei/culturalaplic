import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon


def _performance(**overrides):
    return {
        "title": "Pescărușul", "date": "2026-12-31", "startTime": "18:00",
        "venue": "Sala Studio", "status": "active", "isListed": True,
        "subtitle": "de Autor, regia Regizor", "ageRating": "14+",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", **overrides,
    }


def _script(*performances):
    return "let PERFORMANCES = " + json.dumps(performances) + ";\nrender();"


def test_scrapes_official_widget_with_explicit_dates_halls_prices_and_links():
    script = _script(
        _performance(date="2027-01-02", startTime="19:30", category="Sala Majestic"),
        _performance(),
    )
    html = '<script src="https://widget.example/api/embed/program.js?tenant=odeon&amp;api_key=public"></script>'
    with patch.object(odeon, "fetch_page", side_effect=[html, script]):
        events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 18)),
        ("Pescărușul", datetime(2027, 1, 2, 19, 30)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_hidden_duplicate_and_malformed_performances():
    script = _script(
        _performance(date="2025-12-31"),
        _performance(status="cancelled"),
        _performance(status="suspended"),
        _performance(isListed=False),
        _performance(date="not-a-date"),
        _performance(), _performance(),
        _performance(title="Tonight", date="2026-11-20", startTime="19:30",
                     detailsUrl="#", ticketUrl="https://bilete.teatrul-odeon.ro/tonight",
                     venue=""),
    )
    events = odeon.parse_events(script, datetime(2026, 11, 20, 12))
    assert [(event.title, event.date) for event in events] == [
        ("Tonight", datetime(2026, 11, 20, 19, 30)),
        ("Pescărușul", datetime(2026, 12, 31, 18)),
    ]
    assert events[0].venue == "Teatrul Odeon"
    assert events[0].url == "https://bilete.teatrul-odeon.ro/tonight"


def test_empty_programme_is_distinct_from_missing_widget_data():
    assert odeon.parse_events(_script()) == []
    with pytest.raises(ValueError, match="missing performance data"):
        odeon.parse_events('{"success": false, "error": "blocked"}')
