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

    with patch.object(enescu, "fetch_page", side_effect=["", competition_html]) as fetch:
        events = enescu.scrape()

    assert fetch.call_args_list == [
        call(
            enescu.reader_url(enescu.FESTIVAL_EVENTS_URL),
            needs_js=False,
            timeout=30000,
            headers=enescu.READER_HEADERS,
        ),
        call(
            enescu.reader_url(enescu.COMPETITION_EVENTS_URL),
            needs_js=False,
            timeout=30000,
            headers=enescu.READER_HEADERS,
        ),
    ]
    assert len(events) == 1
    assert events[0].title.startswith("Concertul de deschidere")
    assert events[0].date.isoformat() == "2027-08-23T19:00:00"
    assert events[0].venue == "Ateneul Român"
    assert events[0].url == (
        "https://festivalenescu.ro/ro/concursul-international-george-enescu/"
        "evenimente/deschidere"
    )


def test_reader_url_keeps_the_official_https_source():
    assert enescu.reader_url(enescu.COMPETITION_EVENTS_URL) == (
        "https://r.jina.ai/https://festivalenescu.ro/en/"
        "george-enescu-international-competition/events?limit=100"
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
    with patch.object(enescu, "fetch_page", side_effect=["", completed_html]):
        assert enescu.scrape() == []
    assert enescu.ALLOW_EMPTY_RESULTS is True


def test_cloudflare_challenge_cannot_be_mistaken_for_empty_season():
    with patch.object(enescu, "fetch_page", side_effect=[
        "<title>Just a moment...</title>",
        "<title>Evenimente</title>",
    ]):
        with pytest.raises(ValueError, match="blocked"):
            enescu.scrape()


@pytest.mark.parametrize(("time_text", "expected_time"), [
    ("07:30 PM", "19:30:00"),
    ("10:00 AM", "10:00:00"),
    ("12:15 AM", "00:15:00"),
    ("12:15 PM", "12:15:00"),
    ("7.00 PM", "19:00:00"),
    ("19.30", "19:30:00"),
])
def test_scrape_reads_official_english_programme(time_text, expected_time):
    html = f"""
    <title>Events</title>
    <div class="item" itemprop="blogPost">
      <div class="concert-details">
        <span class="concert-day">18</span><span class="concert-month">September</span>
        <span class="concert-year">2099</span>
        <div class="concert-hour">{time_text}</div>
        <div class="concert-location">Romanian Athenaeum</div>
      </div>
      <div class="concert-preview"><h2><div>
        <a href="/en/george-enescu-international-competition/events/piano-final">
          Piano Final
        </a>
      </div></h2></div>
    </div>
    """
    with patch.object(enescu, "fetch_page", side_effect=["", html]):
        events = enescu.scrape()

    assert len(events) == 1
    assert events[0].title == "Piano Final"
    assert events[0].date.isoformat() == f"2099-09-18T{expected_time}"
    assert events[0].venue == "Romanian Athenaeum"
    assert events[0].url == (
        "https://festivalenescu.ro/en/george-enescu-international-competition/"
        "events/piano-final"
    )


def test_empty_festival_programme_is_verified_by_markup_not_title():
    html = '<div class="blog program-concerte"><div class="items-intro"></div></div>'
    with patch.object(enescu, "fetch_page", return_value=html):
        assert enescu.scrape() == []
    with patch.object(enescu, "fetch_page", return_value="<title>Evenimente</title>"):
        with pytest.raises(ValueError, match="no verifiable programme"):
            enescu.scrape()
