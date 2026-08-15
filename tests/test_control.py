from unittest.mock import patch

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
