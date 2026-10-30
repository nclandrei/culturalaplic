from unittest.mock import patch

import pytest

from scrapers.music import enescu


def test_scrape_includes_international_competition_events():
    competition_html = """
      <div class="item" itemprop="blogPost">
        <div class="concert-details">
          <span class="concert-day">23</span>
          <span class="concert-month">August</span>
          <span class="concert-year">2027</span>
          <div class="concert-hour">19:00</div>
          <div class="concert-location">Ateneul Român</div>
        </div>
        <div class="concert-preview">
          <h2>
            <a href="/ro/concursul-international-george-enescu/evenimente/deschidere">
              Concertul de deschidere al Concursului Internațional George Enescu
            </a>
          </h2>
        </div>
      </div>
    """

    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Program concerte</title>", competition_html,
    ]):
        events = enescu.scrape()

    assert len(events) == 1
    assert events[0].title.startswith("Concertul de deschidere")
    assert events[0].date.isoformat() == "2027-08-23T19:00:00"
    assert events[0].venue == "Ateneul Român"
    assert events[0].url.startswith(enescu.COMPETITION_EVENTS_URL)


def test_reader_url_keeps_the_official_https_source():
    assert enescu.reader_url(enescu.COMPETITION_EVENTS_URL) == (
        "https://r.jina.ai/https://festivalenescu.ro/ro/"
        "concursul-international-george-enescu/evenimente"
    )


def test_completed_competition_can_return_zero_future_events():
    completed_html = """
    <title>Evenimente</title>
    <div class="item" itemprop="blogPost">
      <div class="concert-details">
        <span class="concert-day">19</span><span class="concert-month">Septembrie</span>
        <span class="concert-year">2026</span>
      </div>
      <div class="concert-preview"><h2><a href="/ro/old-concert">Finală</a></h2></div>
    </div>
    """
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Program concerte</title>", completed_html,
    ]):
        assert enescu.scrape() == []
    assert enescu.ALLOW_EMPTY_RESULTS is True


def test_cloudflare_challenge_cannot_be_mistaken_for_empty_season():
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Just a moment...</title>",
        "Title: Just a moment...\nMarkdown Content:\nVerify you are human",
        "<title>Evenimente</title>",
    ]):
        with pytest.raises(ValueError, match="blocked"):
            enescu.scrape()


def test_scrape_recovers_blocked_html_using_full_markdown():
    completed_festival = """
# Program oficial - Festivalul Internațional George Enescu
Concertele din această categorie s-au încheiat.
"""
    competition = f"""
Title: Evenimente
Markdown Content:
# Concursul Internațional George Enescu
Duminică 23 August 2027

 19:30

 Ateneul Român

București

## [Concert de deschidere]({enescu.COMPETITION_EVENTS_URL}/deschidere)

Luni 24 August 2027

 10.15

 Sala Radio

București

Intrare liberă

## [Masterclass]({enescu.COMPETITION_EVENTS_URL}/masterclass)

Sâmbătă 19 Septembrie 2020

18:00

Ateneul Român

## [Finală veche]({enescu.COMPETITION_EVENTS_URL}/finala)
"""
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Attention Required! | Cloudflare</title>", completed_festival,
        "<title>Just a moment...</title>", competition,
    ]):
        events = enescu.scrape()

    assert [(e.title, e.date.isoformat(), e.venue, e.url) for e in events] == [
        ("Concert de deschidere", "2027-08-23T19:30:00", "Ateneul Român",
         f"{enescu.COMPETITION_EVENTS_URL}/deschidere"),
        ("Masterclass", "2027-08-24T10:15:00", "Sala Radio",
         f"{enescu.COMPETITION_EVENTS_URL}/masterclass"),
    ]
