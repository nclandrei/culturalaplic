import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre.odeon import parse_events, scrape


def _performance(**overrides) -> dict:
    return {
        "title": "Pescărușul", "date": "2026-11-15", "startTime": "19:30",
        "originalDate": "2026-09-26", "status": "active", "isListed": True,
        "venue": "Sala Studio", "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", "ticketUrl": "https://bilete.teatrul-odeon.ro/test",
        **overrides,
    }


def _script(*performances: dict) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(performances)}; }})();"


def test_scrape_reads_the_live_programme_embed_not_the_obsolete_calendar():
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=test"></script>'
    script = _script(_performance(date="2099-11-15"))
    with patch("scrapers.theatre.odeon.fetch_page", side_effect=[html, script]):
        events = scrape()
    assert len(events) == 1
    assert events[0].title == "Pescărușul"
    assert events[0].date == datetime(2099, 11, 15, 19, 30)
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_filters_unavailable_entries_and_keeps_same_day_and_next_year_occurrences():
    today = _performance()
    script = _script(
        _performance(date="2027-01-02", venue="Sala Majestic"),
        _performance(date="2026-11-14"),
        _performance(status="cancelled"), _performance(status="suspended"),
        _performance(isListed=False), _performance(date="bad"), today, today,
    )
    events = parse_events(script, datetime(2026, 11, 15, 20))
    assert [(event.title, event.date, event.venue) for event in events] == [
        ("Pescărușul", datetime(2026, 11, 15, 19, 30), "Teatrul Odeon - Sala Studio"),
        ("Pescărușul", datetime(2027, 1, 2, 19, 30), "Teatrul Odeon - Sala Majestic"),
    ]


def test_missing_programme_data_is_not_an_empty_season():
    with pytest.raises(ValueError, match="programme data not found"):
        parse_events("<title>Access denied</title>")
    assert parse_events(_script()) == []
