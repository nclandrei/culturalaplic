from datetime import datetime

from scrapers.music import greenhours
from scrapers.theatre import greenhours as theatre_greenhours


def card(title: str, category: str, date: str, time: str, slug: str, venue: str = "UnderGreen") -> str:
    return f"""
    <a href="/eveniment/{slug}">
      <div class="q-card">
        <div class="absolute-top-left">{category}</div>
        <div class="q-card__actions"><div class="q-item">
          <div class="q-item__label">{title}</div>
          <div class="q-item__label">{venue}</div>
          <div class="q-item__label">{date}</div>
          <div class="q-item__label">{time}</div>
        </div></div>
      </div>
    </a>
    """


def test_parse_date_rolls_december_to_january_but_honours_explicit_year():
    now = datetime(2026, 12, 31, 12)

    assert greenhours.parse_date("Vin, 2 ian.", "19:30", now) == datetime(2027, 1, 2, 19, 30)
    assert greenhours.parse_date("2 ian. 2026", "19:30", now) == datetime(2026, 1, 2, 19, 30)


def test_scrape_all_keeps_distinct_same_date_shows_and_filters_bad_or_stale(monkeypatch):
    html = "".join(
        [
            card("Concert One", "Concert", "3 oct. 2099", "19:00", "concert-one"),
            card("Concert Two", "Concert", "3 oct. 2099", "19:00", "concert-two"),
            card("Old Show", "Teatru", "3 oct. 2020", "19:00", "old"),
            card("Impossible", "Teatru", "31 feb. 2099", "19:00", "bad-date"),
            card("Bad Time", "Concert", "4 oct. 2099", "25:00", "bad-time"),
        ]
    )
    monkeypatch.setattr(greenhours, "fetch_page", lambda *args, **kwargs: html)

    events = greenhours.scrape_all()

    assert [event.title for event in events] == ["Concert One", "Concert Two"]
    assert events[0].url == "https://www.bilet.ro/eveniment/concert-one"


def test_music_and_theatre_adapters_are_asymmetric(monkeypatch):
    html = "".join(
        [
            card("Marion Saliba", "Concert", "3 oct. 2099", "19:00", "marion"),
            card("Garden show", "Concert", "4 oct. 2099", "20:00", "garden", "Gradina Green Hours"),
            card("Această Sonia", "Teatru", "30 sept. 2099", "19:00", "sonia"),
            card("Dezastre Naturale", "Spectacol", "28 sept. 2099", "19:00", "dezastre"),
            card("Talk", "Conferinta", "4 oct. 2099", "19:00", "talk"),
        ]
    )
    monkeypatch.setattr(greenhours, "fetch_page", lambda *args, **kwargs: html)

    music = greenhours.scrape()
    theatre = theatre_greenhours.scrape()

    assert [(event.title, event.category, event.artist) for event in music] == [
        ("Marion Saliba", "music", "Marion Saliba"),
        ("Garden show", "music", "Garden show"),
    ]
    assert [event.venue for event in music] == [
        "Green Hours - UnderGreen", "Gradina Green Hours"
    ]
    assert [(event.title, event.category, event.artist) for event in theatre] == [
        ("Dezastre Naturale", "theatre", None),
        ("Această Sonia", "theatre", None),
    ]


def test_fetch_failure_is_not_swallowed(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(greenhours, "fetch_page", fail)

    try:
        greenhours.scrape_all()
    except RuntimeError as error:
        assert str(error) == "queue unavailable"
    else:
        raise AssertionError("fetch errors must remain observable")
