from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.culture.elvirepopescu import parse_event


def test_parse_event_ignores_material_icon_labels_in_date():
    card = BeautifulSoup(
        """
        <div class="shadow border mb-4 row">
          <div class="text-danger">
            <h5>
              <span class="msym">calendar_month</span>
              17 Aug 2026
              <span><span class="msym">schedule</span>18:00</span>
            </h5>
          </div>
          <a class="event-title" href="/film/bilete-comatogen?hall=cinema-elvire-popesco">
            <h5>COMATOGEN <span>15+</span></h5>
          </a>
          <h5 class="text-uppercase"><span>price:</span> 27 lei</h5>
        </div>
        """,
        "html.parser",
    )

    event = parse_event(card)

    assert event is not None
    assert event.title == "COMATOGEN"
    assert event.date == datetime(2026, 8, 17, 18, 0)
    assert event.url == "https://eventbook.ro/film/bilete-comatogen"
    assert event.price == "27 LEI"
