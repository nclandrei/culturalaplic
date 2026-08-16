from datetime import datetime
from unittest.mock import patch

from bs4 import BeautifulSoup

from scrapers.music.jazzx import parse_current_layout, scrape


def test_scrape_parses_current_program_layout():
    html = """
        <html><body><div class="entry-content">
          <div class="jazzx-program">
            <section class="jazzx-program__block">
              <header class="jazzx-program__header">
                <h2 class="jazzx-program__title">JAZZx NOW</h2>
                <p class="jazzx-program__subtitle">Iulius Town Timișoara</p>
              </header>
              <article class="jazzx-program__day">
                <h3 class="jazzx-program__date-heading">01.07.2026</h3>
                <ul class="jazzx-program__list">
                  <li>
                    <span class="jazzx-program__time">19:15</span>
                    <span class="jazzx-program__artist">Muzica Militară a Brigăzii 18 ISR</span>
                  </li>
                  <li>
                    <span class="jazzx-program__time">20:00</span>
                    <span class="jazzx-program__artist">Giga Jazz Machine 3000</span>
                  </li>
                </ul>
              </article>
            </section>
          </div>
        </div></body></html>
    """

    with patch(
        "scrapers.music.jazzx.get_program_url",
        return_value=("https://plai.ro/jazz/program-2026.html", 2026, html),
    ):
        events = scrape()

    assert [(event.artist, event.date) for event in events] == [
        ("Muzica Militară a Brigăzii 18 ISR", datetime(2026, 7, 1, 19, 15)),
        ("Giga Jazz Machine 3000", datetime(2026, 7, 1, 20, 0)),
    ]
    assert all(
        event.venue == "JAZZx NOW – Iulius Town Timișoara" for event in events
    )


def test_current_layout_uses_published_stage_range_and_rolls_nocturnal_midnight():
    html = """
        <div class="jazzx-program">
          <section class="jazzx-program__block">
            <h2 class="jazzx-program__title">JAZZx weekend</h2>
            <article class="jazzx-program__day">
              <h3 class="jazzx-program__date-heading">03.07.2026</h3>
              <div class="jazzx-program__stage">
                <h4 class="jazzx-program__stage-name">
                  <span>CREATIVE MORNINGS</span>
                  <span class="jazzx-program__stage-venue">
                    Iulius Garden ·
                    <span class="jazzx-program__stage-hours">07:30 – 09:00</span>
                  </span>
                </h4>
                <ul><li><span class="jazzx-program__artist">daoud</span></li></ul>
              </div>
              <div class="jazzx-program__stage">
                <h4 class="jazzx-program__stage-name">
                  Nocturnal Jam
                  <span class="jazzx-program__stage-venue">Reciproc</span>
                </h4>
                <ul><li>
                  <span class="jazzx-program__time">00:00</span>
                  <span class="jazzx-program__artist">Wet Enough!?</span>
                </li></ul>
              </div>
            </article>
          </section>
        </div>
    """

    events = parse_current_layout(
        BeautifulSoup(html, "html.parser"),
        "https://plai.ro/jazz/program-2026.html",
    )

    assert [(event.artist, event.date) for event in events] == [
        ("daoud", datetime(2026, 7, 3, 7, 30)),
        ("Wet Enough!?", datetime(2026, 7, 4)),
    ]
