from unittest.mock import call, patch
from datetime import datetime

import pytest

from scrapers.music import control
from services import http


def test_scrape_uses_server_rendered_events_without_browser_wait():
    html = "<div class='events-list-view'></div>"

    with patch("scrapers.music.control.fetch_page", return_value=html) as fetch:
        control.scrape()

    fetch.assert_called_once_with(control.EVENTS_URL, record_failure=False)


def test_connection_failure_recovers_without_recording_a_scraper_failure():
    html = "<div class='events-list-view'></div>"
    http.reset_fetch_failures()
    with patch.object(http, "_fetch_http", side_effect=ConnectionRefusedError()), patch.object(
        http, "_fetch_js", return_value=html
    ) as browser:
        assert control.fetch_control_page(control.EVENTS_URL) == html
    assert browser.call_args.args[0] == control.EVENTS_URL
    assert http.get_fetch_failures() == []


def test_failed_browser_fallback_still_records_failure():
    http.reset_fetch_failures()
    try:
        with patch.object(http, "_fetch_http", side_effect=ConnectionRefusedError()), patch.object(
            http, "_fetch_js", side_effect=RuntimeError("browser unavailable")
        ):
            with pytest.raises(http.HttpError, match="browser unavailable"):
                control.fetch_control_page(control.EVENTS_URL)
        assert len(http.get_fetch_failures()) == 1
    finally:
        http.reset_fetch_failures()


def test_detail_pages_also_use_browser_fallback():
    url = f"{control.BASE_URL}/events/king-automatic"
    with patch.object(control, "fetch_page", side_effect=[
        http.HttpError("connection refused"), "<p>Show Time: 21:00</p>"
    ]) as fetch:
        assert control.parse_show_time(control.fetch_control_page(url)) == (21, 0)
    assert fetch.call_args_list == [
        call(url, record_failure=False), call(url, needs_js=True)
    ]


def test_scrape_parses_server_rendered_event_fixture():
    html = """
    <div class="events-list-view">
      <div class="date">
        <div class="title"><p>Saturday, August 15, 2026</p></div>
        <div class="room">
          <p class="title">Berlin Room</p>
          <div class="event">
            <a class="title hover" href="/event/?slug=gaap">GAAP</a>
            <span class="hour">22:00</span>
            <span class="tag black">FREE ENTRY</span>
          </div>
        </div>
      </div>
    </div>
    """

    with patch("scrapers.music.control.fetch_page", return_value=html):
        events = control.scrape()

    assert len(events) == 1
    assert events[0].title == "GAAP"
    assert events[0].date.isoformat() == "2026-08-15T22:00:00"
    assert events[0].venue == "Control Club - Berlin Room"
    assert events[0].price == "Gratis"


def test_scrape_prefers_explicit_show_time_over_open_doors(monkeypatch):
    listing_html = """
    <div class="events-list-view">
      <div class="date">
        <div class="title"><p>Sunday, September 6, 2026</p></div>
        <div class="room">
          <p class="title">Berlin Room</p>
          <div class="event" type="live" genre="garage_rock">
            <a class="title hover"
               href="/event/?slug=king-automatic">ctrl LIVE: King Automatic</a>
            <span class="hour">20:00</span>
          </div>
        </div>
      </div>
    </div>
    """
    detail_html = """
    <p>Open Doors: 20:00<br>Show Time: 21:00</p>
    """

    def fetch(url: str, **kwargs) -> str:
        return listing_html if url == control.EVENTS_URL else detail_html

    monkeypatch.setattr(control, "fetch_page", fetch)

    events = control.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 6, 21, 0)


def test_scrape_skips_non_music_spoken_word_nights():
    html = """
    <div class="events-list-view">
      <div class="date">
        <div class="title"><p>Wednesday, August 19, 2026</p></div>
        <div class="room">
          <p class="title">Berlin Room</p>
          <div class="event" type="nights" genre="spoken_word">
            <a class="title hover" href="/event/?slug=cinema-esperanto">
              Cinema Esperanto #4: La Haine (FR)
            </a>
            <span class="hour">20:00</span>
          </div>
        </div>
      </div>
    </div>
    """

    with patch("scrapers.music.control.fetch_page", return_value=html):
        events = control.scrape()

    assert events == []


def test_loading_placeholder_is_not_published_as_a_price():
    html = """
    <div class="events-list-view">
      <div class="date">
        <div class="title"><p>Sunday, September 6, 2026</p></div>
        <div class="room">
          <p class="title">Berlin Room</p>
          <div class="event" type="live" genre="garage_rock">
            <a class="title hover" href="/event/?slug=king">King</a>
            <span class="hour">20:00</span>
            <span class="ticket-price price"><span class="loading">...</span></span>
          </div>
        </div>
      </div>
    </div>
    """

    with patch("scrapers.music.control.fetch_page", return_value=html):
        events = control.scrape()

    assert len(events) == 1
    assert events[0].price is None
