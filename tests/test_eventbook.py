from scrapers.music.eventbook import parse_date


def test_parse_date_preserves_event_time():
    event_date = parse_date("12 Jul 2026 18:30")

    assert event_date is not None
    assert event_date.year == 2026
    assert event_date.month == 7
    assert event_date.day == 12
    assert event_date.hour == 18
    assert event_date.minute == 30
