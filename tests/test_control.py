from unittest.mock import patch

from scrapers.music import control


def test_scrape_waits_for_events_list_before_parsing():
    html = "<div class='events-list-view'></div>"

    with patch("scrapers.music.control.fetch_page", return_value=html) as fetch:
        control.scrape()

    fetch.assert_called_once_with(
        control.EVENTS_URL,
        needs_js=True,
        wait_selector=".events-list-view",
    )
