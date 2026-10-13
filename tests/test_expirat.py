import json
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


def test_scrape_follows_cards_and_pagination_without_listing_json(monkeypatch):
    def card(path, time):
        return f'<div data-event-list="item"><a href="/{path}/?tracking=1">Show</a>{time}</div>'

    def detail(path, date):
        record = {
            "@type": "Event", "name": path,
            "url": f"https://expirat.iabilet.ro/{path}/", "startDate": date,
            "location": {"name": "Expirat Halele Carol"},
        }
        return f'<script type="application/ld+json">{json.dumps(record)}</script>'

    pages = {
        expirat.SCHEDULE_URL: card("first", "ora 21:30 acces de la 20:00")
        + '<div data-event-list="more"><a href="/?page=2">mai mult</a></div>',
        expirat.SCHEDULE_URL + "?page=2": card("first", "") + card("second", ""),
        expirat.SCHEDULE_URL + "first/": detail("first", "2026-12-31"),
        expirat.SCHEDULE_URL + "second/": detail("second", "2027-01-03T19:45:00+02:00"),
    }
    monkeypatch.setattr(expirat, "fetch_page", lambda url, **kwargs: pages[url])

    events = expirat.scrape()

    assert [(event.title, event.date) for event in events] == [
        ("first", datetime(2026, 12, 31, 21, 30)),
        ("second", datetime(2027, 1, 3, 19, 45)),
    ]

    pages[expirat.SCHEDULE_URL + "second/"] = '<title>Just a moment...</title>'
    with pytest.raises(ValueError, match="missing structured data"):
        expirat.scrape()
