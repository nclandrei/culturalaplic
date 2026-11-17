from unittest.mock import call, patch

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
        competition_html.replace("2027", "2020"), competition_html,
    ]) as fetch:
        events = enescu.scrape()

    assert fetch.call_args_list == [
        call(
            enescu.FESTIVAL_EVENTS_URL,
            needs_js=False,
            record_failure=False,
        ),
        call(
            enescu.COMPETITION_EVENTS_URL,
            needs_js=False,
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


@pytest.mark.parametrize("use_reader", [False, True])
def test_completed_competition_can_return_zero_future_events(use_reader):
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
    responses = [RuntimeError("403"), completed_html] if use_reader else [completed_html]
    with patch.object(enescu, "fetch_page", side_effect=responses * 2):
        assert enescu.scrape() == []
    assert enescu.ALLOW_EMPTY_RESULTS is True


def test_cloudflare_challenge_cannot_be_mistaken_for_empty_season():
    with patch.object(enescu, "fetch_page", return_value="<title>Just a moment...</title>"):
        with pytest.raises(ValueError, match="blocked"):
            enescu.scrape()


def test_one_invalid_listing_cannot_be_hidden_by_another_listing():
    with patch.object(enescu, "fetch_programme", side_effect=[
        ValueError("missing programme"),
        enescu.BeautifulSoup("", "html.parser"),
    ]):
        with pytest.raises(ValueError, match="missing programme"):
            enescu.scrape()


def test_reader_fallback_rejects_unverifiable_empty_programme():
    with patch.object(enescu, "fetch_page", side_effect=[
        RuntimeError("403"), "<title>Evenimente</title>",
    ]) as fetch:
        with pytest.raises(ValueError, match="no verifiable programme"):
            enescu.fetch_programme(enescu.COMPETITION_EVENTS_URL)
    assert fetch.call_args == call(
        enescu.reader_url(enescu.COMPETITION_EVENTS_URL),
        needs_js=False, timeout=30000, headers=enescu.READER_HEADERS,
    )
