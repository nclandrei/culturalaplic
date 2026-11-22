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


def test_scrape_reads_cards_without_json_ld_and_preserves_new_year(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 12, 15)

    html = """
    <div data-event-list="item">
      <a href="/bilete-vama-123/?tracking=1"><h1>Vama <strong>Live</strong></h1></a>
      <div class="date-location"><p>Expirat Halele Carol, București</p>
        <p>miercuri, 20 ianuarie '27, ora 21:30 acces de la 20:00</p>
      </div>
    </div>
    <div data-event-list="item">
      <a href="/bilete-coma-124/"><h1>COMA</h1></a>
      <div class="date-location"><p>Expirat Halele Carol, București</p>
        <p>duminică, 27 decembrie acces de la 19:00</p>
      </div>
    </div>
    """
    monkeypatch.setattr(expirat, "datetime", Clock)
    monkeypatch.setattr(expirat, "fetch_page", lambda *args, **kwargs: html + html)

    events = expirat.scrape()

    assert [(event.title, event.date) for event in events] == [
        ("COMA", datetime(2026, 12, 27)),
        ("Vama Live", datetime(2027, 1, 20, 21, 30)),
    ]
    assert events[1].url == "https://expirat.iabilet.ro/bilete-vama-123/"
    assert events[1].venue == "Expirat Halele Carol"
