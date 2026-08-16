from datetime import datetime
from unittest.mock import patch

from scrapers.music.rockstadt import SCHEDULE_URL, scrape


def test_scrape_emits_only_source_scheduled_occurrences_at_published_times():
    html = """
        <html><body>
          <a href="https://rockstadtextremefest.ro/team/unscheduled-band/">
            Unscheduled Band
          </a>
          <div id="2026-07-27" data-role="lineup">
            <div class="panel">
              <h4 class="panel-title">Scena Adrian Rugina</h4>
              <table><tbody>
                <tr data-item="793">
                  <td>Reverse The Moment</td><td>15:50 - 16:35</td>
                </tr>
                <tr data-item="794"><td></td><td>16:40 - 17:25</td></tr>
              </tbody></table>
            </div>
          </div>
        </body></html>
    """

    with patch("scrapers.music.rockstadt.fetch_page", return_value=html) as fetch:
        events = scrape()

    fetch.assert_called_once_with(SCHEDULE_URL, needs_js=False)
    assert len(events) == 1
    assert events[0].artist == "Reverse The Moment"
    assert events[0].date == datetime(2026, 7, 27, 15, 50)
    assert events[0].venue == (
        "Rockstadt Extreme Fest, Ghimbav – Scena Adrian Rugina"
    )
    assert events[0].url == SCHEDULE_URL


def test_scrape_places_after_midnight_set_on_the_next_calendar_day():
    html = """
        <div id="2026-07-27" data-role="lineup">
          <div class="panel">
            <h4 class="panel-title">Scena Andrei Calmuc</h4>
            <table><tbody><tr>
              <td>Fu Manchu</td><td>01:00 - 02:00</td>
            </tr></tbody></table>
          </div>
        </div>
    """

    with patch("scrapers.music.rockstadt.fetch_page", return_value=html):
        events = scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 7, 28, 1, 0)
