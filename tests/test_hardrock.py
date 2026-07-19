from bs4 import BeautifulSoup

from scrapers.music.hardrock import parse_event


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
