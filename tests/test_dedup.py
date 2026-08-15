"""Tests for deduplication logic."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from models import Event
from services.dedup import (
    llm_dedup,
    normalize_venue,
    sanitize_venue,
    stage1_dedup,
)


def make_event(
    artist: str | None,
    venue: str,
    date: datetime,
    source: str = "test",
    title: str | None = None,
) -> Event:
    return Event(
        title=title or f"{artist} at {venue}",
        artist=artist,
        venue=venue,
        date=date,
        url=f"https://{source}.ro/{(artist or title or 'event').lower().replace(' ', '-')}",
        source=source,
        category="music",
    )


class TestVenueNormalization:
    def test_sanitize_venue_lowercase(self):
        assert sanitize_venue("CONTROL CLUB") == "control club"

    def test_sanitize_venue_removes_punctuation(self):
        assert sanitize_venue("Hard Rock Cafe!") == "hard rock cafe"

    def test_sanitize_venue_collapses_whitespace(self):
        assert sanitize_venue("Control   Club") == "control club"

    def test_normalize_venue_resolves_alias(self):
        assert normalize_venue("Control Club") == "control"
        assert normalize_venue("club control") == "control"
        assert normalize_venue("Control Bucuresti") == "control"

    def test_normalize_venue_unknown_passes_through(self):
        assert normalize_venue("Some Unknown Venue") == "some unknown venue"


class TestStage1Dedup:
    def test_empty_list(self):
        assert stage1_dedup([]) == []

    def test_no_duplicates(self):
        events = [
            make_event("Artist A", "Venue 1", datetime(2026, 3, 15)),
            make_event("Artist B", "Venue 2", datetime(2026, 3, 16)),
        ]
        result = stage1_dedup(events)
        assert len(result) == 2

    def test_exact_duplicate_removed(self):
        events = [
            make_event("The Cure", "Control", datetime(2026, 3, 15), "iabilet"),
            make_event("The Cure", "Control", datetime(2026, 3, 15), "eventbook"),
        ]
        result = stage1_dedup(events)
        assert len(result) == 1
        assert result[0].source == "iabilet"

    def test_venue_alias_detected(self):
        events = [
            make_event("The Cure", "Control", datetime(2026, 3, 15)),
            make_event("The Cure", "Control Club", datetime(2026, 3, 15)),
        ]
        result = stage1_dedup(events)
        assert len(result) == 1

    def test_fuzzy_artist_match(self):
        events = [
            make_event("Depeche Mode", "Arena", datetime(2026, 3, 15)),
            make_event("Depeche  Mode", "Arena", datetime(2026, 3, 15)),
        ]
        result = stage1_dedup(events)
        assert len(result) == 1

    def test_different_dates_not_duplicates(self):
        events = [
            make_event("The Cure", "Control", datetime(2026, 3, 15)),
            make_event("The Cure", "Control", datetime(2026, 3, 16)),
        ]
        result = stage1_dedup(events)
        assert len(result) == 2

    def test_same_source_keeps_separate_same_day_showtimes(self):
        events = [
            make_event(
                None,
                "TNB",
                datetime(2026, 9, 5, 11, 0),
                source="tnb",
                title="Amintiri din copilărie",
            ),
            make_event(
                None,
                "TNB",
                datetime(2026, 9, 5, 19, 0),
                source="tnb",
                title="Amintiri din copilărie",
            ),
        ]

        result = stage1_dedup(events)

        assert [event.date.hour for event in result] == [11, 19]

    def test_different_sources_still_merge_unknown_and_known_times(self):
        events = [
            make_event(
                "byron",
                "Expirat",
                datetime(2026, 8, 19),
                source="iabilet",
                title="byron live",
            ),
            make_event(
                "byron",
                "Expirat Halele Carol",
                datetime(2026, 8, 19, 21, 30),
                source="expirat",
                title="byron live",
            ),
        ]

        assert len(stage1_dedup(events)) == 1

    def test_artistless_events_use_title_for_deduplication(self):
        events = [
            make_event(
                None,
                "MNAC",
                datetime(2026, 8, 15),
                title="Boite, Box, Brancusi",
            ),
            make_event(
                None,
                "MNAC",
                datetime(2026, 8, 15),
                title="Seeing History",
            ),
            make_event(
                None,
                "MNAC",
                datetime(2026, 8, 15),
                source="duplicate-feed",
                title="Boite, Box, Brancusi",
            ),
        ]

        result = stage1_dedup(events)

        assert [event.title for event in result] == [
            "Boite, Box, Brancusi",
            "Seeing History",
        ]


class TestLLMDedup:
    def test_empty_list(self):
        assert llm_dedup([]) == []

    def test_single_event(self):
        events = [make_event("Artist", "Venue", datetime(2026, 3, 15))]
        assert llm_dedup(events) == events

    def test_no_api_key_returns_unchanged(self):
        events = [
            make_event("The Cure", "Control", datetime(2026, 3, 15)),
            make_event("Cure", "Control Club", datetime(2026, 3, 15)),
        ]
        with patch.dict("os.environ", {}, clear=True):
            result = llm_dedup(events)
        assert len(result) == 2

    @patch("services.dedup.genai.Client")
    def test_llm_identifies_duplicates(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.text = '{"duplicates": [[0, 1]]}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        events = [
            make_event("The Cure", "Arenele Romane", datetime(2026, 3, 15), "iabilet"),
            make_event("Cure", "Arenele Romane Bucuresti", datetime(2026, 3, 15), "eventbook"),
            make_event("Depeche Mode", "Arena Nationala", datetime(2026, 4, 20)),
        ]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = llm_dedup(events)

        assert len(result) == 2
        assert result[0].artist == "The Cure"
        assert result[1].artist == "Depeche Mode"

    @patch("services.dedup.genai.Client")
    def test_llm_no_duplicates_found(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.text = '{"duplicates": []}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        events = [
            make_event("Artist A", "Venue 1", datetime(2026, 3, 15)),
            make_event("Artist B", "Venue 2", datetime(2026, 3, 16)),
        ]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = llm_dedup(events)

        assert len(result) == 2

    @patch("services.dedup.genai.Client")
    def test_llm_handles_markdown_response(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.text = '```json\n{"duplicates": [[0, 1]]}\n```'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        events = [
            make_event("The Cure", "Control", datetime(2026, 3, 15)),
            make_event("Cure", "Control", datetime(2026, 3, 15)),
        ]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = llm_dedup(events)

        assert len(result) == 1

    @patch("services.dedup.genai.Client")
    def test_llm_error_returns_original(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        events = [
            make_event("Artist A", "Venue", datetime(2026, 3, 15)),
            make_event("Artist B", "Venue", datetime(2026, 3, 15)),
        ]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = llm_dedup(events)

        assert len(result) == 2
