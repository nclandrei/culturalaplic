from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import godot
from services import http


@pytest.mark.parametrize("fallback_page", [None, "listing", "detail"])
@pytest.mark.parametrize("primary_failure", ["blocked", "incomplete"])
def test_scrape_uses_the_performance_time_from_the_detail_page(
    monkeypatch, fallback_page, primary_failure,
):
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

    detail_url = f"{godot.BASE_URL}/spectacole/vino-veritas-30/"
    pages = {godot.EVENTS_URL: listing_html, detail_url: detail_html}
    fallback_url = {
        None: None, "listing": godot.EVENTS_URL, "detail": detail_url,
    }[fallback_page]
    calls = []

    def fetch(url: str, **kwargs) -> str:
        calls.append(url)
        if url in pages:
            assert kwargs["record_failure"] is False
            assert kwargs["needs_js"] is False
            if url == fallback_url:
                if primary_failure == "blocked":
                    raise http.HttpError("HTTP 403", status_code=403)
                return "<html>Verifying your browser</html>"
            return pages[url]
        if fallback_url and url == http.HTML_READER_BASE_URL + fallback_url:
            assert kwargs["headers"] == http.HTML_READER_HEADERS
            return pages[fallback_url]
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(http, "fetch_page", fetch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 19)

    with patch.object(godot, "datetime", FixedDatetime):
        events = godot.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 20, 18, 30)
    assert events[0].title == "Vino Veritas"
    assert events[0].url == detail_url
    expected_calls = [godot.EVENTS_URL]
    if fallback_page == "listing":
        expected_calls.append(http.HTML_READER_BASE_URL + godot.EVENTS_URL)
    expected_calls.append(detail_url)
    if fallback_page == "detail":
        expected_calls.append(http.HTML_READER_BASE_URL + detail_url)
    assert calls == expected_calls


def test_scrape_rejects_a_reader_challenge(monkeypatch, capsys):
    monkeypatch.setattr(
        http, "fetch_page", lambda *args, **kwargs: "Verifying your browser",
    )
    monkeypatch.setattr(http, "_fetch_failures", [])

    assert godot.scrape() == []
    assert "Reader page missing home-show-box" in capsys.readouterr().out
    assert len(http.get_fetch_failures()) == 1
