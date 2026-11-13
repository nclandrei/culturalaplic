import json
from datetime import datetime

import pytest

from scrapers.theatre import odeon


def _performance(title: str, date: str, **kwargs) -> dict:
    return {
        "title": title, "date": date, "startTime": "19:30", "status": "active",
        "venue": "Sala Studio", "subtitle": "de Autor, regia Regizor",
        "detailsUrl": "/spectacol/test/", "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        **kwargs,
    }


def test_scrape_discovers_new_calendar_and_keeps_dates_halls_and_prices(monkeypatch):
    performances = [
        _performance("Pescărușul", "2027-01-02"),
        _performance("Pescărușul", "2026-12-31", venue="Sala Majestic", startTime="18:00"),
    ]
    def fetch(url, **kwargs):
        if url == odeon.EVENTS_URL:
            return '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon"></script>'
        return "let PERFORMANCES = " + json.dumps(performances) + ";"

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 18)),
        ("Pescărușul", datetime(2027, 1, 2, 19, 30)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Majestic"
    assert events[1].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_hidden_duplicate_and_malformed_entries():
    future = _performance("Macbeth", "2026-12-03")
    performances = [
        _performance("Old", "2025-12-31"),
        _performance("Cancelled", "2026-12-04", status="cancelled"),
        _performance("Hidden", "2026-12-05", hiddenFromPublic=True),
        _performance("Unlisted", "2026-12-06", isListed=False),
        _performance("Broken", "not-a-date"), future, future,
    ]
    events = odeon.parse_events("let PERFORMANCES = " + json.dumps(performances), datetime(2026, 11, 13))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 12, 3, 19, 30)),
    ]
    with pytest.raises(ValueError, match="no performances"):
        odeon.parse_events("<html>unavailable</html>")
