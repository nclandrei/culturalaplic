from datetime import datetime
from unittest.mock import Mock

from bs4 import BeautifulSoup

from scrapers.theatre import tnb
from services.http import HttpError


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

    events = tnb.scrape_month(2026, 9)

    assert len(events) == 2
    assert requests == [
        (
            "https://r.jina.ai/https://www.tnb.ro/ro/calendar?year=2026&month=9&view=list",
            {"headers": {"X-Return-Format": "html"}, "timeout": 60000, "record_failure": False},
        )
    ]


def test_scrape_month_retries_official_page_if_reader_fails(monkeypatch):
    fetch = Mock(side_effect=[HttpError("HTTP 422"), LIST_VIEW_HTML])
    monkeypatch.setattr(tnb, "fetch_page", fetch)

    assert len(tnb.scrape_month(2026, 10)) == 2
    assert fetch.call_count == 2
    fetch.assert_called_with(
        "https://www.tnb.ro/ro/calendar?year=2026&month=10&view=list",
        timeout=60000,
    )


def test_scrape_month_does_not_repeat_failed_reader(monkeypatch):
    fetch = Mock(side_effect=HttpError("HTTP 422"))
    monkeypatch.setattr(tnb, "fetch_page", fetch)

    assert tnb.scrape_month(2026, 10) == []
    assert fetch.call_count == 2
    assert fetch.call_args_list[0].args[0].startswith("https://r.jina.ai/")
    assert fetch.call_args_list[1].args[0].startswith("https://www.tnb.ro/")
