import json
from datetime import datetime

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_events


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


def test_scrape_reads_new_widget_dates_and_skips_cancelled_performances(monkeypatch):
    performance = {
        "title": "Cabaret", "date": "2099-12-09", "startTime": "19:30",
        "originalDate": "2099-09-24", "status": "active", "venue": "Sala Majestic",
        "subtitle": "după John Van Druten", "ticketPrices": "120 lei Cat. I",
        "detailsUrl": "/spectacol/cabaret/",
    }
    records = [
        {**performance, "date": "2099-12-10"},
        {**performance, "status": "cancelled", "date": "2099-12-11"},
        {**performance, "status": "suspended", "date": "2099-12-12"},
        {**performance, "date": "2020-12-09"},
        {**performance, "date": "bad-date"},
        performance, performance,
    ]
    widget_url = "https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon"

    def fetch(url, **kwargs):
        if url == odeon.EVENTS_URL:
            return f'<script src="{widget_url}"></script>'
        assert url == widget_url
        return "let PERFORMANCES = " + json.dumps(records) + "; const NEXT = [];"

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    events = odeon.scrape()

    assert [event.date for event in events] == [
        datetime(2099, 12, 9, 19, 30), datetime(2099, 12, 10, 19, 30),
    ]
    assert events[0].title == "Cabaret"
    assert events[0].venue == "Teatrul Odeon - Sala Majestic"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/cabaret/"
    assert events[0].artist == "după John Van Druten"
    assert events[0].price == "120 lei Cat. I"
