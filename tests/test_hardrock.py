from bs4 import BeautifulSoup

from datetime import datetime

from scrapers.music.hardrock import parse_event, scrape_page


def test_parse_event_skips_non_live_promotions():
    html = """
    <div class="calListDayEvent">
      <h3 class="calListDay"
          data-date-year-number="2026"
          data-date-month-number="7"
          data-date-day-number="13"></h3>
      <div class="calListDayEventTitle">HAPPY MONDAY</div>
      <a class="calListDayEventLink" href="?date=2026-07-13"></a>
      <div class="calListDayEventCategory">Food and Beverage Promotions</div>
      <div class="calListDayEventDescription">Buy one, get one free.</div>
    </div>
    """

    event_div = BeautifulSoup(html, "html.parser").select_one(
        ".calListDayEvent"
    )

    assert parse_event(event_div) is None


def test_scrape_page_uses_the_official_detail_start_time(monkeypatch):
    list_html = """
    <div class="calListDayEvent">
      <h3 class="calListDay"
          data-date-year-number="2026"
          data-date-month-number="8"
          data-date-day-number="19"></h3>
      <div class="calListDayEventTitle">Andrada Live Concert on the Terrace</div>
      <a class="calListDayEventLink"
         href="?date=8/19/2026&amp;display=event&amp;eventid=2583987"></a>
      <div class="calListDayEventCategory">Live Events</div>
      <div class="calListDayEventDescription">Free admission</div>
    </div>
    """
    detail_html = """
    <div class="calListDayEventTime">9:00 PM - 10:00 PM</div>
    """
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return detail_html if "display=event" in url else list_html

    monkeypatch.setattr("scrapers.music.hardrock.fetch_page", fake_fetch)

    events, has_next = scrape_page()

    assert has_next is False
    assert len(events) == 1
    assert events[0].date == datetime(2026, 8, 19, 21, 0)
    assert len(calls) == 2
    assert calls[1][1] == {}
