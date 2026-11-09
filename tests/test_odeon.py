import json
from datetime import datetime

import pytest

from scrapers.theatre.odeon import parse_events


def _performance(**changes) -> dict:
    return {
        "title": "Pescărușul",
        "date": "2026-11-13",
        "startTime": "19:30",
        "status": "active",
        "venue": "Sala Studio",
        "category": "Sala Majestic",
        "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/pescarusul/",
        "ticketUrl": "https://bilete.teatrul-odeon.ro/pescarusul",
        "originalDate": "2026-09-23",
        **changes,
    }


def _script(performances: list[dict]) -> str:
    return "(function() { let PERFORMANCES = " + json.dumps(performances) + "; render(); })();"


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    script = _script([
        _performance(date="2027-01-02", venue="Sala Majestic"),
        _performance(),
    ])
    events = parse_events(script, datetime(2026, 11, 9))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 11, 13, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 2, 19, 30)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/pescarusul/"
    assert events[0].source == "odeon"
    assert events[0].category == "theatre"


def test_skips_past_unavailable_duplicate_and_malformed_entries_without_rollover():
    future = _performance()
    script = _script([
        _performance(title="Old", date="2025-12-31"),
        _performance(title="Yesterday", date="2026-11-08"),
        *[_performance(title=status, status=status) for status in ("cancelled", "suspended", "postponed")],
        _performance(title="Hidden", hiddenFromPublic=True),
        _performance(title="Unlisted", isListed=False),
        _performance(title="Broken", date="not-a-date"),
        _performance(title="No time", startTime=""),
        _performance(title=""),
        future, future,
        _performance(title="Today", date="2026-11-09", startTime="18:00"),
    ])
    events = parse_events(script, datetime(2026, 11, 9, 12))
    assert [(event.title, event.date) for event in events] == [
        ("Today", datetime(2026, 11, 9, 18)),
        ("Pescărușul", datetime(2026, 11, 13, 19, 30)),
    ]


def test_uses_ticket_link_when_detail_link_is_missing():
    events = parse_events(_script([_performance(detailsUrl="")]), datetime(2026, 11, 9))
    assert events[0].url == "https://bilete.teatrul-odeon.ro/pescarusul"


def test_missing_widget_data_is_not_reported_as_an_empty_programme():
    with pytest.raises(ValueError, match="missing performance data"):
        parse_events("<html></html>")
    assert parse_events(_script([])) == []
