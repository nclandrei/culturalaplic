from datetime import datetime

from scrapers.theatre.bulandra import parse_json_event


def event_data(room: str, **overrides):
    data = {
        "title": "FAMILY.EXE",
        "start": "2026-09-05T19:00:00+00:00",
        "terms": {"wcs_room": [{"name": room}]},
        "buttons": {
            "main": {
                "custom_url": False,
                "permalink": "https://www.bulandra.ro/family-exe/",
            }
        },
        "permalink": "https://www.bulandra.ro/program/instance/",
    }
    data.update(overrides)
    return data


def test_parse_json_event_keeps_only_bucharest_bulandra_halls():
    toma_caragiu = parse_json_event(
        event_data("Toma Caragiu (Jean-Louis Calderon 76A)")
    )
    liviu_ciulei = parse_json_event(
        event_data("Liviu Ciulei (Schitu Măgureanu nr. 1)")
    )
    iasi_tour = parse_json_event(event_data("Iași", title="ARTĂ"))

    assert toma_caragiu is not None
    assert toma_caragiu.date == datetime(2026, 9, 5, 19, 0)
    assert liviu_ciulei is not None
    assert iasi_tour is None


def test_parse_json_event_prefers_the_show_permalink():
    event = parse_json_event(event_data("Toma Caragiu"))

    assert event is not None
    assert event.url == "https://www.bulandra.ro/family-exe/"
