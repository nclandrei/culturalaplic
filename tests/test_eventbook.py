from datetime import datetime
from unittest.mock import patch

from bs4 import BeautifulSoup

from scrapers.music import eventbook
from scrapers.music.eventbook import parse_date, parse_event_card


def test_parse_date_preserves_event_time():
    event_date = parse_date("12 Jul 2026 18:30")

    assert event_date is not None
    assert event_date.year == 2026
    assert event_date.month == 7
    assert event_date.day == 12
    assert event_date.hour == 18
    assert event_date.minute == 30


def test_parse_date_uses_show_time_from_weekday_date_with_four_digit_year():
    event_date = parse_date(
        "Sunday, 06 September 2026, Open Doors: 20:00 / Show Time: 21:00"
    )

    assert event_date == datetime(2026, 9, 6, 21, 0)


def test_parse_date_infers_year_and_uses_show_time():
    event_date = parse_date(
        "10 septembrie, open doors: 20:00, show time: 21:00"
    )

    assert event_date is not None
    assert event_date.month == 9
    assert event_date.day == 10
    assert event_date.hour == 21
    assert event_date.minute == 0


def test_parse_event_card_ignores_material_icon_labels_in_date():
    card = BeautifulSoup(
        """
        <div class="shadow border mb-4">
          <div class="text-danger">
            <h5>
              <span class="msym">calendar_month</span>
              15 Aug 2026
              <span><span class="msym">schedule</span>20:00</span>
            </h5>
          </div>
          <a href="/theater/bilete-frumosul-si-bestiile" class="event-title">
            <h5>Frumosul și Bestiile</h5>
          </a>
          <a href="/hall/ff-theatre">FF Theatre-Centru Vechi</a>
          <h5 class="text-uppercase">price: 70 lei + taxe</h5>
        </div>
        """,
        "html.parser",
    )

    event = parse_event_card(card)

    assert event is not None
    assert event.title == "Frumosul și Bestiile"
    assert event.category == "theatre"
    assert event.date == datetime(2026, 8, 15, 20, 0)
    assert event.venue == "FF Theatre-Centru Vechi"
    assert event.price == "70 LEI"


def test_scrape_all_keeps_separate_performances_with_the_same_url():
    page_one = """
      <div class="shadow mb-4">
        <div class="text-danger"><h5>1 Sep 2099 19:00</h5></div>
        <a class="event-title" href="/theater/repertory-show"><h5>Repertory Show</h5></a>
        <a href="/hall/test-theatre">Test Theatre</a>
      </div>
    """
    page_two = """
      <div class="shadow mb-4">
        <div class="text-danger"><h5>2 Sep 2099 19:00</h5></div>
        <a class="event-title" href="/theater/repertory-show"><h5>Repertory Show</h5></a>
        <a href="/hall/test-theatre">Test Theatre</a>
      </div>
    """

    with patch.object(
        eventbook,
        "fetch_page",
        side_effect=[page_one, page_two, ""],
    ):
        events = eventbook.scrape_all()

    assert [event.date.day for event in events] == [1, 2]
