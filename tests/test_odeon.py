import json
from datetime import datetime
from unittest.mock import patch

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


def test_scrape_reads_official_widget_dates_halls_and_public_performances():
    performance = {
        "title": "Nu vorbim despre asta", "date": "2027-01-08", "startTime": "19:30",
        "status": "active", "category": "Sala Studio", "venue": "Sala Majestic",
        "subtitle": "de Alexandra Felseghi", "ticketPrices": "60 lei; 40 lei",
        "detailsUrl": "/spectacol/nu-vorbim-despre-asta/", "isListed": True,
    }
    performances = [
        performance, dict(performance, date="2027-01-12"), performance,
        dict(performance, date="2025-01-08"),
        dict(performance, date="2027-01-09", status="cancelled"),
        dict(performance, date="2027-01-10", status="suspended"),
        dict(performance, date="2027-01-11", hiddenFromPublic=True),
        dict(performance, date="2027-01-13", isListed=False),
        dict(performance, date="invalid"),
    ]
    html = '<script src="https://projects.doimih.net/hub/api/embed/program.js?tenant=odeon"></script>'
    programme = "let PERFORMANCES = " + json.dumps(performances) + "; render();"
    with patch.object(odeon, "fetch_page", side_effect=[html, programme]):
        events = odeon.scrape()
    assert [(event.title, event.date) for event in events] == [
        ("Nu vorbim despre asta", datetime(2027, 1, 8, 19, 30)),
        ("Nu vorbim despre asta", datetime(2027, 1, 12, 19, 30)),
    ]
    assert events[0].venue == "Teatrul Odeon - Sala Studio"
    assert events[0].artist == "de Alexandra Felseghi"
    assert events[0].price == "60 lei; 40 lei"
    assert events[0].url == "https://teatrul-odeon.ro/spectacol/nu-vorbim-despre-asta/"
