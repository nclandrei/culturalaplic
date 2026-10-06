from unittest.mock import call, patch

import pytest

from scrapers.music import enescu


EMPTY_PROGRAMME = '<div class="blog program-concerte"><div class="items-intro"></div></div>'


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

    with patch.object(enescu, "fetch_page", side_effect=[EMPTY_PROGRAMME, competition_html]) as fetch:
        events = enescu.scrape()

    assert fetch.call_args_list == [
        call(
            enescu.reader_url(enescu.FESTIVAL_EVENTS_URL),
            needs_js=False,
            timeout=30000,
            headers=enescu.READER_HEADERS,
            record_failure=False,
        ),
        call(
            enescu.reader_url(enescu.COMPETITION_EVENTS_URL),
            needs_js=False,
            timeout=30000,
            headers=enescu.READER_HEADERS,
            record_failure=False,
        ),
    ]
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
    with patch.object(enescu, "fetch_page", side_effect=[EMPTY_PROGRAMME, completed_html]):
        assert enescu.scrape() == []
    assert enescu.ALLOW_EMPTY_RESULTS is True


def test_cloudflare_challenge_cannot_be_mistaken_for_empty_season():
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Just a moment...</title>",
        "<title>Attention Required! | Cloudflare</title>",
        EMPTY_PROGRAMME,
    ]):
        with pytest.raises(ValueError, match="blocked"):
            enescu.scrape()


def test_challenge_falls_back_to_trailing_slash_programme():
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Just a moment...</title>", EMPTY_PROGRAMME, EMPTY_PROGRAMME,
    ]) as fetch:
        assert enescu.scrape() == []
    assert fetch.call_args_list[1].args == (
        enescu.reader_url(enescu.FESTIVAL_EVENTS_URL + "/"),
    )


def test_page_title_alone_does_not_prove_an_empty_programme():
    with patch.object(enescu, "fetch_page", return_value="<title>Evenimente</title>"):
        with pytest.raises(ValueError, match="unverifiable"):
            enescu.scrape()
