import json
from datetime import datetime

import pytest

from scrapers.theatre import odeon
from scrapers.theatre.odeon import parse_embed_events, parse_events


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


def _performance(**changes) -> dict:
    return {
        "title": "Svejk", "date": "2026-11-14", "startTime": "19:00",
        "originalDate": "2026-09-27", "status": "active",
        "hiddenFromPublic": False, "venue": "Sala Majestic",
        "subtitle": "după Jaroslav Hašek, regia Alexandru Dabija",
        "ticketPrices": "80 lei Cat. I; 60 lei Cat. II; 40 lei Cat. III",
        "detailsUrl": "/spectacol/svejk/", "ticketUrl": "/tickets/svejk",
        **changes,
    }


def _embed(*rows: dict) -> str:
    return f"(function() {{ let PERFORMANCES = {json.dumps(rows)}; const OTHER = []; }})();"


def test_embed_uses_actual_rescheduled_date_and_keeps_distinct_performances():
    script = _embed(
        _performance(date="2027-01-02", startTime="19:30", category="Sala Studio"),
        _performance(), _performance(),
    )
    events = parse_embed_events(script, datetime(2026, 11, 14))
    assert [e.date for e in events] == [datetime(2026, 11, 14, 19), datetime(2027, 1, 2, 19, 30)]
    assert events[0].title == "Svejk"
    assert events[0].venue == "Teatrul Odeon - Sala Majestic"
    assert events[1].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].artist == "după Jaroslav Hašek, regia Alexandru Dabija"
    assert events[0].price == "80 lei Cat. I; 60 lei Cat. II; 40 lei Cat. III"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/svejk/"


def test_embed_skips_past_hidden_cancelled_and_invalid_dates():
    script = _embed(
        _performance(date="2025-12-31"), _performance(hiddenFromPublic=True),
        _performance(status="cancelled"), _performance(status="postponed"),
        _performance(date="bad"), _performance(startTime="25:30"),
        _performance(startTime=""), _performance(title=""),
    )
    assert parse_embed_events(script, datetime(2026, 11, 14)) == []
    with pytest.raises(ValueError, match="missing PERFORMANCES"):
        parse_embed_events("A broken widget")


def test_scrape_discovers_current_embed_url_from_official_page(monkeypatch):
    url = "https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon&api_key=public"
    requests = []

    def fetch(url_requested: str, **kwargs) -> str:
        requests.append(url_requested)
        if url_requested == odeon.EVENTS_URL:
            return f'<script async src="{url.replace("&", "&amp;")}"></script>'
        assert url_requested == url
        assert kwargs["headers"] == {"Referer": odeon.EVENTS_URL}
        return _embed(_performance(date="2099-01-02"))

    monkeypatch.setattr(odeon, "fetch_page", fetch)
    events = odeon.scrape()
    assert len(events) == 1
    assert events[0].date == datetime(2099, 1, 2, 19)
    assert requests == [odeon.EVENTS_URL, url]
