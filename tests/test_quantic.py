from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.music.quantic import parse_event, parse_multiday_event


def test_parse_event_combines_calendar_date_with_visible_start_time():
    soup = BeautifulSoup(
        """
        <article class="tribe-events-calendar-month__calendar-event">
          <a class="tribe-events-calendar-month__calendar-event-title-link"
             href="https://quantic.pub/eveniment/eivor/">EIVOR</a>
          <div class="tribe-events-calendar-month__calendar-event-datetime">
            <time datetime="19:00">7:00 pm</time>
            <time datetime="23:30">11:30 pm</time>
          </div>
          <button data-tooltip-content="#tooltip-1"></button>
        </article>
        <div id="tooltip-1">
          <time datetime="2026-08-04">August 4 @ 7:00 pm</time>
        </div>
        """,
        "html.parser",
    )

    event = parse_event(soup.select_one("article"), soup)

    assert event is not None
    assert event.date == datetime(2026, 8, 4, 19, 0)


def test_parse_multiday_event_uses_the_explicit_first_day_start_time():
    soup = BeautifulSoup(
        """
        <article class="tribe-events-calendar-month__multiday-event
                        tribe-events-calendar-month__multiday-event--start">
          <a data-js="tribe-events-tooltip"
             data-tooltip-content="#tooltip-2"
             href="https://quantic.pub/eveniment/iubim-2roti/">
            <div class="tribe-events-calendar-month__multiday-event-bar-title">
              iubim 2ROTI
            </div>
          </a>
        </article>
        <div id="tooltip-2">
          <time datetime="2026-09-04">
            <span class="tribe-event-date-start">September 4 @ 5:00 pm</span>
            - September 6 @ 11:30 pm
          </time>
        </div>
        """,
        "html.parser",
    )

    event = parse_multiday_event(soup.select_one("article"), soup)

    assert event is not None
    assert event.date == datetime(2026, 9, 4, 17, 0)
