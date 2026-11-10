import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_events


def _performance(**overrides) -> dict:
    return {
        "title": "Pescărușul",
        "date": "2026-12-31",
        "startTime": "19:30",
        "status": "active",
        "category": "Sala Studio",
        "venue": "Sala Majestic",
        "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/",
        "ticketUrl": "https://bilete.teatrul-odeon.ro/test",
        **overrides,
    }


def _program(*performances: dict) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(performances)}; render(); }})();"


def test_scrapes_embed_with_explicit_years_halls_prices_and_repeated_shows():
    program = _program(
        _performance(date="2027-01-02", startTime="18:00", category="Sala Majestic"),
        _performance(originalDate="2026-09-23"),
    )
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon"></script>'
    with patch.object(odeon, "fetch_page", side_effect=[html, program]):
        with patch.object(odeon, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 12, 31)
            events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 2, 18)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_suspended_hidden_duplicate_and_malformed_entries():
    future = _performance()
    program = _program(
        _performance(date="2025-12-31"),
        _performance(status="cancelled"),
        _performance(status="suspended"),
        _performance(hiddenFromPublic=True),
        _performance(isListed=False),
        _performance(date="not-a-date"),
        future, future,
    )
    events = parse_events(program, datetime(2026, 12, 31, 12))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 19, 30))
    ]


def test_ticket_link_fallback_and_missing_programme_is_not_an_empty_season():
    events = parse_events(_program(_performance(detailsUrl="#")), datetime(2026, 12, 1))
    assert events[0].url == "https://bilete.teatrul-odeon.ro/test"
    with pytest.raises(ValueError, match="missing PERFORMANCES"):
        parse_events("<html>Service unavailable</html>")
