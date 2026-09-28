from datetime import datetime
from unittest.mock import patch

from scrapers.theatre import teatrulmic


def test_calendar_keeps_repeated_production_dates_and_september_abbreviation(monkeypatch):
    html = """
    <div class="cal"><div class="left"><span class="date">miercuri 30 sept.</span><span class="time">19:00</span></div>
      <div class="right"><div class="title"><a href="/spectacol/ex/">EX</a></div><div class="sala">Sala Studio</div></div></div>
    <div class="cal"><div class="left"><span class="date">joi 01 oct.</span><span class="time">19:00</span></div>
      <div class="right"><div class="title"><a href="/spectacol/ex/">EX</a></div><div class="sala">Sala Studio</div></div></div>
    <div class="cal"><div class="left"><span class="date">joi 01 oct.</span><span class="time">19:00</span></div>
      <div class="right"><div class="title"><a href="/spectacol/delta/">DELTA</a></div><div class="sala">Sala Atelier</div></div></div>
    <div class="cal"><div class="left"><span class="date">vineri 06 nov.</span><span class="time">19:00</span></div>
      <div class="right"><div class="title"><a href="/spectacol/ex/">EX</a></div><div class="sala">Sala Studio</div></div></div>
    """
    monkeypatch.setattr(teatrulmic, "fetch_page", lambda *args, **kwargs: html)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 27)

    with patch.object(teatrulmic, "datetime", FixedDatetime):
        events = teatrulmic.scrape()

    assert [(e.title, e.date, e.venue) for e in events] == [
        ("EX", datetime(2026, 9, 30, 19), "Teatrul Mic - Sala Studio"),
        ("EX", datetime(2026, 10, 1, 19), "Teatrul Mic - Sala Studio"),
        ("DELTA", datetime(2026, 10, 1, 19), "Teatrul Mic - Sala Atelier"),
        ("EX", datetime(2026, 11, 6, 19), "Teatrul Mic - Sala Studio"),
    ]
