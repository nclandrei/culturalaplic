from datetime import datetime
from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup

from scrapers.theatre import tnb
from services.http import HttpError


TICKETS_HTML = """
<div class="day">
  <div class="left_date">
    <div class="number">05</div><div class="month">11</div>
    <div class="year">2027</div>
  </div>
  <div class="right_date"><table id="show_list">
    <tr>
      <td class="c1"><div class="title expozitie">
        <a href="https://www.tnb.ro/ro/amintiri-din-copilarie"><h1>Amintiri din copilărie</h1></a>
        <h3>de Ion Creangă</h3>
      </div></td>
      <td class="c2">Sala Atelier</td><td class="c3">11:30</td>
      <td class="c4"><a href="https://www.bilet.ro/example">Cumpără bilete</a></td>
    </tr>
    <tr>
      <td class="c1"><div class="title expozitie">
        <a href="/ro/amintiri-din-copilarie"><h1>Amintiri din copilărie</h1></a>
      </div></td>
      <td class="c2">TNB - Sala Atelier</td><td class="c3">19:00</td>
      <td class="c4">Vândut</td>
    </tr>
  </table></div>
</div>
"""


def test_parse_ticket_day_keeps_times_halls_and_sold_out_shows():
    day = BeautifulSoup(TICKETS_HTML, "html.parser").select_one("div.day")
    events = tnb.parse_day(day)
    assert [event.date for event in events] == [
        datetime(2027, 11, 5, 11, 30), datetime(2027, 11, 5, 19),
    ]
    assert [event.title for event in events] == ["Amintiri din copilărie"] * 2
    assert [event.venue for event in events] == ["TNB - Sala Atelier"] * 2
    assert events[1].url == "https://www.tnb.ro/ro/amintiri-din-copilarie"


def test_scrape_fetches_all_dates_once_and_deduplicates(monkeypatch):
    fetch = Mock(return_value=TICKETS_HTML * 2 + TICKETS_HTML.replace("2027", "2020"))
    monkeypatch.setattr(tnb, "fetch_page", fetch)
    events = tnb.scrape()
    assert len(events) == 2
    assert events[0].date == datetime(2027, 11, 5, 11, 30)
    fetch.assert_called_once_with(
        "https://r.jina.ai/https://www.tnb.ro/ro/bilete-online",
        headers={"X-Return-Format": "html"}, timeout=60000, record_failure=False,
    )


@pytest.mark.parametrize("response", [HttpError("HTTP 422"), "<title>Blocked</title>"])
def test_scrape_retries_official_page_if_reader_fails(monkeypatch, response):
    fetch = Mock(side_effect=response) if isinstance(response, Exception) else Mock(return_value=response)
    monkeypatch.setattr(tnb, "fetch_page", fetch)
    fallback = Mock(return_value=TICKETS_HTML)
    monkeypatch.setattr(tnb, "fetch_page_with_reader_fallback", fallback)
    assert len(tnb.scrape()) == 2
    fallback.assert_called_once_with(
        tnb.EVENTS_URL, expected_text='id="show_list"', timeout=60000,
    )


def test_scrape_does_not_swallow_terminal_failure(monkeypatch):
    monkeypatch.setattr(tnb, "fetch_page", Mock(side_effect=HttpError("HTTP 422")))
    monkeypatch.setattr(tnb, "fetch_page_with_reader_fallback", Mock(side_effect=HttpError("offline")))
    with pytest.raises(HttpError, match="offline"):
        tnb.scrape()
