from datetime import datetime

from scrapers.theatre.odeon import parse_performances


def _perf(title: str, date: str, start: str = "19:30", status: str = "active", venue: str = "Sala Studio") -> dict:
    return {
        "date": date,
        "startTime": start,
        "title": title,
        "venue": venue,
        "status": status,
        "subtitle": "de Autor, regia Regizor",
        "detailsUrl": "https://teatrul-odeon.ro/spectacol/test/",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
    }


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    events = parse_performances(
        [
            _perf("Pescărușul", "2026-12-31", "18:00", venue="Sala Majestic"),
            _perf("Pescărușul", "2026-10-02"),
        ],
        datetime(2026, 9, 27),
    )
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30)),
        ("Pescărușul", datetime(2026, 12, 31, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries_without_rollover():
    future = _perf("Macbeth", "2026-10-03", "19:00")
    events = parse_performances(
        [
            _perf("Old", "2025-12-31"),
            _perf("Cancelled", "2026-10-04", status="cancelled"),
            _perf("Broken", "not-a-date"),
            future,
            future,
        ],
        datetime(2026, 9, 27),
    )
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]
