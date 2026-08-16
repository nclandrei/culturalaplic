import json
import re
from datetime import datetime
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://www.iabilet.ro"
BUCHAREST_URL = f"{BASE_URL}/bilete-in-bucuresti/"
MAX_PAGES = 50
MAX_PAGINATION_PASSES = 3
MIN_EXPECTED_EVENTS = 1

MUSIC_CATEGORIES = (
    "concerte-pop",
    "concerte-rock",
    "concerte-metal",
    "party",
    "concerte-muzica-clasica",
    "concerte-alternative",
    "concerte-folk",
    "festivaluri",
    "concerte-hip-hop",
    "concerte-pop-rock",
    "world-music",
    "concerte-jazz",
    "muzica-lautareasca",
    "colinde",
    "concerte-populara",
    "latino",
    "concerte",
    "concerte-electro",
    "muzica-de-petrecere",
    "blues",
    "indie",
    "k-pop",
    "manele",
)


def build_listing_url() -> str:
    """Build the iaBilet listing URL with its music taxonomy selected."""
    params = [
        ("filters[category][]", category) for category in MUSIC_CATEGORIES
    ]
    params.append(("filtersSubmitted", "1"))
    return f"{BUCHAREST_URL}?{urlencode(params)}"


EVENTS_URL = build_listing_url()

ROMANIAN_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "oct": 10, "noi": 11, "nov": 11,
    "dec": 12,
}

NON_MUSIC_TITLE_TERMS = (
    "festivalul copiilor",
    "coffee festival",
    "gaming week",
    "fashion festival",
)


