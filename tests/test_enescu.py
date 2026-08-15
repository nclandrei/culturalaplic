from unittest.mock import call, patch

from scrapers.music import enescu


def test_scrape_includes_international_competition_events():
    competition_html = """
      <div class="item" itemprop="blogPost">
        <div class="concert-details">
          <span class="concert-day">23</span>
          <span class="concert-month">August</span>
          <span class="concert-year">2026</span>
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
        call(enescu.FESTIVAL_EVENTS_URL, needs_js=False, timeout=30000),
        call(enescu.COMPETITION_EVENTS_URL, needs_js=False, timeout=30000),
    ]
    assert len(events) == 1
    assert events[0].title.startswith("Concertul de deschidere")
    assert events[0].date.isoformat() == "2026-08-23T19:00:00"
    assert events[0].venue == "Ateneul Român"
    assert events[0].url.startswith(enescu.COMPETITION_EVENTS_URL)
