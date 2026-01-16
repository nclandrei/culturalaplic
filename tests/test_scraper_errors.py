"""Unit tests for scraper error collection and alerting."""

import traceback
from unittest.mock import MagicMock, patch

import pytest

from models import Event
from services.email import ScraperError, send_scraper_alert


def make_mock_scraper(name: str):
    """Create a mock scraper module with __name__ and scrape()."""
    mock = MagicMock()
    mock.__name__ = name
    return mock


class TestScraperErrorCollection:
    """Test that scraper errors are collected without breaking the flow."""

    def test_run_scraper_safely_success(self):
        """Should return events on successful scrape."""
        from main import run_scraper_safely, scraper_errors

        scraper_errors.clear()

        mock_scraper = make_mock_scraper("scrapers.music.test_scraper")
        mock_scraper.scrape.return_value = [
            MagicMock(spec=Event),
            MagicMock(spec=Event),
        ]

        result = run_scraper_safely(mock_scraper)

        assert len(result) == 2
        assert len(scraper_errors) == 0

    def test_run_scraper_safely_failure(self):
        """Should catch exception and record error."""
        from main import run_scraper_safely, scraper_errors

        scraper_errors.clear()

        mock_scraper = make_mock_scraper("scrapers.music.broken_scraper")
        mock_scraper.scrape.side_effect = ValueError("Element not found")

        result = run_scraper_safely(mock_scraper)

        assert result == []
        assert len(scraper_errors) == 1
        assert scraper_errors[0].scraper_name == "broken_scraper"
        assert "Element not found" in scraper_errors[0].error_message

    def test_multiple_scraper_failures_collected(self):
        """Should collect errors from multiple failed scrapers."""
        from main import run_scraper_safely, scraper_errors

        scraper_errors.clear()

        for name in ["scraper_a", "scraper_b", "scraper_c"]:
            mock_scraper = make_mock_scraper(f"scrapers.music.{name}")
            mock_scraper.scrape.side_effect = RuntimeError(f"{name} failed")
            run_scraper_safely(mock_scraper)

        assert len(scraper_errors) == 3
        names = [e.scraper_name for e in scraper_errors]
        assert names == ["scraper_a", "scraper_b", "scraper_c"]


class TestScraperAlertEmail:
    """Test scraper alert email formatting and sending."""

    def test_send_scraper_alert_skips_empty(self):
        """Should not send email when no errors."""
        with patch("services.email.resend.Emails.send") as mock_send:
            send_scraper_alert([], "test@example.com")
            mock_send.assert_not_called()

    def test_send_scraper_alert_formats_correctly(self):
        """Should format alert email with error details."""
        errors = [
            ScraperError(
                scraper_name="iabilet",
                error_message="Connection timeout",
                traceback="Traceback...\nTimeoutError: Connection timeout",
            ),
            ScraperError(
                scraper_name="control",
                error_message="Element not found",
                traceback="Traceback...\nValueError: Element not found",
            ),
        ]

        with patch("services.email.resend.Emails.send") as mock_send:
            with patch.dict("os.environ", {"RESEND_API_KEY": "test_key"}):
                send_scraper_alert(errors, "test@example.com")

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]

            assert "2 scraper(s) failed" in call_args["subject"]
            assert "iabilet" in call_args["text"]
            assert "control" in call_args["text"]
            assert "Connection timeout" in call_args["text"]
            assert "Element not found" in call_args["text"]
