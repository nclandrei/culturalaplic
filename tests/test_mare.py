from datetime import datetime, time
from unittest.mock import patch

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

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 27, 12)

    with patch("scrapers.culture.mare.fetch_page_with_reader_fallback", return_value=html), \
         patch("scrapers.culture.mare.datetime", FixedDatetime):
        events = scrape()

    assert events
    assert {event.title for event in events} == {"Photographs by Constantin Brâncuși"}
    assert events[0].date.hour == 11
    assert events[0].url.endswith("/photographs-constantin-brancusi/")


def test_cross_year_exhibition_does_not_disappear_or_shift_years():
    assert parse_date_range("10.09.2026-24.05.2027") == (
        datetime(2026, 9, 10), datetime(2027, 5, 24),
    )
    assert parse_date_range("27.12-03.01.2027") == (
        datetime(2026, 12, 27), datetime(2027, 1, 3),
    )

    html = """
    <script type="application/ld+json">
      {"openingHours":["Monday,Wednesday,Thursday,Friday,Saturday,Sunday 11:00-19:00"]}
    </script>
    <a class="current__item" href="https://mare.ro/exhibition/imagini-ale-istoriei-istorii-ale-imaginii/">
      <h4>Imagini ale istoriei, istorii ale imaginii</h4>
      <span class="card-meta--period">10.09.2026-24.05.2027</span>
    </a>
    """
    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 27, 12)

    with patch("scrapers.culture.mare.fetch_page_with_reader_fallback", return_value=html), \
         patch("scrapers.culture.mare.datetime", FixedDatetime):
        events = scrape()

    assert events[0].date == datetime(2026, 9, 27, 11)
    assert events[-1].date == datetime(2026, 10, 26, 11)
    assert all(e.title == "Imagini ale istoriei, istorii ale imaginii" for e in events)


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
