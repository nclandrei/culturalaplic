"""Unit tests for HTTP retry logic."""

from unittest.mock import Mock, patch

import httpx
import pytest
import respx
import services.http as http_service

from services.http import (
    fetch_page,
    get_fetch_failures,
    HttpError,
    reset_fetch_failures,
)


class TestHttpRetry:
    """Test exponential backoff retry behavior."""

    @respx.mock
    def test_success_on_first_try(self):
        """Should return content on successful request."""
        respx.get("https://example.com").respond(200, text="Hello World")

        result = fetch_page("https://example.com")

        assert result == "Hello World"
        assert respx.calls.call_count == 1

    @respx.mock
    def test_http_fetch_forwards_custom_headers(self):
        """Should support source-specific reader headers."""
        respx.get("https://example.com").respond(200, text="Reader HTML")

        result = fetch_page(
            "https://example.com",
            headers={"X-Return-Format": "html"},
        )

        assert result == "Reader HTML"
        assert respx.calls.last.request.headers["X-Return-Format"] == "html"

    @respx.mock
    def test_retry_on_429(self):
        """Should retry on 429 Too Many Requests."""
        route = respx.get("https://example.com")
        route.side_effect = [
            httpx.Response(429, text="Rate limited"),
            httpx.Response(429, text="Rate limited"),
            httpx.Response(200, text="Success"),
        ]

        result = fetch_page("https://example.com")

        assert result == "Success"
        assert respx.calls.call_count == 3

    @respx.mock
    def test_retry_on_503(self):
        """Should retry on 503 Service Unavailable."""
        route = respx.get("https://example.com")
        route.side_effect = [
            httpx.Response(503, text="Service down"),
            httpx.Response(200, text="Back up"),
        ]

        result = fetch_page("https://example.com")

        assert result == "Back up"
        assert respx.calls.call_count == 2

    @respx.mock
    def test_no_retry_on_404(self):
        """Should not retry on 404 Not Found."""
        respx.get("https://example.com").respond(404, text="Not found")

        reset_fetch_failures()
        with pytest.raises(HttpError) as exc_info:
            fetch_page("https://example.com")

        assert exc_info.value.status_code == 404
        assert respx.calls.call_count == 1
        assert get_fetch_failures() == ["HTTP 404 for https://example.com"]

    @respx.mock
    def test_exhausted_retries(self):
        """Should raise HttpError after exhausting retries."""
        respx.get("https://example.com").respond(429, text="Rate limited")

        with pytest.raises(HttpError) as exc_info:
            fetch_page("https://example.com")

        assert exc_info.value.status_code == 429
        assert respx.calls.call_count == 3

    @respx.mock
    def test_retry_on_connection_error(self):
        """Should retry on connection errors."""
        route = respx.get("https://example.com")
        route.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, text="Connected"),
        ]

        result = fetch_page("https://example.com")

        assert result == "Connected"
        assert respx.calls.call_count == 2

    def test_js_fetch_waits_for_requested_selector(self):
        """Should wait for asynchronous page content before reading the HTML."""
        with patch("services.http.sync_playwright") as mock_playwright:
            playwright = mock_playwright.return_value.__enter__.return_value
            page = playwright.chromium.launch.return_value.new_page.return_value
            page.content.return_value = "<div class='events-list-view'></div>"

            result = fetch_page(
                "https://example.com/events",
                needs_js=True,
                wait_selector=".events-list-view",
            )

        assert result == "<div class='events-list-view'></div>"
        page.wait_for_selector.assert_called_once_with(
            ".events-list-view", timeout=30000
        )

    def test_js_fetch_renders_bucharest_local_times(self):
        with patch("services.http.sync_playwright") as mock_playwright:
            playwright = mock_playwright.return_value.__enter__.return_value
            browser = playwright.chromium.launch.return_value
            browser.new_page.return_value.content.return_value = "<html></html>"

            fetch_page("https://example.com/events", needs_js=True)

        browser.new_page.assert_called_once_with(
            timezone_id="Europe/Bucharest",
        )

    def test_js_fetch_rejects_http_error_pages(self):
        with patch("services.http.sync_playwright") as mock_playwright:
            playwright = mock_playwright.return_value.__enter__.return_value
            page = playwright.chromium.launch.return_value.new_page.return_value
            page.goto.return_value.status = 403

            reset_fetch_failures()
            with pytest.raises(HttpError) as exc_info:
                fetch_page("https://example.com/events", needs_js=True)

        assert exc_info.value.status_code == 403
        assert get_fetch_failures() == [
            "HTTP 403 for https://example.com/events"
        ]

    def test_js_fetch_retries_transient_http_statuses(self):
        with patch("services.http.sync_playwright") as mock_playwright:
            playwright = mock_playwright.return_value.__enter__.return_value
            page = playwright.chromium.launch.return_value.new_page.return_value
            page.goto.side_effect = [Mock(status=503), Mock(status=200)]
            page.content.return_value = "<html>Recovered</html>"

            result = fetch_page("https://example.com/events", needs_js=True)

        assert result == "<html>Recovered</html>"
        assert page.goto.call_count == 2

    @respx.mock
    def test_empty_success_page_uses_html_reader_fallback(self):
        source_url = "https://example.com/events?year=2026&month=9"
        reader_url = (
            "https://r.jina.ai/https://example.com/events?year=2026&month=9"
        )
        respx.get(source_url).respond(200, text="<html>No event markup</html>")
        respx.get(reader_url).respond(
            200,
            text="<div class='event-marker'>Concert</div>",
        )

        result = http_service.fetch_page_with_reader_fallback(
            source_url,
            expected_text="event-marker",
        )

        assert "event-marker" in result
        assert respx.calls.call_count == 2
        assert respx.calls.last.request.headers["X-Return-Format"] == "html"

    @respx.mock
    def test_expected_markup_does_not_use_html_reader(self):
        source_url = "https://example.com/events"
        respx.get(source_url).respond(
            200,
            text="<div class='event-marker'>Concert</div>",
        )

        result = http_service.fetch_page_with_reader_fallback(
            source_url,
            expected_text="event-marker",
        )

        assert "event-marker" in result
        assert respx.calls.call_count == 1
