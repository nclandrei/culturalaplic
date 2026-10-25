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


@pytest.mark.parametrize("primary", [None, "<html>WordPress critical error</html>"])
def test_scrape_recovers_programme_from_ticket_listing(primary):
    def performance(start, url="https://www.blt.ro/solness.html"):
        return {"@type": "Event", "name": "Constructorul Solness",
                "startDate": start, "url": url}

    performances = [
        performance("2099-11-29T19:00"),
        performance("2099-10-30T19:00"),
        performance("2099-10-30T19:00"),
        performance("2020-10-30T19:00"),
        performance("2099-10-31T19:00", "https://www.blt.ro/tour.html"),
    ]
    html = '''
      <ul class="eventTiles"><li>
        <a href="https://www.blt.ro/solness.html">
          <span class="tileLocation">Teatrul Bulandra (sala Toma Caragiu)</span>
        </a>
      </li><li>
        <a href="https://www.blt.ro/tour.html">
          <span class="tileLocation">Teatru Iași</span>
        </a>
      </li></ul>
      <script type="application/ld+json">'''+ json.dumps(performances) + '</script>'
    real_fetch = bulandra.fetch_page

    def fetch(url, **kwargs):
        if url == bulandra.EVENTS_URL:
            if primary is None:
                # Exercise the real failure recorder, not just a mocked exception.
                return real_fetch(url, **kwargs)
            return primary
        return html

    reset_fetch_failures()
    with patch.object(bulandra, "fetch_page", side_effect=fetch), patch(
        "services.http._fetch_js", side_effect=HttpError("HTTP 500", 500),
    ):
        events = bulandra.scrape()

    assert [(event.title, event.date, event.venue, event.url) for event in events] == [
        ("Constructorul Solness", datetime(2099, 10, 30, 19),
         "Teatrul Bulandra - Toma Caragiu", "https://www.blt.ro/solness.html"),
        ("Constructorul Solness", datetime(2099, 11, 29, 19),
         "Teatrul Bulandra - Toma Caragiu", "https://www.blt.ro/solness.html"),
    ]
    assert get_fetch_failures() == []


def test_scrape_rejects_failed_fallback_instead_of_empty_programme():
    with patch.object(bulandra, "fetch_page", return_value="<html>Error</html>"):
        with pytest.raises(ValueError, match="no verifiable events"):
            bulandra.scrape()
