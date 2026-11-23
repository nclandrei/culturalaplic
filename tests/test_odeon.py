from datetime import datetime

from scrapers.theatre import odeon
from scrapers.theatre.odeon import get_data_url, parse_events


def _perf(title: str, date: str, time: str = "19:30", status: str = "active", venue: str = "Sala Studio") -> dict:
    return {
        "date": date,
        "startTime": time,
        "title": title,
        "venue": venue,
        "status": status,
        "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II.",
        "detailsUrl": "https://teatrul-odeon.ro/spectacol/test/",
        "ticketUrl": "https://bilete.teatrul-odeon.ro/test",
        "isListed": True,
    }


def test_data_url_comes_from_the_embedded_widget():
    page = (
        '<script src="https://projects.doimih.net/hub/api/embed/program.js?'
        'tenant=tenant-teatrul-odeon&amp;showFilter=false&amp;api_key=k" async=""></script>'
    )
    assert get_data_url(page) == (
        "https://projects.doimih.net/hub/api/embed/program-data?"
        "tenant=tenant-teatrul-odeon&showFilter=false&api_key=k"
    )


def test_parses_dates_halls_prices_and_same_title_occurrences():
    data = {"performances": [
        _perf("Pescărușul", "2026-10-02"),
        _perf("Pescărușul", "2026-12-31", "18:00", venue="Sala Majestic"),
        _perf("Tur ghidat", "2026-10-03", "15:00", venue=""),
    ]}
    events = parse_events(data, datetime(2026, 9, 27))
    assert [(event.title, event.date, event.venue) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30), "Teatrul Odeon - Sala Studio"),
        ("Tur ghidat", datetime(2026, 10, 3, 15, 0), "Teatrul Odeon"),
        ("Pescărușul", datetime(2026, 12, 31, 18, 0), "Teatrul Odeon - Sala Majestic"),
    ]
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries():
    future = _perf("Macbeth", "2026-10-03", "19:00")
    data = {"performances": [
        _perf("Old", "2025-12-31"),
        _perf("Cancelled", "2026-10-04", status="cancelled"),
        _perf("Suspended", "2026-10-05", status="suspended"),
        _perf("Broken", "not-a-date"),
        future,
        future,
    ]}
    events = parse_events(data, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]


def test_scrape_sends_official_referer_to_feed(monkeypatch):
    calls = []

    def fake_fetch_page(url, **kwargs):
        calls.append((url, kwargs))
        if url == odeon.EVENTS_URL:
            return '<script src="https://hub.example/api/embed/program.js?tenant=t&amp;api_key=k"></script>'
        return '{"success": true, "performances": [{"date": "2099-01-02", "startTime": "19:00", "title": "Macbeth", "venue": "Sala Majestic", "status": "active"}]}'

    monkeypatch.setattr(odeon, "fetch_page", fake_fetch_page)
    events = odeon.scrape()
    assert calls[1] == (
        "https://hub.example/api/embed/program-data?tenant=t&api_key=k",
        {"headers": {"Referer": odeon.EVENTS_URL}},
    )
    assert [event.title for event in events] == ["Macbeth"]
