from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.culture.arcub import parse_card_events, parse_date_range


NOW = datetime(2026, 8, 16, 12, 0)


def card(title: str, date_text: str, venue: str = "ARCUB - Hanul Gabroveni"):
    return BeautifulSoup(
        f"""
        <div class="project-box">
          <a href="/eveniment/test"><h3>{title}</h3></a>
          <div class="meta"><span>{date_text}</span><span>{venue}</span></div>
        </div>
        """,
        "html.parser",
    ).select_one(".project-box")


def test_parse_date_range_keeps_an_active_cross_month_range_in_this_year():
    assert parse_date_range("3 aprilie - 30 august", now=NOW) == (
        datetime(2026, 4, 3),
        datetime(2026, 8, 30),
    )
    assert parse_date_range("15 - 16 august", now=NOW) == (
        datetime(2026, 8, 15),
        datetime(2026, 8, 16),
    )


def test_exhibition_range_expands_only_official_open_days_and_times():
    detail_html = """
    <div class="content">
      <p><strong>Luni – Marți:</strong> închis</p>
      <p><strong>Miercuri – Vineri:</strong> 13:00 – 21:00</p>
      <p><strong>Sâmbătă – Duminică:</strong> 11:00 – 21:00</p>
    </div>
    """

    events = parse_card_events(
        card("Expoziție: DRAFT", "3 aprilie - 30 august"),
        detail_html,
        now=NOW,
    )

    assert [event.date for event in events] == [
        datetime(2026, 8, 16, 11),
        datetime(2026, 8, 19, 13),
        datetime(2026, 8, 20, 13),
        datetime(2026, 8, 21, 13),
        datetime(2026, 8, 22, 11),
        datetime(2026, 8, 23, 11),
        datetime(2026, 8, 26, 13),
        datetime(2026, 8, 27, 13),
        datetime(2026, 8, 28, 13),
        datetime(2026, 8, 29, 11),
        datetime(2026, 8, 30, 11),
    ]


def test_guided_tour_title_emits_every_advertised_time():
    events = parse_card_events(
        card(
            "Tur ghidat cu Dan Perjovschi | ora 15:00 & 17:00",
            "23 august",
        ),
        "<div class='content'></div>",
        now=NOW,
    )

    assert [event.date for event in events] == [
        datetime(2026, 8, 23, 15),
        datetime(2026, 8, 23, 17),
    ]
    assert all("ora" not in event.title.casefold() for event in events)


def test_festival_program_emits_each_named_line_with_its_location():
    detail_html = """
    <div class="content">
      <h3>Duminică, 16 august</h3>
      <ul>
        <li>10:00–22:00 | Piața Revoluției – Activități sportive</li>
        <li>11:00–13:00 | zona Parcului Kretzulescu – Atelier creativ</li>
        <li>17:30–20:00 | Cercul Militar Național – Emoții în Oraș</li>
      </ul>
    </div>
    """

    events = parse_card_events(
        card(
            "Program artistic • Străzi deschise • Weekend #16",
            "15 - 16 august",
            "Calea Victoriei",
        ),
        detail_html,
        now=NOW,
    )

    assert [(event.date, event.venue) for event in events] == [
        (datetime(2026, 8, 16, 10), "Piața Revoluției"),
        (datetime(2026, 8, 16, 11), "zona Parcului Kretzulescu"),
        (datetime(2026, 8, 16, 17, 30), "Cercul Militar Național"),
    ]


def test_ticket_intervals_expand_only_through_the_arcub_range_end():
    ticket_html = """
    <h3>30.05.2026 - 20.09.2026</h3>
    <span>Intervale: 10:00, 11:00, 12:00, 13:00</span>
    """
    events = parse_card_events(
        card(
            "Expoziție | Ocolul Pământului în 50 de misiuni",
            "30 mai - 22 august",
            "Muzeul Copiilor",
        ),
        "<a href='https://bilete.hubproedus.ro/view/test.html'>Bilete</a>",
        now=NOW,
        ticket_html=ticket_html,
    )

    assert [event.date for event in events] == [
        datetime(2026, 8, day, 10) for day in range(16, 23)
    ]
