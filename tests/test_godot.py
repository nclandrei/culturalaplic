from datetime import datetime

from scrapers.theatre import godot


def test_scrape_uses_the_performance_time_from_the_detail_page(monkeypatch):
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

    def fetch(url: str, **kwargs) -> str:
        if url == godot.reader_url(godot.EVENTS_URL):
            return listing_html
        if url == godot.reader_url(
            f"{godot.BASE_URL}/spectacole/vino-veritas-30/"
        ):
            return detail_html
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(godot, "fetch_page", fetch)

    events = godot.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 20, 18, 30)
