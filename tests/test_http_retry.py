"""Unit tests for HTTP retry logic."""

from unittest.mock import patch

import httpx
import pytest
import respx

from services.http import fetch_page, HttpError


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

        with pytest.raises(HttpError) as exc_info:
            fetch_page("https://example.com")

        assert exc_info.value.status_code == 404
        assert respx.calls.call_count == 1

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
