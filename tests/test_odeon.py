import json
from datetime import datetime

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_events


def _row(title: str, start: str, status: str = "active", hall: str = "Sala Studio") -> dict:
    date, time = start.split("T")
    return {
        "title": title, "date": date, "startTime": time, "status": status,
        "venue": hall, "subtitle": "de Autor, regia Regizor",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II",
        "detailsUrl": "/spectacol/test/", "ticketUrl": "https://bilete.teatrul-odeon.ro/test",
    }


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    data = {"performances": [
        _row("Pescărușul", "2026-10-02T19:30"),
        _row("Pescărușul", "2027-01-03T18:00", hall="Sala Majestic"),
    ]}
    events = parse_events(data, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 3, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries_without_rollover():
    future = _row("Macbeth", "2026-10-03T19:00")
    data = {"performances": [
        _row("Old", "2025-12-31T19:00"),
        _row("Cancelled", "2026-10-04T19:00", "cancelled"),
        _row("Suspended", "2026-10-04T19:00", "suspended"),
        _row("Broken", "not-a-dateT19:00"), future, future,
    ]}
    events = parse_events(data, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]


def test_scrape_discovers_current_embed_feed():
    import httpx
    import respx

    data_url = "https://projects.doimih.net/hub/api/embed/program-data?tenant=odeon&api_key=public-example"
    with respx.mock() as router:
        router.get(odeon.EVENTS_URL).mock(return_value=httpx.Response(200, text='''
            <script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon&amp;api_key=public-example"></script>
        '''))
        router.get(data_url, headers={"Referer": odeon.EVENTS_URL}).mock(
            return_value=httpx.Response(200, text=json.dumps({"performances": [
                _row("Cabaret", "2099-12-09T19:30"),
            ]})),
        )
        events = odeon.scrape()

    assert [(event.title, event.date) for event in events] == [
        ("Cabaret", datetime(2099, 12, 9, 19, 30)),
    ]
