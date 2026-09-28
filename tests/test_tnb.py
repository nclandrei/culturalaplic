from datetime import datetime
from unittest.mock import Mock

import httpx
import pytest
from bs4 import BeautifulSoup

from scrapers.theatre import tnb
from services import http
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


@pytest.mark.parametrize("first_result", [422, "<title>Just a moment...</title>"])
def test_reader_recovers_without_recording_a_scraper_failure(monkeypatch, first_result):
    urls = []

    def fake_get(url, **kwargs):
        urls.append(url)
        status = first_result if len(urls) == 1 and isinstance(first_result, int) else 200
        content = first_result if len(urls) == 1 and isinstance(first_result, str) else LIST_VIEW_HTML
        return httpx.Response(status, text=content, request=httpx.Request("GET", url))

    monkeypatch.setattr(http.httpx, "get", fake_get)
    http.reset_fetch_failures()
    try:
        events = tnb.scrape_month(2026, 9)
        assert len(events) == 2
        assert events[0].date == datetime(2026, 9, 5, 11)
        assert events[0].url.startswith("https://www.tnb.ro/")
        assert urls == [
            "https://r.jina.ai/https://www.tnb.ro/ro/calendar?year=2026&month=9&view=list",
            "https://r.jina.ai/http://www.tnb.ro/ro/calendar?year=2026&month=9&view=list",
        ]
        assert http.get_fetch_failures() == []
    finally:
        http.reset_fetch_failures()


def test_exhausted_recovery_still_records_failure(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(422, request=httpx.Request("GET", url))

    monkeypatch.setattr(http.httpx, "get", fake_get)
    http.reset_fetch_failures()
    try:
        assert tnb.scrape_month(2026, 9) == []
        assert len(http.get_fetch_failures()) == 1
        assert "HTTP 422" in http.get_fetch_failures()[0]
    finally:
        http.reset_fetch_failures()
