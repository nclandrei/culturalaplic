from datetime import datetime
from unittest.mock import Mock

from bs4 import BeautifulSoup

from scrapers.theatre import tnb
from services.http import HttpError


LIST_VIEW_HTML = """
<table class="fc-header list_calendar"><tr><td>Septembrie 2026</td></tr></table>
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
        "http://www.tnb.ro/ro/calendar?year=2026&month=10&view=list",
        expected_text="list_calendar", timeout=60000,
    )


EMPTY_MONTH_HTML = """
<table class="fc-header list_calendar">
  <tr><td class="fc-header-center"><h2>Noiembrie 2027</h2></td></tr>
</table>
<div id="calendar"><div class="right_item"><h1>Nu există evenimente.</h1></div></div>
"""


def test_scrape_month_accepts_empty_calendar_from_reader(monkeypatch, capsys):
    monkeypatch.setattr(tnb, "fetch_page", Mock(return_value=EMPTY_MONTH_HTML))
    fallback = Mock(side_effect=AssertionError("valid empty month needs no fallback"))
    monkeypatch.setattr(tnb, "fetch_page_with_reader_fallback", fallback)

    assert tnb.scrape_month(2027, 11) == []
    fallback.assert_not_called()
    assert capsys.readouterr().out == ""


def test_scrape_month_recovers_empty_month_after_https_reader_422(monkeypatch, capsys):
    from services import http

    monkeypatch.setattr(tnb, "fetch_page", Mock(side_effect=HttpError("HTTP 422")))
    fetch = Mock(side_effect=[HttpError("blocked origin"), EMPTY_MONTH_HTML])
    monkeypatch.setattr(http, "fetch_page", fetch)
    http.reset_fetch_failures()

    assert tnb.scrape_month(2027, 11) == []
    assert fetch.call_args_list[-1].args == (
        "https://r.jina.ai/http://www.tnb.ro/ro/calendar?year=2027&month=11&view=list",
    )
    assert http.get_fetch_failures() == []
    assert capsys.readouterr().out == ""


def test_scrape_month_rejects_challenge_instead_of_treating_it_as_empty(monkeypatch, capsys):
    from services import http

    monkeypatch.setattr(tnb, "fetch_page", Mock(return_value="<h1>Verify you are human</h1>"))
    monkeypatch.setattr(http, "fetch_page", Mock(return_value="<h1>Verify you are human</h1>"))
    http.reset_fetch_failures()

    assert tnb.scrape_month(2026, 11) == []
    assert "Failed to fetch TNB calendar for 2026/11" in capsys.readouterr().out
    assert len(http.get_fetch_failures()) == 1
    http.reset_fetch_failures()
