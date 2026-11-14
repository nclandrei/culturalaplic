from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import godot


@pytest.mark.parametrize("reader_has_time,live_has_time", [(True, True), (False, True), (False, False)])
def test_scrape_uses_the_performance_time_from_the_detail_page(monkeypatch, reader_has_time, live_has_time):
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
    live_requests = []

    def fetch(url: str, **kwargs) -> str:
        if url == godot.reader_url(godot.EVENTS_URL):
            return listing_html
        if url == godot.reader_url(
            f"{godot.BASE_URL}/spectacole/vino-veritas-30/"
        ):
            return detail_html if reader_has_time else "<main>Incomplete reader snapshot</main>"
        if url == f"{godot.BASE_URL}/spectacole/vino-veritas-30/":
            live_requests.append(kwargs)
            return detail_html if live_has_time else "<div class='show-info-box'>No time</div>"
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(godot, "fetch_page", fetch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 19)

    with patch.object(godot, "datetime", FixedDatetime):
        if not reader_has_time and not live_has_time:
            with pytest.raises(ValueError, match="Missing Godot performance time"):
                godot.scrape()
            return
        events = godot.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 20, 18, 30)
    assert len(live_requests) == (0 if reader_has_time else 1)
    if live_requests:
        assert live_requests[0]["needs_js"] is True
