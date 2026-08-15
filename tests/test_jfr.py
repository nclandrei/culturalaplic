from datetime import datetime
from unittest.mock import patch

from scrapers.music import jfr


def test_scrape_ignores_icon_labels_and_keeps_only_bucharest_events():
    html = """
    <div class="shadow border mb-4 ms-3 me-3 d-flex row">
      <h4>
        <span class="msym">calendar_month</span>
        4 Sep 2026
        <span><span class="msym">schedule</span>19:00</span>
      </h4>
      <a class="event-title" href="/music/bilete-jazzamnassaden-jfr-bucuresti">
        <h5>Magnus ÖSTRÖM &amp; Andrii POKAZ / JAZZAMBASSADEN la Jazz Fan Rising BUCUREȘTI</h5>
      </a>
      <a href="/hall/sala-dalles">Sala Dalles București</a>
      <a href="/city/bucuresti">București</a>
    </div>
    <div class="shadow border mb-4 ms-3 me-3 d-flex row">
      <h4>
        <span class="msym">calendar_month</span>
        6 Oct 2026
        <span><span class="msym">schedule</span>19:00</span>
      </h4>
      <a class="event-title" href="/music/bilete-triosence-jfr-cluj">
        <h5>TRIOSENCE la Jazz Fan Rising CLUJ</h5>
      </a>
      <a href="/hall/academia-de-muzica">Academia de Muzică</a>
      <a href="/city/cluj">Cluj-Napoca</a>
    </div>
    """

    with patch.object(jfr, "fetch_page", return_value=html):
        events = jfr.scrape()

    assert len(events) == 1
    assert events[0].title == (
        "Magnus ÖSTRÖM & Andrii POKAZ / JAZZAMBASSADEN "
        "la Jazz Fan Rising BUCUREȘTI"
    )
    assert events[0].date == datetime(2026, 9, 4, 19, 0)
    assert events[0].venue == "Sala Dalles București"
    assert events[0].url == (
        "https://eventbook.ro/music/bilete-jazzamnassaden-jfr-bucuresti"
    )
    assert events[0].source == "jfr"
    assert events[0].category == "music"
