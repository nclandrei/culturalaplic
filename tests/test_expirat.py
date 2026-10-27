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


def test_scrape_fetches_detail_json_ld_and_follows_pagination(monkeypatch):
    card = EXPIRAT_HTML.split('<script type="application/ld+json">')[0]
    detail_url = (
        "https://expirat.iabilet.ro/"
        "bilete-byron-o-triptic-electric-acustic-improv-128427/"
    )
    second_detail = EXPIRAT_HTML.replace("128427", "128428").replace(
        "2026-08-19", "2027-01-09"
    )
    pages = {
        expirat.SCHEDULE_URL: card + '<a href="/?page=2">mai mult</a>',
        detail_url: EXPIRAT_HTML,
        "https://expirat.iabilet.ro/?page=2": (
            card + card.replace("128427", "128428").replace("ora 21:30", "ora 22:00")
            + '<a href="/?page=2">mai mult</a>'
        ),
        detail_url.replace("128427", "128428"): second_detail,
    }
    requests = []

    def fake_fetch_page(url, **kwargs):
        assert kwargs == {"needs_js": False}
        requests.append(url)
        return pages[url]

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)

    events = expirat.scrape()

    assert len(events) == 2
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
    assert events[1].date == datetime(2027, 1, 9, 22, 0)
    assert events[0].url == detail_url
    assert events[0].price == "90 RON"
    assert requests == list(pages)


def test_scrape_continues_after_detail_fetch_failure(monkeypatch):
    card = EXPIRAT_HTML.split('<script type="application/ld+json">')[0]

    def fake_fetch_page(url, **kwargs):
        if url == expirat.SCHEDULE_URL:
            return card.replace("128427", "missing") + card
        if "missing" in url:
            raise RuntimeError("unavailable")
        return EXPIRAT_HTML

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch_page)

    events = expirat.scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
