from datetime import datetime
from unittest.mock import patch

from scrapers.music.jazzinthepark import (
    COMPETITION_URL,
    FESTIVAL_URL,
    LINEUP_URL,
    parse_schedule,
    scrape,
)


def test_parse_schedule_keeps_published_artist_time():
    date, stage = parse_schedule("18.09.2026 / 19:30 - 20:30 / Hill Stage")

    assert date == datetime(2026, 9, 18, 19, 30)
    assert stage == "Hill Stage"


def test_scrape_keeps_each_competition_day_as_a_time_unknown_festival_event():
    lineup_html = "<html><body><h1>Jazz in the Park 2027</h1></body></html>"
    competition_html = """
        <html><body>
          <h5 class="elementor-heading-title">
            18-20 SEPTEMBER 2026 | CENTRAL PARK, CLUJ-NAPOCA, ROMÂNIA
          </h5>
          <h1>Jazz in the Park Competition</h1>
          <p>Three days of live music featuring 12 competing bands.</p>
        </body></html>
    """

    def fetch(url: str, needs_js: bool = False) -> str:
        assert needs_js is (url != FESTIVAL_URL)
        return {
            LINEUP_URL: lineup_html,
            COMPETITION_URL: competition_html,
            FESTIVAL_URL: "<html><body>No announced festival dates</body></html>",
        }[url]

    with patch("scrapers.music.jazzinthepark.fetch_page", side_effect=fetch):
        events = scrape()

    assert len(events) == 3
    assert [event.date for event in events] == [
        datetime(2026, 9, 18),
        datetime(2026, 9, 19),
        datetime(2026, 9, 20),
    ]
    assert all(event.title == "Jazz in the Park Competition 2026" for event in events)
    assert all(event.artist is None for event in events)
    assert all(event.venue == "Parcul Central, Cluj-Napoca" for event in events)
    assert all(event.url == COMPETITION_URL for event in events)


def test_announced_2027_festival_days_are_listed_without_invented_artist_times():
    def fetch(url: str, needs_js: bool = False) -> str:
        return {
            LINEUP_URL: "<p>No artists announced yet</p>",
            COMPETITION_URL: "<p>No competition dates announced</p>",
            FESTIVAL_URL: "<p>See you next year: June 25-27, 2027</p><p>KAMASI WASHINGTON first headliner</p>",
        }[url]

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 27)

    with patch("scrapers.music.jazzinthepark.fetch_page", side_effect=fetch), \
         patch("scrapers.music.jazzinthepark.datetime", FixedDatetime):
        events = scrape()

    assert [(e.title, e.date, e.venue) for e in events] == [
        ("Jazz in the Park 2027", datetime(2027, 6, day), "Parcul Etnografic, Cluj-Napoca")
        for day in (25, 26, 27)
    ]
    assert all(e.artist is None and e.url == FESTIVAL_URL for e in events)
