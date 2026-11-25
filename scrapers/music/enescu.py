import re
from datetime import datetime

from models import Event
from services.http import fetch_page

BASE_URL = "https://festivalenescu.ro"
FESTIVAL_EVENTS_URL = f"{BASE_URL}/ro/festivalul-george-enescu/concerte"
COMPETITION_EVENTS_URL = (
    f"{BASE_URL}/ro/concursul-international-george-enescu/evenimente"
)
EVENTS_URL = COMPETITION_EVENTS_URL
EVENTS_URLS = (FESTIVAL_EVENTS_URL, COMPETITION_EVENTS_URL)
ALLOW_EMPTY_RESULTS = True  # An accessible, completed festival has no future shows.
# Cloudflare blocks CI runners and r.jina.ai; Cloudflare's own Markdown
# renderer still returns the official page.
READER_BASE_URL = "https://markdown.new/"
READER_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; culturalaplic/1.0)"}

ROMANIAN_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}
DATE_LINE = re.compile(r"^[^\W\d_]+\s+(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})$")
TIME_LINE = re.compile(r"^(\d{1,2})[.:](\d{2})$")
TITLE_LINE = re.compile(r"^##\s+\[(.+?)\]\((\S+?)\)")


def reader_url(url: str) -> str:
    """Route the official page through a CI-accessible Markdown reader."""
    return f"{READER_BASE_URL}{url}"


def parse_events(markdown: str) -> list[Event]:
    """Parse the programme blocks: date, time, venue, city, ..., ## [title](url)."""
    events: list[Event] = []
    event_date: datetime | None = None
    details: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        date_match = DATE_LINE.match(line)
        month = ROMANIAN_MONTHS.get(date_match.group(2).lower()) if date_match else None
        if date_match and month:
            try:
                event_date = datetime(
                    int(date_match.group(3)), month, int(date_match.group(1)), 19, 0
                )
            except ValueError:
                event_date = None
            details = []
            continue
        if event_date is None:
            continue
        time_match = TIME_LINE.match(line)
        if time_match and not details:
            event_date = event_date.replace(
                hour=int(time_match.group(1)), minute=int(time_match.group(2))
            )
            continue
        title_match = TITLE_LINE.match(line)
        if title_match:
            title = re.sub(r"<[^>]+>", " ", title_match.group(1))
            title = " ".join(title.replace("*", "").split())
            if title:
                events.append(Event(
                    title=title,
                    artist=None,
                    venue=details[0] if details else "Festivalul George Enescu",
                    date=event_date,
                    url=title_match.group(2),
                    source="Festivalul Enescu",
                    category="music",
                    price=None,
                ))
            event_date = None
            continue
        details.append(line)
    return events


def scrape() -> list[Event]:
    """Fetch Festival and International Competition events."""
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    valid_listings = 0
    blocked_listings: list[str] = []
    today = datetime.now().date()

    for events_url in EVENTS_URLS:
        try:
            markdown = fetch_page(
                reader_url(events_url),
                needs_js=False,
                timeout=60000,
                headers=READER_HEADERS,
            )
        except Exception as e:
            print(f"Failed to fetch Festivalul Enescu events from {events_url}: {e}")
            continue

        title_match = re.search(r"^Title:\s*(.*)$", markdown, re.MULTILINE)
        title = title_match.group(1).casefold() if title_match else ""
        if (
            "just a moment" in markdown.casefold()
            or "attention required" in markdown.casefold()
            or not title
        ):
            blocked_listings.append(events_url)
            continue

        listing_events = parse_events(markdown)
        if listing_events or "program" in title or "evenimente" in title:
            valid_listings += 1
        for event in listing_events:
            if event.date.date() >= today:
                key = (event.title, event.date.isoformat())
                if key not in seen:
                    seen.add(key)
                    events.append(event)

    if blocked_listings:
        raise ValueError(f"Festivalul Enescu programme blocked: {', '.join(blocked_listings)}")
    if not valid_listings:
        raise ValueError("Festivalul Enescu returned no verifiable programme markup")
    events.sort(key=lambda e: e.date)
    return events
