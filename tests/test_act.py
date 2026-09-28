from datetime import datetime

from scrapers.theatre.act import parse_events


def _row(title: str, date: str, time: str = "19:30", extra: str = "") -> str:
    return f'''<li class="event_list"><div class="movie_title"><a href="/movies/test/">{title}</a></div>
      <span class="movies_list_date">{date}</span><span class="movie_time">{time}</span>
      <div class="info event_country">de Autor</div><div class="info event_box_office">Cat. I - 100 lei</div>{extra}</li>'''


def test_parses_official_act_fields_and_keeps_same_title_multiple_dates():
    html = _row("DON QUIJOTE", "28 septembrie 2026") + _row(
        "DON QUIJOTE", "2 octombrie 2026", "20:00"
    )
    events = parse_events(html, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("DON QUIJOTE", datetime(2026, 9, 28, 19, 30)),
        ("DON QUIJOTE", datetime(2026, 10, 2, 20, 0)),
    ]
    assert events[0].artist == "de Autor"
    assert events[0].venue == "Teatrul ACT"
    assert events[0].price == "Cat. I - 100 lei"
    assert events[0].url == "https://www.teatrulact.ro/movies/test/"


def test_explicit_year_prevents_false_rollover_and_bad_or_cancelled_rows_are_skipped():
    valid = _row("O SCRISOARE PIERDUTĂ", "30 septembrie 2026")
    html = (
        _row("Past", "31 decembrie 2025")
        + _row("Bad date", "31 făurar 2026")
        + _row("Bad time", "1 octombrie 2026", "seara")
        + _row("Cancelled", "1 octombrie 2026", extra="<b>Spectacol anulat</b>")
        + valid + valid
    )
    events = parse_events(html, datetime(2026, 9, 27))
    assert [(event.title, event.date) for event in events] == [
        ("O SCRISOARE PIERDUTĂ", datetime(2026, 9, 30, 19, 30))
    ]
