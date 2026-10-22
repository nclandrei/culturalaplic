from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import godot


@pytest.mark.parametrize("repeated_page", [False, True])
def test_scrape_uses_the_performance_time_from_the_detail_page(monkeypatch, repeated_page):
    listing_html = """
    <div class="show-item">
      <div class="about-col">
        <h2 class="title">
          <a href="/spectacole/vino-veritas-30/">Vino Veritas</a>
        </h2>
        <div class="home-show-box">
          <div class="hsb-box-1">20</div>
          <div class="hsb-box-2">septembrie duminică 2026</div>
        </div>
        <div class="show-label">TEATRU</div>
      </div>
    </div>
    """
    detail_html = """
    <div class="show-info-box">
      <span class="show-label">Ora:</span> 6:30 pm<br>
    </div>
    """
    if repeated_page:
        listing_html += '<link rel="next" href="/spectacole/page/2/">'
    unexpected_urls = []

    def fetch(url: str, **kwargs) -> str:
        if url == godot.reader_url(godot.EVENTS_URL):
            return listing_html
        if repeated_page and url == godot.reader_url(f"{godot.EVENTS_URL}page/2/"):
            return listing_html
        if url == godot.reader_url(
            f"{godot.BASE_URL}/spectacole/vino-veritas-30/"
        ):
            return detail_html
        unexpected_urls.append(url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(godot, "fetch_page", fetch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 19)

    with patch.object(godot, "datetime", FixedDatetime):
        events = godot.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 20, 18, 30)
    assert unexpected_urls == []
