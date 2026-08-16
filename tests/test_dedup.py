"""Tests for deduplication logic."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from models import Event
from services.dedup import (
    canonicalize_url,
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


class TestUrlCanonicalization:
    def test_identity_query_parameters_are_preserved(self):
        first = canonicalize_url("https://control-club.ro/event/?slug=first")
        second = canonicalize_url("https://control-club.ro/event/?slug=second")

        assert first != second


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

    def test_same_canonical_url_and_datetime_prefers_curated_source(self):
        eventbook = make_event(
            "Magnus ÖSTRÖM & Andrii POKAZ",
            "Sala Dalles București",
            datetime(2026, 9, 4, 19, 0),
            source="eventbook",
            title=(
                "Magnus ÖSTRÖM & Andrii POKAZ / Sara ALDEN Trio / "
                "JAZZAMBASSADEN la Jazz Fan Rising BUCUREȘTI"
            ),
        )
        jfr = make_event(
            "Magnus ÖSTRÖM & Andrii POKAZ / Sara ALDEN Trio / JAZZAMBASSADEN",
            "Sala Dalles București",
            datetime(2026, 9, 4, 19, 0),
            source="jfr",
            title=eventbook.title,
        )
        eventbook.url = (
            "https://www.eventbook.ro/music/bilete-jazzamnassaden-jfr-bucuresti/"
            "?utm_source=agenda#tickets"
        )
        jfr.url = "http://eventbook.ro/music/bilete-jazzamnassaden-jfr-bucuresti"

        result = stage1_dedup([eventbook, jfr])

        assert result == [jfr]

    def test_same_url_keeps_separate_performance_times(self):
        matinee = make_event(
            "Company",
            "TNB",
            datetime(2026, 9, 5, 11, 0),
            source="eventbook",
            title="Two-show production",
        )
        evening = make_event(
            "Company",
            "TNB",
            datetime(2026, 9, 5, 19, 0),
            source="eventbook",
            title=matinee.title,
        )
        evening.url = matinee.url

        assert stage1_dedup([matinee, evening]) == [matinee, evening]

    @pytest.mark.parametrize(
        (
            "eventbook_title",
            "control_title",
            "month",
            "day",
            "eventbook_time",
            "control_time",
        ),
        [
            (
                "Kabinett [CO], Walentin Pauer, Nek, Duro Disco w/ Vast Solo & Kosta",
                "Kabinett [CO], Walentin Pauer, Nek, Duro Disco w/ Vast Solo & Kosta",
                8,
                21,
                (22, 0),
                (22, 0),
            ),
            ("ctrl LIVE: King Automatic [FR]", "ctrl LIVE: King Automatic [FR]", 9, 6, (21, 0), (21, 0)),
            ("ctrl LIVE: JazzyBIT & K-lu", "LIVE: JazzyBIT & K-lu [RO]", 9, 10, (21, 0), (21, 0)),
            ("ctrl LIVE: past self [US]", "ctrl LIVE: past self [US]", 9, 16, (20, 0), (21, 0)),
            ("City of the Sun (USA) | Live at Control | 26.09.2026", "LIVE: City of the Sun [USA]", 9, 26, (20, 0), (20, 0)),
            ("ctrl LIVE: Holy Fuck [CA]", "ctrl LIVE: Holy Fuck [CA]", 10, 10, (20, 0), (20, 0)),
            ("Valerinne Live + Special Guests Ordinul Negru", "LIVE: Valerinne + Special Guests: Ordinul Negru [RO]", 10, 21, (20, 0), (21, 0)),
            ("The Underground Youth | Live at Control | 24.10.2026", "LIVE: The Underground Youth [UK/DE]", 10, 24, (20, 0), (20, 0)),
            ("Jozef Van Wissem | Control Club | 29.10.2026", "LIVE: Jozef Van Wissem [NL]", 10, 29, (20, 0), (20, 0)),
            ("Alt Jazz: Elijah Fox [USA]", "Alt Jazz: Elijah Fox [USA]", 11, 2, (19, 30), (19, 30)),
            ("ctrl LIVE: The Veils", "ctrl LIVE: The Veils", 11, 6, (20, 0), (20, 0)),
            ("ctrl LIVE: Imarhan [Algeria]", "ctrl LIVE: Imarhan [Algeria]", 11, 7, (19, 0), (20, 0)),
            ("The Notwist (DE) | Live at Control | 21.11.2026", "LIVE: The Notwist [DE]", 11, 21, (20, 0), (20, 0)),
            ("ctrl LIVE: Arab Strap [UK]", "ctrl LIVE: Arab Strap [UK]", 11, 26, (19, 0), (20, 0)),
            ("ctrl LIVE: DELUXE [FR]", "ctrl LIVE: DELUXE [FR]", 11, 28, (19, 0), (20, 0)),
        ],
    )
    def test_control_eventbook_overlap_prefers_first_party_occurrence(
        self,
        eventbook_title,
        control_title,
        month,
        day,
        eventbook_time,
        control_time,
    ):
        eventbook = make_event(
            None,
            "Club Control",
            datetime(2026, month, day, *eventbook_time),
            source="eventbook",
            title=eventbook_title,
        )
        control = make_event(
            None,
            "Control Club - Berlin Room",
            datetime(2026, month, day, *control_time),
            source="control",
            title=control_title,
        )

        assert stage1_dedup([eventbook, control]) == [control]

    def test_cross_source_day_match_preserves_ambiguous_multiple_performances(self):
        eventbook = make_event(
            None,
            "Club Control",
            datetime(2026, 9, 5, 20, 0),
            source="eventbook",
            title="Artist | Live at Control | 05.09.2026",
        )
        early = make_event(
            None,
            "Control Club - Front Room",
            datetime(2026, 9, 5, 19, 0),
            source="control",
            title="LIVE: Artist",
        )
        late = make_event(
            None,
            "Control Club - Berlin Room",
            datetime(2026, 9, 5, 21, 0),
            source="control",
            title="LIVE: Artist",
        )

        assert stage1_dedup([eventbook, early, late]) == [eventbook, early, late]

    def test_cross_source_day_match_preserves_far_apart_performances(self):
        matinee = make_event(
            None,
            "Club Control",
            datetime(2026, 9, 5, 11, 0),
            source="eventbook",
            title="Artist | Live at Control | 05.09.2026",
        )
        evening = make_event(
            None,
            "Control Club - Berlin Room",
            datetime(2026, 9, 5, 19, 0),
            source="control",
            title="LIVE: Artist",
        )

        assert stage1_dedup([matinee, evening]) == [matinee, evening]

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
