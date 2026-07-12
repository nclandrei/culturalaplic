from unittest.mock import patch

from scrapers.culture.mare import scrape


def test_scrape_reads_current_exhibition_from_live_card_markup():
    html = """
    <section class="current">
      <div class="current__grid"></div>
    </section>
    <div class="past__grid is-collapsed">
      <a href="https://mare.ro/exhibition/photographs-constantin-brancusi/"
         class="current__item">
        <div class="current__item__info">
          <h4 class="h4 uppercase bold">Photographs by Constantin Brâncuși</h4>
          <span class="card-meta card-meta--period">22 mai - 27 sep 2099</span>
        </div>
      </a>
    </div>
    """

    with patch("scrapers.culture.mare.fetch_page", return_value=html):
        events = scrape()

    assert len(events) == 1
    assert events[0].title == "Photographs by Constantin Brâncuși"
    assert events[0].date.year == 2099
    assert events[0].date.month == 5
    assert events[0].url.endswith("/photographs-constantin-brancusi/")
