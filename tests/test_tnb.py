import json
from datetime import datetime, timezone
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
    assert events[1].url == "https://tnb.ro/ro/moroi-si-papadii-la-chisinau"


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
            "https://r.jina.ai/https://tnb.ro/ro/calendar?year=2026&month=9&view=list",
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
        "https://tnb.ro/ro/calendar?year=2026&month=10&view=list",
        expected_text="right_items", timeout=60000,
    )


def test_scrape_reads_full_ticket_programme_and_only_tnb_venues(monkeypatch):
    clock = Mock(wraps=datetime)
    clock.now.return_value = datetime(2026, 11, 16)
    monkeypatch.setattr(tnb, "datetime", clock)
    items = [
        {
            "id": 100 + day, "event": {"id": 200 + day},
            "title": f"Show {day}", "venue": {"name": "TNB - Sala Atelier"},
            "dateStart": datetime(2026, 12, day, 19, 30, tzinfo=timezone.utc).timestamp() * 1000,
        }
        for day in range(1, 18)
    ]
    state = {"instances": {"instances": items + [
        items[0], dict(items[0], title="Elsewhere", venue={"name": "Other theatre"}),
    ]}}
    html = '<script>window.__INITIAL_STATE__=' + json.dumps(state) + ';</script>'
    monkeypatch.setattr(tnb, "fetch_page", lambda *args, **kwargs: html)
    monkeypatch.setattr(tnb, "scrape_month", Mock(side_effect=AssertionError("calendar not needed")))

    events = tnb.scrape()
    assert len(events) == 17
    assert events[0].date == datetime(2026, 12, 1, 21, 30)
    assert events[-1].title == "Show 17"
    assert events[0].venue == "TNB - Sala Atelier"
    assert events[0].url == "https://www.bilet.ro/eveniment/tnb-201-101"
