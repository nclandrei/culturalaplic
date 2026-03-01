import re
import unicodedata
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://improteca.ro"
EVENTS_URL = f"{BASE_URL}/calendar-evenimente/"

ROMANIAN_MONTHS = {
    "ianuarie": 1, "ian": 1,
    "februarie": 2, "feb": 2,
    "martie": 3, "mar": 3,
    "aprilie": 4, "apr": 4,
    "mai": 5,
    "iunie": 6, "iun": 6,
    "iulie": 7, "iul": 7,
    "august": 8, "aug": 8,
    "septembrie": 9, "sept": 9, "sep": 9,
    "octombrie": 10, "oct": 10,
    "noiembrie": 11, "noi": 11, "nov": 11,
    "decembrie": 12, "dec": 12,
}

ENGLISH_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

MONTH_LOOKUP = {**ROMANIAN_MONTHS, **ENGLISH_MONTHS}
MONTH_PATTERN = "|".join(sorted((re.escape(k) for k in MONTH_LOOKUP.keys()), key=len, reverse=True))


def normalize_text(text: str) -> str:
    """Normalize text for robust regex parsing (remove diacritics, lowercase)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def parse_time(text: str) -> tuple[int, int]:
    """Extract event time from text."""
    context_patterns = [
        r"(?:ora|de la ora|de la|la ora|from|at)\s*[:\-]?\s*([01]?\d|2[0-3])[:\.]([0-5]\d)",
        r"[|]\s*(?:\N{ALARM CLOCK}\s*)?([01]?\d|2[0-3])[:\.]([0-5]\d)",
        r"\(([01]?\d|2[0-3])[:\.]([0-5]\d)\s*hours?\)",
    ]
    for pattern in context_patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))

    am_pm_match = re.search(r"(?<!\d)([1-9]|1[0-2])(?::([0-5]\d))?\s*(am|pm)\b", text)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = int(am_pm_match.group(2) or "0")
        suffix = am_pm_match.group(3)
        if suffix == "pm" and hour != 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
        return hour, minute

    # Fallback: capture colon time without relying on marker words.
    matches = list(re.finditer(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", text))
    if matches:
        last = matches[-1]
        return int(last.group(1)), int(last.group(2))

    return 19, 0


def parse_date(text: str) -> datetime | None:
    """Parse date from excerpt text containing emoji markers.
    
    Formats:
    - 📅 Sambata 17 ianuarie, ora 18:00
    - 📅 Sâmbătă, 10 ianuarie 2026
    - 📆 Sâmbătă, 10 ianuarie 2026
    - 🗓 7 Martie 2026 | ⏰ 18:00
    - Sambata 14.03 ora 18:00
    - 🕗 Ora: 20:00
    """
    text_normalized = normalize_text(text)
    day: int | None = None
    month: int | None = None
    year_str: str | None = None

    numeric_match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?(?!\d)", text_normalized)
    if numeric_match:
        candidate_day = int(numeric_match.group(1))
        candidate_month = int(numeric_match.group(2))
        if 1 <= candidate_day <= 31 and 1 <= candidate_month <= 12:
            day = candidate_day
            month = candidate_month
            year_str = numeric_match.group(3)

    if day is None or month is None:
        textual_match = re.search(
            rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_PATTERN})(?:\s+(\d{{4}}))?",
            text_normalized,
        )
        if textual_match:
            day = int(textual_match.group(1))
            month = MONTH_LOOKUP.get(textual_match.group(2))
            year_str = textual_match.group(3)

    if day is None or month is None:
        reverse_match = re.search(
            rf"\b({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s*(\d{{4}}))?",
            text_normalized,
        )
        if reverse_match:
            month = MONTH_LOOKUP.get(reverse_match.group(1))
            day = int(reverse_match.group(2))
            year_str = reverse_match.group(3)

    if day is None or month is None:
        return None

    now = datetime.now()
    year = int(year_str) if year_str else now.year
    if year < 100:
        year += 2000

    hour, minute = parse_time(text_normalized)

    try:
        event_date = datetime(year, month, day, hour, minute)
        if not year_str and event_date < now.replace(hour=0, minute=0, second=0, microsecond=0):
            event_date = datetime(year + 1, month, day, hour, minute)
        return event_date
    except ValueError:
        return None


def parse_event(article: BeautifulSoup) -> Event | None:
    """Parse a single event article element."""
    title_elem = article.select_one("h2.elementor-post__title a")
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    title = re.sub(r"^[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF]+\s*", "", title)
    title = re.sub(r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF]+$", "", title)
    title = title.strip()
    
    url = title_elem.get("href", "")
    if not url.startswith("http"):
        url = BASE_URL + url
    
    excerpt_elem = article.select_one(".elementor-post__excerpt")
    if not excerpt_elem:
        return None
    
    excerpt_text = excerpt_elem.get_text(" ", strip=True)
    event_date = parse_date(excerpt_text)
    if not event_date:
        return None
    
    venue = "Improteca"
    venue_match = re.search(
        r"(?:📍|🗺️|📌|🎤)\s*(.+?)(?=(?:📅|📆|🗓|⏰|🏷️|☎️|$))",
        excerpt_text,
    )
    if venue_match:
        venue_text = venue_match.group(1).strip()
        venue_text = re.sub(r"Locație:\s*", "", venue_text, flags=re.IGNORECASE)
        venue_text = re.sub(r"Unde:\s*", "", venue_text, flags=re.IGNORECASE)
        venue_text = re.sub(r"^\s*La\s+", "", venue_text, flags=re.IGNORECASE)
        if venue_text:
            venue = venue_text.split(",")[0].strip()
    
    return Event(
        title=title,
        artist=None,
        venue=venue,
        date=event_date,
        url=url,
        source="improteca",
        category="culture",
        price=None,
    )


def scrape() -> list[Event]:
    """Fetch upcoming events from Improteca."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    page = 1
    max_pages = 1
    
    while page <= max_pages:
        url = EVENTS_URL if page == 1 else f"{EVENTS_URL}{page}/"
        
        try:
            # Listing pages are server-rendered and can be fetched over HTTP.
            html = fetch_page(url, needs_js=False, timeout=60000)
        except Exception as e:
            print(f"Failed to fetch Improteca page {page}: {e}")
            break
        
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.elementor-post")
        
        if not articles:
            break
        
        for article in articles:
            event = parse_event(article)
            if event and event.date >= today:
                key = (event.title, event.date.isoformat())
                if key not in seen:
                    seen.add(key)
                    events.append(event)
        
        pagination_anchor = soup.select_one(".e-load-more-anchor")
        if pagination_anchor:
            max_page = pagination_anchor.get("data-max-page", "1")
            try:
                max_pages = max(max_pages, int(max_page))
                if page >= max_pages:
                    break
            except ValueError:
                pass
        else:
            break
        
        page += 1
    
    events.sort(key=lambda e: e.date)
    return events
