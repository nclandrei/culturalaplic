from datetime import datetime, timedelta

from main import MAX_EVENT_HORIZON_DAYS, cleanup_past_events


def event_at(event_date: datetime) -> dict:
    return {
        "title": "Test event",
        "date": event_date.isoformat(),
        "source": "test",
    }


def test_cleanup_keeps_current_and_plausible_future_events():
    now = datetime.now()
    events = [
        event_at(now),
        event_at(now + timedelta(days=MAX_EVENT_HORIZON_DAYS)),
    ]

    assert cleanup_past_events(events) == events


def test_cleanup_rejects_implausibly_distant_and_invalid_dates():
    now = datetime.now()
    events = [
        event_at(now + timedelta(days=MAX_EVENT_HORIZON_DAYS + 1)),
        {"title": "Broken date", "date": "2040-not-a-date", "source": "test"},
    ]

    assert cleanup_past_events(events) == []
