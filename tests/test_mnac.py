import json
from datetime import datetime
from unittest.mock import patch

from scrapers.culture import mnac


def timestamp_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def test_parse_exhibition_keeps_ongoing_and_permanent_exhibitions():
    now = datetime(2026, 8, 15, 12, 0)
    ongoing = {
        "rid": 1354,
        "nameRO": "Boîte, Box, Brâncuși",
        "eventStartDate": timestamp_ms(datetime(2026, 2, 19, 18, 30)),
        "eventEndDate": timestamp_ms(datetime(2026, 10, 15, 19, 30)),
        "permanent": False,
    }
    permanent = {
        "rid": 1029,
        "nameRO": "LEVIATHAN",
        "eventStartDate": timestamp_ms(datetime(2022, 5, 26, 12, 0)),
        "eventEndDate": None,
        "permanent": True,
    }

    ongoing_event = mnac.parse_exhibition(ongoing, now=now)
    permanent_event = mnac.parse_exhibition(permanent, now=now)

    assert ongoing_event is not None
    assert ongoing_event.date == datetime(2026, 8, 15, 11, 0)
    assert ongoing_event.url.endswith(
        "/event/1354/Bo%C3%AEte%2C%20Box%2C%20Br%C3%A2ncu%C8%99i"
    )
    assert permanent_event is not None
    assert permanent_event.date == datetime(2026, 8, 15, 11, 0)


def test_exhibition_occurrences_respect_temporary_closures():
    data = {
        "rid": 1372,
        "nameRO": "CECI N’EST PAS POP",
        "eventStartDate": timestamp_ms(datetime(2026, 5, 23, 18, 0)),
        "eventEndDate": timestamp_ms(datetime(2026, 10, 18, 18, 30)),
        "permanent": False,
        "descriptionRO": (
            "[Această expoziție este închisă temporar "
            "(12.08-06.09.2026).]"
        ),
    }

    events = mnac.parse_exhibition_occurrences(
        data,
        now=datetime(2026, 8, 16, 12, 0),
    )

    assert [event.date for event in events] == [
        datetime(2026, 9, day, 11, 0) for day in range(9, 14)
    ]


def test_undated_temporary_closure_suppresses_exhibition():
    data = {
        "rid": 1373,
        "nameRO": "LAURENȚIU RUȚĂ",
        "eventStartDate": timestamp_ms(datetime(2026, 5, 23, 18, 0)),
        "eventEndDate": timestamp_ms(datetime(2026, 10, 18, 18, 30)),
        "permanent": False,
        "descriptionRO": "[Această expoziție este închisă temporar.]",
    }

    assert mnac.parse_exhibition_occurrences(
        data,
        now=datetime(2026, 8, 16, 12, 0),
    ) == []


def test_scrape_reads_current_exhibitions_from_api():
    api_response = {
        "errorCode": 0,
        "numberOfPages": 1,
        "eventList": [
            {
                "rid": 1372,
                "nameRO": "CECI N’EST PAS POP",
                "eventStartDate": timestamp_ms(datetime(2026, 5, 23, 18, 0)),
                "eventEndDate": timestamp_ms(datetime(2099, 10, 18, 18, 30)),
                "permanent": False,
            }
        ],
    }

    def fetch(url: str, **kwargs) -> str:
        if url == mnac.EVENTS_URL:
            return "<div id='currentEvent'></div><div id='futureEvent'></div>"
        if url == mnac.CURRENT_EXHIBITIONS_URL:
            return json.dumps(api_response)
        if url == mnac.VISITING_HOURS_URL:
            return json.dumps(
                {"textRO": "Muzeu: miercuri – duminică – 11:00-18:30"}
            )
        raise AssertionError(f"Unexpected URL: {url}")

    with patch.object(mnac, "fetch_page", side_effect=fetch):
        events = mnac.scrape()

    assert events
    assert {event.title for event in events} == {"CECI N’EST PAS POP"}
    assert {event.category for event in events} == {"culture"}
    assert {event.venue for event in events} == {"MNAC"}
