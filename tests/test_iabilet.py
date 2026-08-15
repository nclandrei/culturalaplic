from datetime import datetime
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from scrapers.music.iabilet import (
    MUSIC_CATEGORIES,
    build_listing_url,
    parse_date,
    scrape,
)


def card(title: str, href: str, day: int) -> str:
    return f"""
    <div data-event-list="item">
      <div class="title"><a href="{href}"><span>{title}</span></a></div>
      <div class="location"><div class="venue"><span>Control Club</span></div></div>
      <div class="date-start">
        <span class="date-day">{day}</span>
        <span class="date-month">sep</span>
        <span class="date-year">'26</span>
      </div>
    </div>
    """


def test_listing_url_requests_only_music_categories():
    query = parse_qs(urlparse(build_listing_url()).query)

    assert set(query["filters[category][]"]) == set(MUSIC_CATEGORIES)
    assert query["filtersSubmitted"] == ["1"]
    assert "teatru" not in query["filters[category][]"]
    assert "workshop" not in query["filters[category][]"]


def test_yearless_event_later_today_does_not_roll_into_next_year():
    parsed = parse_date("15", "aug", now=datetime(2026, 8, 15, 18, 0))

    assert parsed == datetime(2026, 8, 15)


def test_scrape_follows_filtered_next_page_link():
    page_one = (
        card("First concert", "/music/first", 10)
        + """
        <div data-event-list="more">
          <a href="/bilete-in-bucuresti?filters%5Bcategory%5D%5B0%5D=concerte-rock&amp;filtersSubmitted=1&amp;page=2">
            mai mult
          </a>
        </div>
        """
    )
    page_two = card("Second concert", "/music/second", 11)

    with patch(
        "scrapers.music.iabilet.fetch_page",
        side_effect=[page_one, page_two],
    ) as fetch:
        events = scrape()

    assert [event.title for event in events] == ["First concert", "Second concert"]
    assert all(event.category == "music" for event in events)
    assert "filtersSubmitted=1" in fetch.call_args_list[1].args[0]
    assert "page=2" in fetch.call_args_list[1].args[0]
