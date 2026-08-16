from datetime import datetime
from unittest.mock import patch

from scrapers.music.bfh import scrape


def test_scrape_preserves_unknown_artist_time_as_midnight():
    html = """
        <html><body>
          <h1>BIKERS FOR HUMANITY ROCK FEST 2026</h1>
          <div class="e-con">
            <h4>18 IUNIE</h4>
            <a href="https://example-band.test/">Example Band</a>
          </div>
        </body></html>
    """

    with patch("scrapers.music.bfh.fetch_page", return_value=html):
        events = scrape()

    assert len(events) == 1
    assert events[0].artist == "Example Band"
    assert events[0].date == datetime(2026, 6, 18)
