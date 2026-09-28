from datetime import datetime
from unittest.mock import patch

from bs4 import BeautifulSoup

from scrapers.culture import improteca


def make_article(url: str, excerpt: str) -> BeautifulSoup:
    return BeautifulSoup(
        f"""
        <article class="elementor-post">
          <h2 class="elementor-post__title">
            <a href="{url}">Eveniment Improteca</a>
          </h2>
          <div class="elementor-post__excerpt"><p>{excerpt}</p></div>
        </article>
        """,
        "html.parser",
    ).select_one("article")


def test_parse_date_treats_textual_range_as_august_not_february():
    event_date = improteca.parse_date(
        "1–2 August 2026 | 12:00–15:00",
        datetime(2026, 7, 21),
    )

    assert event_date == datetime(2026, 8, 1, 12, 0)


def test_parse_date_uses_earliest_date_when_a_later_range_exists():
    event_date = improteca.parse_date(
        "Perioade: 29 iunie - 3 iulie; 27-31 iulie, ora 11:00",
        datetime(2026, 6, 24),
    )

    assert event_date == datetime(2026, 6, 29, 11, 0)


def test_parse_event_uses_archive_publication_year_for_yearless_date():
    article = make_article(
        "https://improteca.ro/2024/01/12/laptic-sketch-comedy-improteca/",
        "Duminică, 21 ianuarie, ora 19:00, la Improteca.",
    )

    event = improteca.parse_event(article)

    assert event is not None
    assert event.date == datetime(2024, 1, 21, 19, 0)


def test_parse_event_handles_december_announcement_for_january():
    article = make_article(
        "https://improteca.ro/2025/12/20/show-de-ianuarie/",
        "Ne vedem pe 10 ianuarie, de la ora 20:00.",
    )

    event = improteca.parse_event(article)

    assert event is not None
    assert event.date == datetime(2026, 1, 10, 20, 0)


def test_scrape_stops_after_consecutive_archive_pages(monkeypatch):
    page_html = """
    <article class="elementor-post">
      <h2 class="elementor-post__title">
        <a href="https://improteca.ro/2024/01/12/old-show/">Old show</a>
      </h2>
      <div class="elementor-post__excerpt"><p>21 ianuarie, ora 19:00</p></div>
    </article>
    <div class="e-load-more-anchor" data-max-page="36"></div>
    """
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append(url)
        return page_html

    monkeypatch.setattr(improteca, "fetch_page", fake_fetch_page)

    events = improteca.scrape()

    assert events == []
    assert requests == [
        "https://improteca.ro/calendar-evenimente/",
        "https://improteca.ro/calendar-evenimente/2/",
    ]


def test_course_uses_both_explicit_first_meetings_and_detail_start_time(monkeypatch):
    course_url = "https://improteca.ro/2026/09/25/curs-pentru-incepatori/"
    listing = f"""
    <article class="elementor-post"><h2 class="elementor-post__title"><a href="{course_url}">
      Curs de improvizatie pentru incepatori</a></h2>
      <div class="elementor-post__excerpt">13 octombrie 2026, ora 20:00 📍 Vechea sală 📅</div>
    </article>
    """
    detail = "<p>În fiecare marți, 18:00-20:00. Primele întâlniri: 6 și 13 octombrie 2026. Sala de repetiții: Negustori 25 Trainer: Andrei</p>"
    requests = []

    def fetch(url, **kwargs):
        requests.append(url)
        return listing if url == improteca.EVENTS_URL else detail

    monkeypatch.setattr(improteca, "fetch_page", fetch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 27)

    with patch.object(improteca, "datetime", FixedDatetime):
        events = improteca.scrape()

    assert [e.date for e in events] == [
        datetime(2026, 10, 6, 18), datetime(2026, 10, 13, 18),
    ]
    assert [e.venue for e in events] == ["Negustori 25", "Negustori 25"]
    assert requests == [improteca.EVENTS_URL, course_url]
