import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://improteca.ro"
EVENTS_URL = f"{BASE_URL}/calendar-evenimente/"

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def parse_date(text: str) -> datetime | None:
    """Parse date from excerpt text containing emoji markers.
    
    Formats:
    - 📅 Sambata 17 ianuarie, ora 18:00
    - 📅 Sâmbătă, 10 ianuarie 2026
    - 📆 Sâmbătă, 10 ianuarie 2026
    - 🕗 Ora: 20:00
    """
    text_lower = text.lower()
    
    date_match = re.search(
        r"(\d{1,2})\s+(" + "|".join(ROMANIAN_MONTHS.keys()) + r")(?:\s+(\d{4}))?",
        text_lower
    )
    if not date_match:
        return None
    
    day = int(date_match.group(1))
    month_name = date_match.group(2)
    year_str = date_match.group(3)
    
    month = ROMANIAN_MONTHS.get(month_name)
    if not month:
        return None
    
    year = int(year_str) if year_str else datetime.now().year
    
    time_match = re.search(r"ora[:\s]+(\d{1,2})[:\.](\d{2})", text_lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
    else:
        hour, minute = 19, 0
    
    try:
        event_date = datetime(year, month, day, hour, minute)
        if not year_str and event_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
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
    venue_match = re.search(r"📍\s*([^📅🗺️🎬👥💎\n]+)", excerpt_text)
    if venue_match:
        venue_text = venue_match.group(1).strip()
        venue_text = re.sub(r"Locație:\s*", "", venue_text, flags=re.IGNORECASE)
        venue_text = re.sub(r"Unde:\s*", "", venue_text, flags=re.IGNORECASE)
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
    max_pages = 10
    
    while page <= max_pages:
        url = EVENTS_URL if page == 1 else f"{EVENTS_URL}{page}/"
        
        try:
            html = fetch_page(url, needs_js=True, timeout=60000)
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
        
        next_page = soup.select_one(".e-load-more-anchor")
        if next_page:
            max_page = next_page.get("data-max-page", "1")
            try:
                if page >= int(max_page):
                    break
            except ValueError:
                pass
        else:
            break
        
        page += 1
    
    events.sort(key=lambda e: e.date)
    return events
