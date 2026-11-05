import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon


def _performance(**overrides) -> dict:
    return {
        "title": "Pescărușul", "date": "2026-11-05", "startTime": "19:30",
        "status": "active", "isListed": True, "venue": "Sala Studio",
        "subtitle": "de A. P. Cehov, regia Andrei și Andreea Grosu",
        "detailsUrl": "/spectacol/pescarusul/", "ticketUrl": "https://bilete.teatrul-odeon.ro/pescarusul",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II; 30 lei Cat. III",
        **overrides,
    }


def _program(performances: list[dict]) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(performances)}; render(); }})();"


def test_scrape_reads_official_embed_and_preserves_performance_details():
    program = _program([
        _performance(date="2026-12-31", venue="Sala Majestic", startTime="18:00"),
        _performance(),
    ])
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=tenant-teatrul-odeon"></script>'
    with patch.object(odeon, "fetch_page", side_effect=[html, program]):
        with patch.object(odeon, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 5, 23)
            events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 11, 5, 19, 30)),
        ("Pescărușul", datetime(2026, 12, 31, 18)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II; 30 lei Cat. III"
    assert events[0].artist == "de A. P. Cehov, regia Andrei și Andreea Grosu"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/pescarusul/"


def test_skips_past_cancelled_unlisted_duplicate_and_malformed_performances():
    future = _performance(date="2027-01-03")
    program = _program([
        _performance(date="2025-12-31"),
        _performance(status="cancelled"),
        _performance(isListed=False),
        _performance(date="not-a-date"),
        future, future,
    ])
    events = odeon.parse_events(program, datetime(2026, 11, 5))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2027, 1, 3, 19, 30)),
    ]


def test_missing_programme_is_not_an_empty_season():
    with pytest.raises(ValueError, match="missing performance data"):
        odeon.parse_events("Access denied")
    assert odeon.parse_events(_program([])) == []
