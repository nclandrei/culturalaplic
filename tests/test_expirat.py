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


def test_listing_without_json_ld_fetches_explicit_dates_from_detail_pages(monkeypatch):
    card_html, script_html = EXPIRAT_HTML.split('<script type="application/ld+json">')
    requests = []

    def fake_fetch(url, **kwargs):
        requests.append(url)
        if url == expirat.SCHEDULE_URL:
            return card_html + card_html  # Duplicate cards must fetch only once.
        return '<script type="application/ld+json">' + script_html

    monkeypatch.setattr(expirat, "fetch_page", fake_fetch)
    events = expirat.scrape()
    assert requests == [
        expirat.SCHEDULE_URL,
        "https://expirat.iabilet.ro/bilete-byron-o-triptic-electric-acustic-improv-128427/",
    ]
    assert len(events) == 1
    assert events[0].date == datetime(2026, 8, 19, 21, 30)
    assert events[0].price == "90 RON"


def test_detail_without_matching_event_is_a_failure_not_an_empty_schedule(monkeypatch):
    card_html = EXPIRAT_HTML.split("<script")[0]
    monkeypatch.setattr(
        expirat, "fetch_page",
        lambda url, **kwargs: card_html if url == expirat.SCHEDULE_URL else "<title>Blocked</title>",
    )
    with pytest.raises(ValueError, match="missing Event JSON-LD"):
        expirat.scrape()


def test_partial_listing_json_ld_still_fetches_uncovered_cards(monkeypatch):
    second_card = '''<div data-event-list="item">
        <a href="/bilete-other-123/">Other concert</a>
        <div>vineri, 1 ianuarie, ora 22:00 acces de la 20:00</div>
    </div>'''
    second_record = '''<script type="application/ld+json">{
        "@type": "Event", "name": "Other concert",
        "url": "https://expirat.iabilet.ro/bilete-other-123/",
        "startDate": "2027-01-01"
    }</script>'''
    monkeypatch.setattr(
        expirat, "fetch_page",
        lambda url, **kwargs: EXPIRAT_HTML + second_card if url == expirat.SCHEDULE_URL else second_record,
    )
    events = expirat.scrape()
    assert len(events) == 2
    assert events[1].date == datetime(2027, 1, 1, 22)


def test_access_time_is_not_mistaken_for_start_time():
    from bs4 import BeautifulSoup

    html = EXPIRAT_HTML.split("<script")[0].replace(
        ", ora 21:30 acces de la 20:00", " acces de la 20:00",
    )
    assert expirat.extract_card_times(BeautifulSoup(html, "html.parser")) == {}


def test_malformed_event_record_is_not_silently_dropped(monkeypatch):
    monkeypatch.setattr(
        expirat, "fetch_page",
        lambda url, **kwargs: EXPIRAT_HTML.replace("2026-08-19", "invalid-date"),
    )
    with pytest.raises(ValueError, match="invalid Event JSON-LD"):
        expirat.scrape()
