from unittest.mock import patch
from datetime import datetime

from scrapers.music import control


def test_scrape_uses_server_rendered_events_without_browser_wait():
    html = "<div class='events-list-view'></div>"

    with patch("scrapers.music.control.fetch_page", return_value=html) as fetch:
        control.scrape()

    fetch.assert_called_once_with(control.EVENTS_URL)


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

    def fetch(url: str) -> str:
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
