from datetime import datetime
from unittest.mock import patch

from scrapers.music.garana import scrape


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 8, 16, tzinfo=tz)


def test_scrape_keeps_day_only_card_with_text_node_spacing_and_unknown_time():
    html = """
        <html><body>
          <h1>Line Up</h1>
          <section class="elementor-inner-section">
            <div class="elementor-column">
              <div class="ld-fh-element">Mindthegap Trio</div>
            </div>
            <div class="elementor-column">
              <div class="ld-fh-element">
                <span>Sâmbătă, 11 iulie</span>
                <span>Biserica Romano-Catolică Brebu Nou</span>
                <span>EXPERIMENTAL STAGE – Brebu Nou</span>
              </div>
            </div>
            <a class="elementor-button" href="/gjf-2026/mindthegap-trio/">Details</a>
          </section>
        </body></html>
    """

    with (
        patch("scrapers.music.garana.datetime", FixedDatetime),
        patch("scrapers.music.garana.fetch_page", return_value=html),
    ):
        events = scrape()

    assert len(events) == 1
    assert events[0].artist == "Mindthegap Trio"
    assert events[0].date == datetime(2026, 7, 11)
