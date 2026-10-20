from datetime import datetime
from unittest.mock import patch

import pytest

from scrapers.theatre import cuibul


def test_scrape_reads_event_from_current_program_markup():
    html = """
    <div class="mb-8">
      <div>
        <div class="mx-6 flex items-center gap-3">
          <span>Marti</span><span>14 Iulie</span>
        </div>
      </div>
      <div>
        <div class="group relative z-10 mb-16">
          <h2><a href="/spectacol/ataraxia">ATARAXIA</a></h2>
          <span>Cuibul Artiștilor - Facultatea de Inginerie a Instalațiilor, București</span>
          <button data-testid="time-slot-3214">
            <span>schedule</span><span>19:30</span>
          </button>
        </div>
      </div>
    </div>
    """

    with patch("scrapers.theatre.cuibul.fetch_page", return_value=html) as fetch:
        events = cuibul.scrape()

    fetch.assert_called_once_with(
        cuibul.EVENTS_URL,
        needs_js=True,
        timeout=60000,
    )
    assert len(events) == 1
    assert events[0].title == "ATARAXIA"
    assert events[0].date.month == 7
    assert events[0].date.day == 14
    assert events[0].date.hour == 19
    assert events[0].date.minute == 30
    assert events[0].url == f"{cuibul.BASE_URL}/spectacol/ataraxia"


def test_scrape_keeps_every_performance_time_in_a_program_card():
    html = """
    <div class="mb-8">
      <div class="mx-6"><span>Duminica</span><span>16 August</span></div>
      <div class="group relative z-10 mb-16">
        <h2><a href="/spectacol/em">-EM</a></h2>
        <span>Cuibul Artiștilor - București</span>
        <button data-testid="time-slot-3233"><span>schedule</span><span>19:00</span></button>
        <button data-testid="time-slot-3234"><span>schedule</span><span>21:00</span></button>
      </div>
    </div>
    """

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 8, 15)

    with patch("scrapers.theatre.cuibul.fetch_page", return_value=html), \
         patch("scrapers.theatre.cuibul.datetime", FixedDatetime):
        events = cuibul.scrape()

    assert [event.date.strftime("%Y-%m-%d %H:%M") for event in events] == [
        "2026-08-16 19:00",
        "2026-08-16 21:00",
    ]


def test_scrape_accepts_explicitly_empty_calendar():
    html = "<main><h1>Calendar Spectacole</h1><p>Niciun spectacol programat.</p></main>"
    with patch.object(cuibul, "fetch_page", return_value=html):
        assert cuibul.scrape() == []
    assert cuibul.ALLOW_EMPTY_RESULTS is True


@pytest.mark.parametrize("html", [
    "<main><h1>Calendar Spectacole</h1></main>",
    "<title>Attention Required! | Cloudflare</title>",
])
def test_scrape_rejects_empty_output_without_empty_calendar_message(html):
    with patch.object(cuibul, "fetch_page", return_value=html):
        with pytest.raises(ValueError, match="no verifiable programme markup"):
            cuibul.scrape()
