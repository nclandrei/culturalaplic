from datetime import datetime

from scrapers.music import expirat


def _card(slug: str, title_html: str, when: str) -> str:
    return f"""
<div class="col-sm-12 slot" data-event-list="item">
  <div class="box event-is-future">
    <a href="/{slug}/?ica_source=HPWhitelabel"><img alt="x"></a>
    <div class="desc">
      <a href="/{slug}/?ica_source=HPWhitelabel"><h1>{title_html}</h1></a>
      <div class="date-location">
        <p>Expirat Halele Carol, București</p>
        <p>{when}</p>
      </div>
    </div>
  </div>
</div>
"""


EXPIRAT_HTML = (
    _card(
        "bilete-byron-128427",
        "<strong>byron</strong> • Triptic: Electric / Acustic",
        "miercuri, 9 decembrie, ora 21:30 acces de la 20:00",
    )
    + _card("bilete-vama-134874", "Concert Vama", "miercuri, 20 ianuarie '27, ora 21:30")
    + _card("bilete-munte-132144", "Am Fost La Munte 10 ani | Live", "joi, 26 noiembrie acces de la 20:00")
)


def test_scrape_uses_official_iabilet_listing(monkeypatch):
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append((url, kwargs))
        return EXPIRAT_HTML

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)
    events = expirat.scrape()

    assert requests == [("https://expirat.iabilet.ro/", {"needs_js": False})]
    assert len(events) == 3


def test_parses_card_dates_years_and_titles():
    events = expirat.parse_events(EXPIRAT_HTML, datetime(2026, 11, 23))

    assert [(event.title, event.date) for event in events] == [
        ("Am Fost La Munte 10 ani | Live", datetime(2026, 11, 26)),
        ("byron • Triptic: Electric / Acustic", datetime(2026, 12, 9, 21, 30)),
        ("Concert Vama", datetime(2027, 1, 20, 21, 30)),
    ]
    byron = events[1]
    assert byron.artist == "byron"
    assert byron.venue == "Expirat Halele Carol"
    assert byron.url == "https://expirat.iabilet.ro/bilete-byron-128427/"
    assert byron.source == "expirat"


def test_yearless_date_after_new_year_rolls_forward():
    html = _card("bilete-x-1", "X", "vineri, 8 ianuarie, ora 21:00")
    events = expirat.parse_events(html, datetime(2026, 12, 28))
    assert events[0].date == datetime(2027, 1, 8, 21, 0)


def test_expirat_zero_results_are_monitored():
    assert expirat.MIN_EXPECTED_EVENTS == 1
