from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import HttpError
from scrapers.music import quantic
from scrapers.music.quantic import (
    enrich_event_from_ticket,
    parse_event,
    parse_multiday_event,
    parse_ticket_datetime,
    ticket_title_matches,
)


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


def test_ticketbox_start_show_overrides_open_doors():
    html = """
    <time datetime="2026-09-09T20:00:00.000Z">9 Septembrie, 20:00</time>
    <p>OPEN DOORS: 19:00 START SHOW: 20:00</p>
    """

    assert parse_ticket_datetime(html, "https://ticketbox.ro/ro/event/307") == (
        datetime(2026, 9, 9, 20, 0)
    )


def test_iabilet_whitelabel_can_override_a_rescheduled_date():
    html = """
    <script type="application/ld+json">
    {
      "@type": "Event",
      "name": "Xzibit",
      "startDate": "2026-11-12"
    }
    </script>
    <div class="date-location">
      <p>joi, 12 noiembrie, ora 20:00 acces de la 19:00</p>
    </div>
    """

    assert parse_ticket_datetime(
        html,
        "https://bilete.quantic.pub/bilete-xzibit-126726/",
    ) == datetime(2026, 11, 12, 20, 0)

    assert ticket_title_matches(
        "XZIBIT Live in Bucharest",
        "Xzibit - Kingmaker Tour 2026 - București",
    )


def test_enrich_event_follows_the_linked_ticket_page(monkeypatch):
    event = Event(
        title="Trio Mandili live in Bucharest",
        artist="Trio Mandili live in Bucharest",
        venue="Quantic",
        date=datetime(2026, 9, 12, 20, 0),
        url="https://quantic.pub/eveniment/trio-mandili/",
        source="quantic",
        category="music",
    )
    detail_html = """
    <a href="https://bilete.quantic.pub/bilete-trio-mandili-126954/">
      Bilete
    </a>
    """
    ticket_html = """
    <script type="application/ld+json">
      {"@type":"Event", "name":"Trio Mandili live in Bucharest",
       "startDate":"2026-09-12"}
    </script>
    <div class="date-location">
      <p>12 septembrie, ora 21:00 acces de la 20:00</p>
    </div>
    """
    monkeypatch.setattr(
        quantic,
        "fetch_page_with_reader_fallback",
        lambda *args, **kwargs: detail_html,
    )
    monkeypatch.setattr(quantic, "fetch_page", lambda *args, **kwargs: ticket_html)

    enrich_event_from_ticket(event)

    assert event.date == datetime(2026, 9, 12, 21, 0)


def test_ticket_json_ld_timezone_is_converted_to_bucharest():
    html = """
    <script type="application/ld+json">
      {
        "@type":"Event",
        "name":"Green Carnation",
        "startDate":"2026-09-25T18:00:00+00:00"
      }
    </script>
    """

    assert parse_ticket_datetime(
        html,
        "https://www.ambilet.ro/bilete/green-carnation/",
    ) == datetime(2026, 9, 25, 21, 0)


def test_unrelated_ticket_page_cannot_override_calendar_datetime(monkeypatch):
    event = Event(
        title="NERVY live la Quantic",
        artist="NERVY live la Quantic",
        venue="Quantic",
        date=datetime(2026, 9, 9, 19, 0),
        url="https://quantic.pub/eveniment/nervy/",
        source="quantic",
        category="music",
    )
    detail_html = '<a href="https://ticketbox.ro/ro/event/other">Bilete</a>'
    unrelated_ticket_html = """
    <script type="application/ld+json">
      {"@type":"Event", "name":"Completely Different Band",
       "startDate":"2026-11-20"}
    </script>
    <p>START SHOW: 22:00</p>
    """
    monkeypatch.setattr(
        quantic,
        "fetch_page_with_reader_fallback",
        lambda *args, **kwargs: detail_html,
    )
    monkeypatch.setattr(
        quantic,
        "fetch_page",
        lambda *args, **kwargs: unrelated_ticket_html,
    )

    enrich_event_from_ticket(event)

    assert event.date == datetime(2026, 9, 9, 19, 0)


def test_verified_ambilet_block_uses_exact_source_checked_datetime(monkeypatch):
    event = Event(
        title="Oddland, Mother Of Millions, Ring Of Gyges",
        artist="Oddland, Mother Of Millions, Ring Of Gyges",
        venue="Quantic",
        date=datetime(2026, 9, 26, 19, 0),
        url="https://quantic.pub/eveniment/oddland-mother-of-millions/",
        source="quantic",
        category="music",
    )
    ticket_url = (
        "https://www.ambilet.ro/bilete/"
        "oddland-mother-of-millions-ring-of-gyges-26-09-2026/"
    )
    monkeypatch.setattr(
        quantic,
        "fetch_page_with_reader_fallback",
        lambda *args, **kwargs: f'<a href="{ticket_url}">Bilete</a>',
    )

    calls = []

    def blocked_fetch(url: str, **kwargs):
        calls.append((url, kwargs))
        raise HttpError("HTTP 403", status_code=403)

    monkeypatch.setattr(quantic, "fetch_page", blocked_fetch)

    enrich_event_from_ticket(event)

    assert event.date == datetime(2026, 9, 26, 20, 0)
    assert calls == [(ticket_url, {"record_failure": False})]
