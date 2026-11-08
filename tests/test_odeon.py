import json
from datetime import datetime

import pytest

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_events, parse_program


def _row(title: str, start: str, status: str = "EventScheduled", hall: str = "Sala Studio") -> str:
    return f'''<div class="eventon_list_event scheduled">
      <div class="evo_event_schema"><a itemprop="url" href="/events/wrong-calendar-url"></a>
      <meta itemprop="startDate" content="{start}+0:00"><meta itemprop="eventStatus" content="https://schema.org/{status}"></div>
      <span class="evcal_event_title">{title}</span>
      <span class="evcal_event_subtitle">de Autor, regia Regizor | În cadrul unui festival</span>
      <em class="event_location_name">{hall}, Preț bilete: 60 lei Cat. I; 40 lei Cat. II.</em>
      <a class="evo_cusmeta_btn" href="/spectacol/test/">Detalii</a>
    </div>'''


def test_parses_explicit_dates_halls_prices_and_same_title_occurrences():
    html = _row("Pescărușul | 14 +", "2026-10-2T19:30") + _row(
        "Pescărușul | 14 +", "2026-12-31T18:00", hall="Sala Majestic"
    )
    events = parse_events(html, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Pescărușul", datetime(2026, 10, 2, 19, 30)),
        ("Pescărușul", datetime(2026, 12, 31, 18, 0)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].artist == "de Autor, regia Regizor"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/test/"


def test_skips_past_cancelled_duplicate_and_malformed_entries_without_rollover():
    future = _row("Macbeth | 14 +", "2026-10-3T19:00")
    html = (
        _row("Old", "2025-12-31T19:00")
        + _row("Cancelled", "2026-10-4T19:00", "EventCancelled")
        + _row("Broken", "not-a-date") + future + future
    )
    events = parse_events(html, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("Macbeth", datetime(2026, 10, 3, 19, 0))
    ]


def _performance(**overrides):
    return {
        "id": "perf-test", "date": "2026-12-31", "startTime": "19:30",
        "endTime": "21:00", "title": "Pescărușul", "ageRating": "14+",
        "subtitle": "de Anton Cehov, regia Eugen Jebeleanu",
        "venue": "Sala Studio", "category": "Festival", "status": "active",
        "detailsUrl": "/spectacol/pescarusul/", "ticketUrl": "https://tickets.example/test",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II", "isListed": True,
        **overrides,
    }


def test_program_uses_explicit_year_time_and_performance_fields():
    events = parse_program({"success": True, "performances": [
        _performance(date="2027-01-02", venue="Sala Majestic"),
        _performance(venue="Sala Majestic", category="Sala Studio"),
    ]}, datetime(2026, 12, 30))
    assert [(e.title, e.date) for e in events] == [
        ("Pescărușul", datetime(2026, 12, 31, 19, 30)),
        ("Pescărușul", datetime(2027, 1, 2, 19, 30)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[1].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].artist == "de Anton Cehov, regia Eugen Jebeleanu"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/pescarusul/"
    assert events[0].source == "odeon"
    assert events[0].category == "theatre"


def test_program_skips_past_unlisted_cancelled_duplicates_and_invalid_dates():
    rows = [
        _performance(date="2025-12-31"), _performance(status="cancelled"),
        _performance(isListed=False), _performance(date="2026-02-30"),
        _performance(date="31 dec"), _performance(startTime="bad"),
        _performance(title=""), {}, None, _performance(), _performance(),
    ]
    events = parse_program({"performances": rows}, datetime(2026, 12, 31, 22))
    assert len(events) == 1  # Keep today's performances, as with the EventON parser.
    assert events[0].date == datetime(2026, 12, 31, 19, 30)


def test_program_optional_fields_and_suspended_ticket_sales():
    events = parse_program({"performances": [_performance(
        venue="", subtitle="", ticketPrices="", detailsUrl="#", status="suspended",
    )]}, datetime(2026, 12, 30))
    assert events[0].venue == "Teatrul Odeon"
    assert events[0].artist is None
    assert events[0].price is None
    assert events[0].url == odeon.EVENTS_URL


@pytest.mark.parametrize("data", [{"success": False, "performances": []}, {}, {"performances": None}])
def test_program_rejects_invalid_response(data):
    with pytest.raises(ValueError, match="Invalid Odeon programme"):
        parse_program(data)


def test_scrape_discovers_public_api_query_and_sends_required_site_headers(monkeypatch):
    html = '''<script async src="https://projects.doimih.net/hub/api/embed/program.js?tenant=tenant-teatrul-odeon&amp;showFilter=false&amp;api_key=public-test-key"></script>'''
    calls = []

    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return html if url == odeon.EVENTS_URL else json.dumps({"performances": [
            _performance(date="2099-01-02"),
        ]})

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    events = odeon.scrape()
    assert len(events) == 1
    assert events[0].date == datetime(2099, 1, 2, 19, 30)
    assert calls == [
        (odeon.EVENTS_URL, {}),
        ("https://projects.doimih.net/hub/api/embed/program-data?tenant=tenant-teatrul-odeon&showFilter=false&api_key=public-test-key",
         {"headers": {"Referer": odeon.EVENTS_URL, "Origin": odeon.BASE_URL}}),
    ]


def test_scrape_retains_eventon_fallback(monkeypatch):
    monkeypatch.setattr(odeon, "fetch_page", lambda url: _row("Legacy", "2099-01-02T19:00"))
    assert odeon.scrape()[0].title == "Legacy"
