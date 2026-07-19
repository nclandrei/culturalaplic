from unittest.mock import patch

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
