from datetime import datetime

from scrapers.music import expirat
from services import http


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


def test_listing_without_json_ld_reads_detail_dates_and_deduplicates(monkeypatch):
    listing = """
    <div data-event-list="item">
      <a href="/bilete-concert-123/?tracking=1"><h1>Concert</h1></a>
      <div class="date-location">joi, 21 ianuarie '27, ora 21:30 acces de la 20:00</div>
    </div>
    <div data-event-list="item"><a href="/bilete-concert-123/">Concert</a></div>
    """
    detail = """
    <script type="application/ld+json">
    {"@type":"BreadcrumbList", "name":"Not an event"}
    </script>
    <script type="application/ld+json">
    {"@type":"Event", "name":"Concert", "startDate":"2027-01-21",
     "url":"https://expirat.iabilet.ro/bilete-concert-123/"}
    </script>
    """
    requests = []

    def fake_fetch(url, **kwargs):
        requests.append((url, kwargs))
        return listing if url == expirat.SCHEDULE_URL else detail

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch)

    events = expirat.scrape()

    assert requests == [
        (expirat.SCHEDULE_URL, {"needs_js": False}),
        ("https://expirat.iabilet.ro/bilete-concert-123/", {"needs_js": False}),
    ]
    assert len(events) == 1
    assert events[0].date == datetime(2027, 1, 21, 21, 30)


def test_detail_without_advertised_show_time_preserves_iso_date(monkeypatch):
    listing = '<div data-event-list="item"><a href="/concert/">Concert</a></div>'
    detail = """
    <script type="application/ld+json">
    {"@type":"Event", "name":"Concert", "startDate":"2026-12-01",
     "url":"https://expirat.iabilet.ro/concert/"}
    </script>
    """
    monkeypatch.setattr(
        expirat, "fetch_page",
        lambda url, **kwargs: listing if url == expirat.SCHEDULE_URL else detail,
    )

    assert expirat.scrape()[0].date == datetime(2026, 12, 1)


def test_primary_detail_failure_is_still_recorded(monkeypatch):
    def fake_http(url, headers=None):
        if url == expirat.SCHEDULE_URL:
            return '<div data-event-list="item"><a href="/concert/">Concert</a></div>'
        raise http.HttpError("detail unavailable", status_code=404)

    monkeypatch.setattr(http, "_fetch_http", fake_http)
    http.reset_fetch_failures()
    try:
        assert expirat.scrape() == []
        assert len(http.get_fetch_failures()) == 1
        assert "detail unavailable" in http.get_fetch_failures()[0]
    finally:
        http.reset_fetch_failures()
