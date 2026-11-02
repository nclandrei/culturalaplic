import json
from datetime import datetime
from unittest.mock import patch

import pytest

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


def test_scrape_reads_official_embed_with_explicit_dates_and_filters_invalid_shows():
    performance = {
        "title": "Pescărușul", "date": "2097-12-31", "startTime": "19:30",
        "venue": "Sala Studio", "status": "active", "isListed": True,
        "subtitle": "de A. P. Cehov, regia Andrei și Andreea Grosu",
        "detailsUrl": "/spectacol/pescarusul/", "ticketUrl": "https://bilete.teatrul-odeon.ro/pescarusul",
        "ticketPrices": "60 lei Cat. I; 40 lei Cat. II; 30 lei Cat. III",
    }
    rows = [
        {**performance, "date": "2098-01-02", "venue": "Sala Majestic"},
        {**performance, "date": "2025-12-31"},
        *({**performance, "status": status} for status in ["cancelled", "suspended", "postponed"]),
        {**performance, "isListed": False},
        {**performance, "date": "invalid"},
        performance, performance,
    ]
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=test"></script>'
    script = "(function() { let PERFORMANCES = " + json.dumps(rows) + "; let OTHER = []; })();"
    with patch.object(odeon, "fetch_page", side_effect=[html, script]):
        events = odeon.scrape()

    assert [(event.title, event.date, event.venue) for event in events] == [
        ("Pescărușul", datetime(2097, 12, 31, 19, 30), "Teatrul Odeon - Sala Studio"),
        ("Pescărușul", datetime(2098, 1, 2, 19, 30), "Teatrul Odeon - Sala Majestic"),
    ]
    assert events[0].artist == "de A. P. Cehov, regia Andrei și Andreea Grosu"
    assert events[0].price == "60 lei Cat. I; 40 lei Cat. II; 30 lei Cat. III"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/pescarusul/"
    assert events[0].source == "odeon"
    assert events[0].category == "theatre"


def test_widget_access_error_is_not_an_empty_programme():
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=test"></script>'
    with patch.object(odeon, "fetch_page", side_effect=[html, '{"success":false}']):
        with pytest.raises(ValueError, match="no programme data"):
            odeon.scrape()