def parse_date(
    day: str,
    month: str,
    year: str | None = None,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Parse Romanian date format (e.g., '17', 'ian', "'26")."""
    month_num = ROMANIAN_MONTHS.get(month.lower())
    if month_num is None:
        return None
    
    if year:
        year_num = int(year.replace("'", "").strip())
        if year_num < 100:
            year_num += 2000
    else:
        reference = now or datetime.now()
        year_num = reference.year
        test_date = datetime(year_num, month_num, int(day))
        if test_date.date() < reference.date():
            year_num += 1
    
    return datetime(year_num, month_num, int(day))


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    parts = re.split(
        r"\s*[•·|]\s*|\s+[@–]\s+|\s+-\s*|\s*-\s+|:\s+",
        title,
        maxsplit=1,
    )
    return parts[0].strip()


def is_music_event_title(title: str) -> bool:
    """Exclude clearly non-music items from iaBilet's mixed festival bucket."""
    normalized = " ".join(title.casefold().split())
    return not any(term in normalized for term in NON_MUSIC_TITLE_TERMS)


def extract_card_time(card: BeautifulSoup) -> tuple[int, int] | None:
    """Extract a start time advertised in an iaBilet card description."""
    text = card.get_text(" ", strip=True)
    matches = re.finditer(
        r"\bora\s*[:\-]?\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",
        text,
        re.IGNORECASE,
    )
    for match in matches:
        context = text[max(0, match.start() - 140):match.start()].casefold()
        if re.search(
            r"(?:bilet|presale|pre-sale).{0,120}(?:v[aâ]nzare|sale|disponibil)",
            context,
        ):
            continue
        return int(match.group(1)), int(match.group(2))
    return None


def extract_detail_time(html: str) -> tuple[int, int] | None:
    """Extract the show time (not access time) from an event detail page."""
    soup = BeautifulSoup(html, "html.parser")
    date_elem = soup.select_one(".date")
    if not date_elem:
        return None

    text = date_elem.get_text(" ", strip=True)
    match = re.search(
        r"\bora\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    context = text[max(0, match.start() - 60):match.start()].casefold()
    if re.search(r"(?:acces|access|intrare|open\s+doors?|doors?)\D{0,35}$", context):
        return None
    return int(match.group(1)), int(match.group(2))


def parse_event_card(card: BeautifulSoup) -> Event | None:
    """Parse a single event card from the HTML."""
    title_elem = card.select_one(".title a span")
    if not title_elem:
        return None
    title = " ".join(title_elem.get_text(" ", strip=True).split())
    if not is_music_event_title(title):
        return None
    
    link_elem = card.select_one(".title a")
    if not link_elem:
        return None
    url = BASE_URL + link_elem.get("href", "").split("?")[0]
    
    venue_elem = card.select_one(".location .venue span")
    venue = venue_elem.get_text(strip=True) if venue_elem else "Unknown"
    
    date_elem = card.select_one(".date-start")
    if not date_elem:
        date_elem = card.select_one(".date")
    
    if date_elem:
        day_elem = date_elem.select_one(".date-day") or date_elem.select_one("span:first-child")
        month_elem = date_elem.select_one(".date-month") or date_elem.select_one("span:nth-child(2)")
        year_elem = date_elem.select_one(".date-year")
        
        if day_elem and month_elem:
            day = day_elem.get_text(strip=True)
            month = month_elem.get_text(strip=True)
            year = year_elem.get_text(strip=True) if year_elem else None
            event_date = parse_date(day, month, year)
            if event_date is None:
                return None
            start_time = extract_card_time(card)
            if start_time:
                event_date = event_date.replace(
                    hour=start_time[0], minute=start_time[1]
                )
        else:
            return None
    else:
        return None
    
    price_elem = card.select_one(".price")
    price = None
    if price_elem:
        price_copy = BeautifulSoup(str(price_elem), "html.parser")
        for superscript in price_copy.select("sup"):
            superscript.replace_with(f".{superscript.get_text(strip=True)}")
        price_text = price_copy.get_text(" ", strip=True)
        price_text = re.sub(r"\s*\.\s*", ".", price_text)
        price_text = re.sub(r"\s*(lei|RON)\b", r" \1", price_text)
        if price_text:
            price = price_text
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue=venue,
        date=event_date,
        url=url,
        source="iabilet",
        category="music",
        price=price,
    )


def extract_json_ld_events(soup: BeautifulSoup) -> list[dict]:
    """Extract events from JSON-LD structured data."""
    events = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            text = script.string
            if not text:
                continue
            text = text.replace("/*<![CDATA[*/", "").replace("/*]]>*/", "").strip()
            data = json.loads(text)
            if data.get("@type") == "Event":
                events.append(data)
        except (json.JSONDecodeError, AttributeError):
            continue
    return events


def parse_json_ld_event(data: dict) -> Event | None:
    """Parse event from JSON-LD data."""
    try:
        title = data.get("name", "")
        title = " ".join(title.split())
        if not is_music_event_title(title):
            return None
        url = data.get("url", "")
        
        location = data.get("location", {})
        venue = location.get("name", "Unknown") if isinstance(location, dict) else "Unknown"
        
        start_date_str = data.get("startDate", "")
        if start_date_str:
            event_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            return None
        
        offers = data.get("offers", {})
        price = None
        if isinstance(offers, dict) and offers.get("price"):
            price = f"{offers['price']} {offers.get('priceCurrency', 'RON')}"
        
        artist = extract_artist_from_title(title)
        
        return Event(
            title=title,
            artist=artist,
            venue=venue,
            date=event_date,
            url=url,
            source="iabilet",
            category="music",
            price=price,
        )
    except (ValueError, KeyError):
        return None


def scrape() -> list[Event]:
    """Fetch upcoming Bucharest music events from iaBilet."""
    events: list[Event] = []
    seen_events: set[tuple[str, str]] = set()
    # iaBilet's page ordering is unstable for events with equal sort values, so
    # neighbouring pages can repeat some cards and omit others. Union a few
    # bounded traversals, stopping once a complete repeat adds nothing.
    for pass_number in range(MAX_PAGINATION_PASSES):
        count_before_pass = len(events)
        seen_pages: set[str] = set()
        url: str | None = EVENTS_URL

        for page in range(1, MAX_PAGES + 1):
            if not url or url in seen_pages:
                break
            seen_pages.add(url)

            try:
                html = fetch_page(url)
            except Exception as e:
                print(
                    f"Failed to fetch iaBilet page {page} "
                    f"on pass {pass_number + 1}: {e}"
                )
                break

            soup = BeautifulSoup(html, "html.parser")

            # Prefer cards because they can include a start time omitted by JSON-LD.
            cards = soup.select('[data-event-list="item"]')
            for card in cards:
                event = parse_event_card(card)
                key = (
                    event.url.rstrip("/"),
                    event.date.strftime("%Y-%m-%d"),
                ) if event else None
                if event and key not in seen_events:
                    seen_events.add(key)
                    events.append(event)

            json_ld_events = extract_json_ld_events(soup)
            for data in json_ld_events:
                event = parse_json_ld_event(data)
                key = (
                    event.url.rstrip("/"),
                    event.date.strftime("%Y-%m-%d"),
                ) if event else None
                if event and key not in seen_events:
                    seen_events.add(key)
                    events.append(event)

            more_btn = soup.select_one('[data-event-list="more"] a')
            if not more_btn:
                break
            next_href = more_btn.get("href")
            url = urljoin(BASE_URL, next_href) if next_href else None

        if pass_number >= 1 and len(events) == count_before_pass:
            break

    for event in events:
        if event.date.hour != 0 or event.date.minute != 0:
            continue
        try:
            detail_html = fetch_page(event.url)
        except Exception as e:
            print(f"Failed to fetch iaBilet detail {event.url}: {e}")
            continue
        start_time = extract_detail_time(detail_html)
        if start_time:
            event.date = event.date.replace(
                hour=start_time[0], minute=start_time[1]
            )
    
    return events
