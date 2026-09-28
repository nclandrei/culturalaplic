from datetime import datetime

import pytest

from scrapers.culture import cinemateca


def card(title: str, date: str, time: str, slug: str, hall: str) -> str:
    return f"""<div class="row shadow border">
      <div class="text-danger"><h5>
        <span>calendar_month</span>{date}<span>schedule</span>{time}
      </h5></div>
      <a class="event-title" href="/film/{slug}?hall={hall}"><h5>{title}</h5></a>
      <h5><span>price:</span> 15 lei</h5>
    </div>"""


def test_scrape_both_halls_and_all_pages_without_passes_or_stale_events(monkeypatch):
    film = card("The Film 15+", "2 Oct 2099", "17:30", "the-film", "cinema-eforie")
    pages = {
        "https://eventbook.ro/hall/cinema-eforie": (
            card("Abonament Cinematecă", "Septembrie 2099 - Iulie 2100", "", "abonament", "cinema-union")
            + card("Old film", "2 Oct 2020", "18:00", "old", "cinema-eforie")
            + film
            + '<a href="/hall/cinema-eforie?page=2">2</a>'
        ),
        "https://eventbook.ro/hall/cinema-eforie?page=2": film
        + card("Another film", "3 Oct 2099", "20:15", "another", "cinema-eforie"),
        "https://eventbook.ro/hall/cinema-union": card(
            "The Film", "2 Oct 2099", "19:00", "the-film", "cinema-union"
        ),
    }
    requests = []

    def fetch(url):
        requests.append(url)
        return pages[url]

    monkeypatch.setattr(cinemateca, "fetch_page", fetch)
    events = cinemateca.scrape()

    assert requests == list(pages)
    assert [(e.title, e.venue, e.date) for e in events] == [
        ("The Film", "Cinemateca Eforie", datetime(2099, 10, 2, 17, 30)),
        ("The Film", "Cinema Union", datetime(2099, 10, 2, 19)),
        ("Another film", "Cinemateca Eforie", datetime(2099, 10, 3, 20, 15)),
    ]
    assert events[0].url == "https://eventbook.ro/film/the-film"
    assert events[0].price == "15 LEI"
    assert all(e.category == "culture" and e.source == "cinemateca" for e in events)


def test_fetch_failure_in_second_hall_does_not_return_partial_feed(monkeypatch):
    def fetch(url):
        if url.endswith("cinema-union"):
            raise RuntimeError("Union unavailable")
        return card("Film", "2 Oct 2099", "17:30", "film", "cinema-eforie")

    monkeypatch.setattr(cinemateca, "fetch_page", fetch)
    with pytest.raises(RuntimeError, match="Union unavailable"):
        cinemateca.scrape()
