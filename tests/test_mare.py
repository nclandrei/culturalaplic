from datetime import datetime, time
from unittest.mock import patch

import pytest

from scrapers.culture.mare import expand_exhibition, parse_date_range, scrape


def test_scrape_reads_current_exhibition_from_live_card_markup():
    html = """
    <script type="application/ld+json">
      {"@type":"Organization",
       "openingHours":["Monday,Wednesday,Thursday,Friday,Saturday,Sunday 11:00-19:00"]}
    </script>
    <section class="current">
      <div class="current__grid"></div>
    </section>
    <div class="past__grid is-collapsed">
      <a href="https://mare.ro/exhibition/photographs-constantin-brancusi/"
         class="current__item">
        <div class="current__item__info">
          <h4 class="h4 uppercase bold">Photographs by Constantin Brâncuși</h4>
          <span class="card-meta card-meta--period">22 mai - 27 sep 2026</span>
        </div>
      </a>
    </div>
    """

    with (
        patch("scrapers.culture.mare.fetch_page_with_reader_fallback", return_value=html),
        patch("scrapers.culture.mare.datetime") as clock,
    ):
        clock.now.return_value = datetime(2026, 9, 27, 12)
        clock.side_effect = datetime
        clock.combine = datetime.combine
        events = scrape()

    assert events
    assert {event.title for event in events} == {"Photographs by Constantin Brâncuși"}
    assert events[0].date.hour == 11
    assert events[0].url.endswith("/photographs-constantin-brancusi/")


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("10.09.2026-24.05.2027", datetime(2026, 9, 10), datetime(2027, 5, 24)),
        ("13.08-15.11.2026", datetime(2026, 8, 13), datetime(2026, 11, 15)),
        ("10.09.2026 – 24.05.2027", datetime(2026, 9, 10), datetime(2027, 5, 24)),
    ],
)
def test_listing_date_ranges(text, start, end):
    assert parse_date_range(text) == (start, end)


def test_exhibition_end_date_is_inclusive_through_its_opening_day():
    events = expand_exhibition(
        title="Bernard Frize",
        url="https://mare.ro/exhibition/bernard-frize/",
        start_date=datetime(2026, 5, 22),
        end_date=datetime(2026, 8, 16),
        opening_weekdays={0, 2, 3, 4, 5, 6},
        opening_time=time(11, 0),
        now=datetime(2026, 8, 16, 12, 0),
    )

    assert [event.date for event in events] == [datetime(2026, 8, 16, 11, 0)]
