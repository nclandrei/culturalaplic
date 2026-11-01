from datetime import datetime

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


def test_fetches_detail_schema_when_listing_has_none_and_follows_pagination(monkeypatch):
    import json

    def card(path, time):
        return f'<div data-event-list="item"><a href="/{path}/?tracking=1">Concert</a><p>{time}</p></div>'

    def detail(path, date):
        return '<script type="application/ld+json">' + json.dumps({
            "@type": "Event", "name": "Concert", "url": f"{expirat.BASE_URL}/{path}/",
            "startDate": date, "location": {"name": "Expirat Halele Carol"},
        }) + '</script>'

    pages = {
        expirat.SCHEDULE_URL: card("first", "ora 21:30 acces de la 20:00") + '<a href="/?page=2">mai mult</a>',
        expirat.BASE_URL + "/?page=2": card("first", "") + card("second", "acces de la 20:00"),
        expirat.BASE_URL + "/first/": detail("first", "2026-12-31"),
        expirat.BASE_URL + "/second/": detail("second", "2027-01-02"),
    }
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        return pages[url]

    monkeypatch.setattr(expirat, "fetch_page", fetch)
    events = expirat.scrape()
    assert [event.date for event in events] == [datetime(2026, 12, 31, 21, 30), datetime(2027, 1, 2)]
    assert calls.count(expirat.BASE_URL + "/first/") == 1
    assert len(calls) == 4


def test_empty_season_stays_empty(monkeypatch):
    monkeypatch.setattr(expirat, "fetch_page", lambda *args, **kwargs: "<html></html>")
    assert expirat.scrape() == []
