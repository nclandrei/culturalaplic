from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from scrapers.music import expirat
from services.http import HttpError, get_fetch_failures, reset_fetch_failures


EXPIRAT_HTML = """
<div data-event-list="item">
  <a href="/bilete-byron-o-triptic-electric-acustic-improv-128427/?tracking=1">
    <h1>byron • Triptic: Electric / Acustic / Improv</h1>
  </a>
  <div class="date-location">
    Expirat Halele Carol, București
    miercuri, 19 august, ora 21:30 acces de la 20:00
  </div>
</div>
<script type="application/ld+json">
/*<![CDATA[*/
{
  "@type": "Event",
  "name": "byron • Triptic: Electric / Acustic / Improv",
  "url": "https://expirat.iabilet.ro/bilete-byron-o-triptic-electric-acustic-improv-128427/",
  "startDate": "2026-08-19",
  "location": {"name": "Expirat Halele Carol"},
  "offers": {"price": "90", "priceCurrency": "RON"}
}
/*]]>*/
</script>
"""


def test_scrape_uses_official_iabilet_feed(monkeypatch):
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append((url, kwargs))
        return EXPIRAT_HTML

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)

    events = expirat.scrape()

    assert requests == [
        ("https://expirat.iabilet.ro/", {"needs_js": False}),
    ]
    assert len(events) == 1
    assert events[0].title == "byron • Triptic: Electric / Acustic / Improv"
    assert events[0].artist == "byron"
    assert events[0].venue == "Expirat Halele Carol"
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
    assert events[0].price == "90 RON"
    assert events[0].source == "expirat"


def test_expirat_zero_results_are_monitored():
    assert expirat.MIN_EXPECTED_EVENTS == 1


def test_cards_without_listing_json_ld_fetch_detail_dates_and_prices(monkeypatch):
    soup = BeautifulSoup(EXPIRAT_HTML, "html.parser")
    soup.script.decompose()
    listing = str(soup)
    calls = []

    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return listing + listing if url == expirat.SCHEDULE_URL else EXPIRAT_HTML

    monkeypatch.setattr(expirat, "fetch_page", fetch)
    events = expirat.scrape()
    assert len(events) == 1
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
    assert events[0].price == "90 RON"
    assert calls == [
        (expirat.SCHEDULE_URL, {"needs_js": False}),
        ("https://expirat.iabilet.ro/bilete-byron-o-triptic-electric-acustic-improv-128427/?tracking=1",
         {"needs_js": False}),
    ]


def test_card_detail_missing_required_data_is_not_silently_dropped(monkeypatch):
    soup = BeautifulSoup(EXPIRAT_HTML, "html.parser")
    soup.script.decompose()
    monkeypatch.setattr(expirat, "fetch_page", lambda *args, **kwargs: str(soup))
    with pytest.raises(ValueError, match="detail missing event data"):
        expirat.scrape()


def test_invalid_structured_date_is_not_silently_dropped(monkeypatch):
    html = EXPIRAT_HTML.replace('"startDate": "2026-08-19"', '"startDate": "invalid"')
    monkeypatch.setattr(expirat, "fetch_page", lambda *args, **kwargs: html)
    with pytest.raises(ValueError, match="invalid required data"):
        expirat.scrape()


def test_required_detail_fetch_failure_is_recorded(monkeypatch):
    soup = BeautifulSoup(EXPIRAT_HTML, "html.parser")
    soup.script.decompose()

    def fetch(url, headers=None):
        if url == expirat.SCHEDULE_URL:
            return str(soup)
        raise HttpError("HTTP 403", status_code=403)

    monkeypatch.setattr("services.http._fetch_http", fetch)
    reset_fetch_failures()
    with pytest.raises(HttpError):
        expirat.scrape()
    assert len(get_fetch_failures()) == 1
