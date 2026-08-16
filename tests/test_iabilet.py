from datetime import datetime
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from scrapers.music.iabilet import (
    MUSIC_CATEGORIES,
    build_listing_url,
    extract_artist_from_title,
    is_music_event_title,
    parse_date,
    scrape,
)


def card(title: str, href: str, day: int, description: str = "") -> str:
    return f"""
    <div data-event-list="item">
      <div class="title"><a href="{href}"><span>{title}</span></a></div>
      <div class="location"><div class="venue"><span>Control Club</span></div></div>
      <div class="date-start">
        <span class="date-day">{day}</span>
        <span class="date-month">sep</span>
        <span class="date-year">'26</span>
      </div>
      <div class="description">{description}</div>
    </div>
    """


def test_listing_url_requests_only_music_categories():
    query = parse_qs(urlparse(build_listing_url()).query)

    assert set(query["filters[category][]"]) == set(MUSIC_CATEGORIES)
    assert query["filtersSubmitted"] == ["1"]
    assert "teatru" not in query["filters[category][]"]
    assert "workshop" not in query["filters[category][]"]
    assert "festivaluri" in query["filters[category][]"]


def test_yearless_event_later_today_does_not_roll_into_next_year():
    parsed = parse_date("15", "aug", now=datetime(2026, 8, 15, 18, 0))

    assert parsed == datetime(2026, 8, 15)


def test_unknown_month_is_rejected_instead_of_defaulting_to_january():
    assert parse_date("15", "invalid", "'26") is None


def test_bullet_title_extracts_artist_for_cross_source_deduplication():
    assert (
        extract_artist_from_title("byron • Triptic: Electric / Acustic / Improv")
        == "byron"
    )
    assert extract_artist_from_title("Pinholes• Concert") == "Pinholes"
    assert extract_artist_from_title("Faust x Live Band- Concert") == "Faust x Live Band"


def test_obvious_non_music_festivals_are_filtered():
    assert not is_music_event_title("Festivalul Copiilor")
    assert not is_music_event_title("Slow Coffee Festival – Ediția #10")
    assert not is_music_event_title("Bucharest Gaming Week 2026")
    assert not is_music_event_title("Pasarela International Fashion Festival")
    assert is_music_event_title("BalKaniK! Festival | Ediția a XIII-a")


def test_scrape_keeps_times_advertised_in_card_descriptions():
    html = card(
        "Concert Tribut ABBA",
        "/music/abba-matinee",
        24,
        "Concertul începe de la ora 17:00.",
    ) + card(
        "Concert Tribut ABBA",
        "/music/abba-evening",
        24,
        "A doua reprezentație începe la ora 19:30.",
    )

    with patch("scrapers.music.iabilet.fetch_page", return_value=html):
        events = scrape()

    assert [event.date for event in events] == [
        datetime(2026, 9, 24, 17, 0),
        datetime(2026, 9, 24, 19, 30),
    ]


def test_ticket_sale_time_is_not_used_as_show_time():
    html = card(
        "The Rumjacks la Hard Rock Cafe",
        "/music/rumjacks",
        7,
        "Biletele se pun în vânzare pe 8 mai la ora 10:00.",
    )

    with patch("scrapers.music.iabilet.fetch_page", return_value=html):
        events = scrape()

    assert events[0].date == datetime(2026, 9, 7)


def test_scrape_enriches_a_date_only_card_from_its_detail_page():
    listing_html = card(
        "Directia 5 - Dubla aniversare",
        "/bilete-directia-5-127180/",
        24,
    )
    detail_html = """
    <div class="date">
      joi, 24 septembrie, ora 20:00 acces de la 19:00
    </div>
    """

    def fetch(url: str) -> str:
        if url.endswith("/bilete-directia-5-127180/"):
            return detail_html
        return listing_html

    with patch("scrapers.music.iabilet.fetch_page", side_effect=fetch):
        events = scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 9, 24, 20, 0)


def test_november_card_and_json_ld_are_one_occurrence():
    html = card(
        "Pink Floyd History",
        "/music/pink-floyd-history",
        1,
    ).replace(">sep<", ">nov<") + """
    <script type="application/ld+json">
    {
      "@type": "Event",
      "name": "Pink Floyd History",
      "url": "https://www.iabilet.ro/music/pink-floyd-history",
      "startDate": "2026-11-01",
      "location": {"name": "Sala Palatului"}
    }
    </script>
    """

    with patch("scrapers.music.iabilet.fetch_page", return_value=html):
        events = scrape()

    assert len(events) == 1
    assert events[0].date == datetime(2026, 11, 1)


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
        side_effect=lambda url: page_two if "page=2" in url else page_one,
    ) as fetch:
        events = scrape()

    assert [event.title for event in events] == ["First concert", "Second concert"]
    assert all(event.category == "music" for event in events)
    assert "filtersSubmitted=1" in fetch.call_args_list[1].args[0]
    assert "page=2" in fetch.call_args_list[1].args[0]


def test_scrape_unions_events_across_unstable_pagination_passes():
    page_one = (
        card("First concert", "/music/first", 10)
        + """
        <div data-event-list="more">
          <a href="/bilete-in-bucuresti?filtersSubmitted=1&amp;page=2">
            mai mult
          </a>
        </div>
        """
    )
    page_two_calls = 0

    def fetch(url: str) -> str:
        nonlocal page_two_calls
        if "page=2" not in url:
            return page_one
        page_two_calls += 1
        result = card("Second concert", "/music/second", 11)
        if page_two_calls >= 2:
            result += card("Boundary concert", "/music/boundary", 12)
        return result

    with patch("scrapers.music.iabilet.fetch_page", side_effect=fetch) as mocked_fetch:
        events = scrape()

    assert [event.title for event in events] == [
        "First concert",
        "Second concert",
        "Boundary concert",
    ]
    assert page_two_calls == 3
    listing_calls = [
        call for call in mocked_fetch.call_args_list
        if "filtersSubmitted=1" in call.args[0]
    ]
    assert len(listing_calls) == 6
