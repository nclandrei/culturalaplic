from datetime import datetime

import pytest

from scrapers.music import expirat


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


@pytest.mark.parametrize("listing_has_json_ld", [True, False])
def test_scrape_uses_official_iabilet_feed(monkeypatch, listing_has_json_ld):
    requests = []

    def fake_fetch_page(url, **kwargs):
        requests.append((url, kwargs))
        if url == expirat.SCHEDULE_URL and not listing_has_json_ld:
            return EXPIRAT_HTML.split('<script type="application/ld+json">')[0]
        return EXPIRAT_HTML

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)

    events = expirat.scrape()

    expected_requests = [
        ("https://expirat.iabilet.ro/", {"needs_js": False}),
    ]
    if not listing_has_json_ld:
        expected_requests.append((
            "https://expirat.iabilet.ro/bilete-byron-o-triptic-electric-acustic-improv-128427",
            {"needs_js": False},
        ))
    assert requests == expected_requests
    assert len(events) == 1
    assert events[0].title == "byron • Triptic: Electric / Acustic / Improv"
    assert events[0].artist == "byron"
    assert events[0].venue == "Expirat Halele Carol"
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
    assert events[0].price == "90 RON"
    assert events[0].source == "expirat"


def test_expirat_zero_results_are_monitored():
    assert expirat.MIN_EXPECTED_EVENTS == 1
