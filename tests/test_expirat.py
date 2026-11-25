from datetime import datetime

from scrapers.music import expirat


EXPIRAT_HTML = """
<div data-event-list="item">
  <a href="/bilete-byron-128427/?ica_source=HPWhitelabel"><img></a>
  <div class="desc">
    <a href="/bilete-byron-128427/?ica_source=HPWhitelabel">
      <h1><strong>byron</strong> • Triptic</h1>
    </a>
    <div class="date-location">
      <p>Expirat Halele Carol, București</p>
      <p>miercuri, 9 decembrie, ora 21:30   acces de la 20:00</p>
    </div>
  </div>
</div>
<div data-event-list="item"><div class="desc">
  <a href="/bilete-doors-only-1/"><h1>Doors Only</h1></a>
  <div class="date-location"><p>Expirat Halele Carol, București</p>
  <p>joi, 26 noiembrie acces de la 20:00</p></div>
</div></div>
<div data-event-list="item"><div class="desc">
  <a href="/bilete-next-year-2/"><h1>Next Year</h1></a>
  <div class="date-location"><p>Expirat Halele Carol, București</p>
  <p>joi, 21 ianuarie '27, ora 21:30 acces de la 20:00</p></div>
</div></div>
"""


def test_scrape_parses_official_iabilet_cards(monkeypatch):
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append((url, kwargs))
        return EXPIRAT_HTML

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 25, 12, 0)

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(expirat, "datetime", FixedDatetime)

    events = expirat.scrape()

    assert requests == [
        ("https://expirat.iabilet.ro/", {"needs_js": False}),
    ]
    assert [(e.title, e.date) for e in events] == [
        ("Doors Only", datetime(2026, 11, 26, 20, 0)),
        ("byron • Triptic", datetime(2026, 12, 9, 21, 30)),
        ("Next Year", datetime(2027, 1, 21, 21, 30)),
    ]
    assert events[1].artist == "byron"
    assert events[1].venue == "Expirat Halele Carol"
    assert events[1].url == "https://expirat.iabilet.ro/bilete-byron-128427/"
    assert events[1].source == "expirat"


def test_card_date_without_year_rolls_into_next_year():
    assert expirat.parse_card_date(
        "luni, 5 ianuarie, ora 21:00", datetime(2026, 11, 25)
    ) == datetime(2027, 1, 5, 21, 0)


def test_expirat_zero_results_are_monitored():
    assert expirat.MIN_EXPECTED_EVENTS == 1
