from unittest.mock import call, patch

import pytest

from scrapers.music import enescu

COMPETITION_MD = """Title: Evenimente

URL Source: https://festivalenescu.ro/ro/concursul-international-george-enescu/evenimente

# Programul evenimentelor

Sâmbătă 15 August 2026

UNMB, Foaierul Sălii George Enescu

București

## [Expoziție veche](https://festivalenescu.ro/ro/old)

Luni 23 August 2027

19.30

Ateneul Român

București

## [Concertul de deschidere <br> al Concursului](https://festivalenescu.ro/ro/concursul-international-george-enescu/evenimente/deschidere)

[Detalii](https://festivalenescu.ro/ro/concursul-international-george-enescu/evenimente/deschidere)

Marți 24 August 2027

Sala Radio

## [Masterclass](https://festivalenescu.ro/ro/masterclass)
"""


def test_scrape_includes_future_competition_events_with_time_and_venue():
    with patch.object(
        enescu, "fetch_page", side_effect=["Title: Program concerte\n", COMPETITION_MD]
    ) as fetch:
        events = enescu.scrape()

    assert fetch.call_args_list == [
        call(
            enescu.reader_url(url),
            needs_js=False,
            timeout=60000,
            headers=enescu.READER_HEADERS,
        )
        for url in enescu.EVENTS_URLS
    ]
    assert [(e.title, e.date.isoformat(), e.venue) for e in events] == [
        ("Concertul de deschidere al Concursului", "2027-08-23T19:30:00", "Ateneul Român"),
        ("Masterclass", "2027-08-24T19:00:00", "Sala Radio"),
    ]
    assert events[0].url.startswith(enescu.COMPETITION_EVENTS_URL)


def test_reader_url_keeps_the_official_https_source():
    assert enescu.reader_url(enescu.COMPETITION_EVENTS_URL) == (
        "https://markdown.new/https://festivalenescu.ro/ro/"
        "concursul-international-george-enescu/evenimente"
    )


def test_completed_competition_can_return_zero_future_events():
    completed = COMPETITION_MD.split("Luni 23 August 2027")[0]
    with patch.object(enescu, "fetch_page", side_effect=["Title: Program concerte\n", completed]):
        assert enescu.scrape() == []
    assert enescu.ALLOW_EMPTY_RESULTS is True


def test_cloudflare_challenge_cannot_be_mistaken_for_empty_season():
    with patch.object(enescu, "fetch_page", side_effect=[
        "Title: Just a moment...\n",
        "Title: Evenimente\n",
    ]):
        with pytest.raises(ValueError, match="blocked"):
            enescu.scrape()
