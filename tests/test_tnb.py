from datetime import datetime
from unittest.mock import Mock

from bs4 import BeautifulSoup
import respx

from scrapers.theatre import tnb
from services.http import HttpError, get_fetch_failures, reset_fetch_failures


LIST_VIEW_HTML = """
<div class="day" id="day-05">
  <div class="left_date">
    <div class="number">05</div>
    <div class="month">Sep</div>
    <div class="year">2026</div>
  </div>
  <div class="right_items">
    <div class="item spectacol spectacol-tnb">
      <div class="right_item">
        <a class="ev_title" href="https://www.tnb.ro/ro/amintiri-din-copilarie">
          Amintiri din copilărie
        </a>
        <span class="time">11:00</span>
        <span class="location">Sala Atelier</span>
      </div>
    </div>
    <div class="item turneu">
      <div class="right_item">
        <a class="ev_title" href="/ro/moroi-si-papadii-la-chisinau">
          Moroi și păpădii la Chișinău
        </a>
        <span class="time">00:00</span>
        <span class="location">-</span>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_day_keeps_events_on_the_list_view_date():
    day = BeautifulSoup(LIST_VIEW_HTML, "html.parser").select_one("div.day")

    events = tnb.parse_day(day)

    assert [event.date for event in events] == [
        datetime(2026, 9, 5, 11, 0),
        datetime(2026, 9, 5, 0, 0),
    ]
    assert events[0].venue == "TNB - Sala Atelier"
    assert events[1].venue == "TNB"
    assert events[1].url == "https://www.tnb.ro/ro/moroi-si-papadii-la-chisinau"


def test_scrape_month_prefers_reader_list_view(monkeypatch):
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append((url, kwargs))
        return LIST_VIEW_HTML

    monkeypatch.setattr(tnb, "fetch_page", fake_fetch_page)
    fallback = Mock(side_effect=AssertionError("should not fetch blocked primary"))
    monkeypatch.setattr(tnb, "fetch_page_with_reader_fallback", fallback)

    events = tnb.scrape_month(2026, 9)

    assert len(events) == 2
    assert requests == [
        (
            "https://r.jina.ai/https://www.tnb.ro/ro/calendar?year=2026&month=9&view=list",
            {"headers": {"X-Return-Format": "html"}, "timeout": 60000, "record_failure": False},
        )
    ]
    fallback.assert_not_called()


def test_scrape_month_retries_official_page_if_reader_fails(monkeypatch):
    monkeypatch.setattr(tnb, "fetch_page", Mock(side_effect=HttpError("HTTP 422")))
    fallback = Mock(return_value=LIST_VIEW_HTML)
    monkeypatch.setattr(tnb, "fetch_page_with_reader_fallback", fallback)

    assert len(tnb.scrape_month(2026, 10)) == 2
    fallback.assert_called_once_with(
        "https://www.tnb.ro/ro/calendar?year=2026&month=10&view=list",
        expected_text="right_items", timeout=60000,
    )


@respx.mock
def test_scrape_month_recovers_reader_timeout_via_official_host_alias():
    respx.get(
        "https://r.jina.ai/https://www.tnb.ro/ro/calendar?year=2026&month=9&view=list"
    ).respond(422, text="Request failed: Timeout was reached")
    respx.get(
        "https://r.jina.ai/https://tnb.ro/ro/calendar?year=2026&month=9&view=list"
    ).respond(200, text=LIST_VIEW_HTML)

    reset_fetch_failures()
    events = tnb.scrape_month(2026, 9)

    assert [(event.title, event.date) for event in events] == [
        ("Amintiri din copilărie", datetime(2026, 9, 5, 11)),
        ("Moroi și păpădii la Chișinău", datetime(2026, 9, 5)),
    ]
    assert get_fetch_failures() == []
