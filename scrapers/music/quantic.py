import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page_with_reader_fallback

BASE_URL = "https://quantic.pub"
EVENTS_URL = f"{BASE_URL}/evenimente/"


def get_month_url(year: int, month: int) -> str:
    """Get the URL for a specific month's calendar."""
    return f"{BASE_URL}/evenimente/month/{year}-{month:02d}/"


def extract_artist_from_title(title: str) -> str | None:
    """Extract artist name from event title."""
    separators = [" – ", " - ", " | ", " @ ", ": "]
    for sep in separators:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def parse_datetime(time_elem: BeautifulSoup) -> datetime | None:
    """Parse datetime from the time element in tooltip."""
    if not time_elem:
        return None
    
    datetime_attr = time_elem.get("datetime")
    if datetime_attr:
        try:
            return datetime.strptime(datetime_attr, "%Y-%m-%d")
        except ValueError:
            pass
    
    return None


def parse_event(event_article: BeautifulSoup, soup: BeautifulSoup) -> Event | None:
    """Parse a single event from the calendar."""
    link = event_article.select_one("a.tribe-events-calendar-month__calendar-event-title-link")
    if not link:
        return None
    
    title = link.get_text(strip=True)
    url = link.get("href", "")
    
    tooltip_selector = event_article.select_one("[data-tooltip-content]")
    if not tooltip_selector:
        return None
    
    tooltip_id = tooltip_selector.get("data-tooltip-content")
    if not tooltip_id:
        return None
    
    tooltip = soup.select_one(tooltip_id)
    if not tooltip:
        return None
    
    time_elem = tooltip.select_one("time[datetime]")
    event_date = parse_datetime(time_elem)
    if not event_date:
        return None
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue="Quantic",
        date=event_date,
        url=url,
        source="quantic",
        category="music",
        price=None,
    )


def parse_multiday_event(event_article: BeautifulSoup, soup: BeautifulSoup) -> Event | None:
    """Parse a multiday event from the calendar."""
    link = event_article.select_one("a[data-js='tribe-events-tooltip']")
    if not link:
        return None
    
    title_elem = event_article.select_one(".tribe-events-calendar-month__multiday-event-bar-title")
    if not title_elem:
        title_elem = event_article.select_one(".tribe-events-calendar-month__multiday-event-hidden-title")
    
    if not title_elem:
        return None
    
    title = title_elem.get_text(strip=True)
    url = link.get("href", "")
    
    tooltip_id = link.get("data-tooltip-content")
    if not tooltip_id:
        return None
    
    tooltip = soup.select_one(tooltip_id)
    if not tooltip:
        return None
    
    time_elem = tooltip.select_one("time[datetime]")
    event_date = parse_datetime(time_elem)
    if not event_date:
        return None
    
    artist = extract_artist_from_title(title)
    
    return Event(
        title=title,
        artist=artist,
        venue="Quantic",
        date=event_date,
        url=url,
        source="quantic",
        category="music",
        price=None,
    )


def scrape_month(year: int, month: int) -> list[Event]:
    """Scrape events for a specific month."""
    events: list[Event] = []
    
    url = get_month_url(year, month)
    try:
        html = fetch_page_with_reader_fallback(
            url,
            expected_text="tribe-events-calendar-month__calendar-event",
        )
    except Exception as e:
        print(f"Failed to fetch Quantic {year}-{month:02d}: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    for event_article in soup.select("article.tribe-events-calendar-month__calendar-event"):
        event = parse_event(event_article, soup)
        if event:
            events.append(event)
    
    for event_article in soup.select("article.tribe-events-calendar-month__multiday-event"):
        if "tribe-events-calendar-month__multiday-event--start" not in event_article.get("class", []):
            continue
        event = parse_multiday_event(event_article, soup)
        if event:
            events.append(event)
    
    return events


def scrape() -> list[Event]:
    """Fetch upcoming events from Quantic for current and next month."""
    events: list[Event] = []
    seen_urls: set[str] = set()
    
    now = datetime.now()
    current_month = now.replace(day=1)
    next_month = current_month + relativedelta(months=1)
    
    for date in [current_month, next_month]:
        month_events = scrape_month(date.year, date.month)
        for event in month_events:
            if event.url not in seen_urls:
                seen_urls.add(event.url)
                events.append(event)
    
    events.sort(key=lambda e: e.date)
    
    return events
