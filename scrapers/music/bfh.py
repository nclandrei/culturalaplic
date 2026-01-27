import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import Event
from services.http import fetch_page

BASE_URL = "https://bikersforhumanity.ro"
EVENTS_URL = f"{BASE_URL}/en/bikers-for-humanity-rock-fest-v-2/"

SKIP_DOMAINS = ["bikersforhumanity.ro", "instagram.com", "youtube.com", "ambilet.ro", "iabilet.ro"]


def scrape() -> list[Event]:
    """Fetch upcoming events from Bikers For Humanity Rock Fest."""
    events: list[Event] = []
    seen: set[str] = set()
    
    try:
        html = fetch_page(EVENTS_URL, needs_js=True)
    except Exception as e:
        print(f"Failed to fetch events: {e}")
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    
    year_match = re.search(r"ROCK FEST (\d{4})", html)
    year = int(year_match.group(1)) if year_match else datetime.now().year
    
    for h4 in soup.select("h4"):
        text = h4.get_text(strip=True).upper()
        
        if "IUNIE" not in text:
            continue
        
        try:
            day = int("".join(c for c in text if c.isdigit()))
            current_date = datetime(year, 6, day, 20, 0)
        except ValueError:
            continue
        
        container = h4.find_parent("div", class_="e-con")
        if not container:
            continue
        
        for link in container.select("a"):
            href = link.get("href", "")
            
            if any(domain in href.lower() for domain in SKIP_DOMAINS):
                continue
            
            if not href.startswith("http"):
                continue
            
            artist = link.get_text(strip=True)
            if not artist or len(artist) < 2:
                continue
            
            key = f"{artist}:{current_date.isoformat()}"
            if key in seen:
                continue
            seen.add(key)
            
            events.append(Event(
                title=f"{artist} @ Bikers For Humanity Rock Fest",
                artist=artist,
                venue="Bikers For Humanity Rock Fest, Brezoi",
                date=current_date,
                url=EVENTS_URL,
                source="bfh",
                category="music",
                price=None,
            ))
    
    events.sort(key=lambda e: (e.date, e.title))
    return events
