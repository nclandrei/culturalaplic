import json
from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import bulandra
from scrapers.theatre.bulandra import parse_json_event
from services.http import HttpError, get_fetch_failures, reset_fetch_failures


def event_data(room: str, **overrides):
    data = {
        "title": "FAMILY.EXE",
        "start": "2026-09-05T19:00:00+00:00",
        "terms": {"wcs_room": [{"name": room}]},
        "buttons": {
            "main": {
                "custom_url": False,
                "permalink": "https://www.bulandra.ro/family-exe/",
            }
        },
        "permalink": "https://www.bulandra.ro/program/instance/",
    }
    data.update(overrides)
    return data


def test_parse_json_event_keeps_only_bucharest_bulandra_halls():
    toma_caragiu = parse_json_event(
        event_data("Toma Caragiu (Jean-Louis Calderon 76A)")
    )
    liviu_ciulei = parse_json_event(
        event_data("Liviu Ciulei (Schitu Măgureanu nr. 1)")
    )
    iasi_tour = parse_json_event(event_data("Iași", title="ARTĂ"))

    assert toma_caragiu is not None
    assert toma_caragiu.date == datetime(2026, 9, 5, 19, 0)
    assert liviu_ciulei is not None
    assert iasi_tour is None


def test_parse_json_event_prefers_the_show_permalink():
    event = parse_json_event(event_data("Toma Caragiu"))

    assert event is not None
    assert event.url == "https://www.bulandra.ro/family-exe/"


def test_scrape_recovers_from_official_site_failure_without_duplicate_performances():
    def listing(*events):
        return '<script type="application/ld+json">' + json.dumps(events) + '</script>'

    def performance(title, start, location, url):
        return {"@type": "Event", "name": title, "startDate": start,
                "location": location, "url": url}

    bilet = listing(performance(
        "Măscăriciul", "2099-11-05T19:00:00",
        {"name": "Teatrul Bulandra - Sala Toma Caragiu"},
        "https://www.bilet.ro/eveniment/mascariciul",
    ))
    blt = listing(
        performance("Mascariciul - Teatrul Bulandra", "2099-11-05T19:00",
                    {"name": "Icoanei, Strada J.L..Calderon, 76 A, Bucuresti ",
                     "sameAs": "bulandra.ro"}, "https://www.blt.ro/mascariciul.html"),
        performance("Artă", "2099-11-05T19:00",
                    {"name": "Izvor, Bulevardul Schitu Magureanu 1, Bucuresti ",
                     "sameAs": "bulandra.ro"}, "https://www.blt.ro/arta.html"),
        performance("Artă", "2099-11-06T14:00",
                    {"name": "Teatrul Bulandra - Sala Liviu Ciulei"},
                    "https://www.blt.ro/arta.html"),
        performance("Expired", "2020-01-01T19:00",
                    {"name": "Teatrul Bulandra - Sala Toma Caragiu"}, "https://example.com"),
        performance("Tour", "2099-11-07T19:00",
                    {"name": "Iași"}, "https://example.com"),
    )
    reset_fetch_failures()
    with patch("services.http._fetch_http", side_effect=[HttpError("HTTP 500"), bilet, blt]):
        events = bulandra.scrape()

    assert [(e.title, e.date, e.venue) for e in events] == [
        ("Măscăriciul", datetime(2099, 11, 5, 19), "Teatrul Bulandra - Toma Caragiu"),
        ("Artă", datetime(2099, 11, 5, 19), "Teatrul Bulandra - Liviu Ciulei"),
        ("Artă", datetime(2099, 11, 6, 14), "Teatrul Bulandra - Liviu Ciulei"),
    ]
    assert events[0].url == "https://www.bilet.ro/eveniment/mascariciul"
    assert all(e.source == "bulandra" and e.category == "theatre" for e in events)
    assert get_fetch_failures() == []


def test_scrape_rejects_unusable_fallback_pages():
    with patch.object(bulandra, "fetch_page", return_value="<title>Error</title>"):
        with pytest.raises(ValueError, match="no programme data"):
            bulandra.scrape()
