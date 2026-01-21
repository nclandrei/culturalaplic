"""Enrichment service for theatre/culture events.

Fetches descriptions, images, and videos from event detail pages.
Falls back to Gemini AI for generating descriptions when none found.
"""

import json
import os
import re
from dataclasses import replace

from bs4 import BeautifulSoup
from google import genai

from models import Event
from services.http import fetch_page, HttpError


def extract_bulandra(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Bulandra event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: gallery carousel links with wp-content/uploads
    gallery_links = soup.select("a[href*='wp-content/uploads']")
    for link in gallery_links:
        href = link.get("href", "")
        if href and any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            result["image_url"] = href
            break
    
    # Fallback to og:image
    if not result["image_url"]:
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            result["image_url"] = og_image["content"]
    
    # Video: YouTube links (not iframes - Bulandra uses direct links)
    video_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
    if video_link:
        href = video_link.get("href", "")
        # Convert watch URL to embed format
        if "youtube.com/watch" in href:
            video_id = re.search(r'v=([^&]+)', href)
            if video_id:
                result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
        elif "youtu.be" in href:
            video_id = href.split("/")[-1].split("?")[0]
            result["video_url"] = f"https://www.youtube.com/embed/{video_id}"
    
    # Also check for iframe embeds
    if not result["video_url"]:
        iframe = soup.select_one("iframe[src*='youtube']")
        if iframe and iframe.get("src"):
            result["video_url"] = iframe["src"]
    
    # Description: Bulandra uses eael-tabs with #intro-tab containing the synopsis
    intro_tab = soup.select_one("#intro-tab, .eael-tab-content-item.active")
    if intro_tab:
        # Get paragraphs from the intro tab
        paragraphs = intro_tab.select("p")
        texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
        if texts:
            result["description"] = " ".join(texts[:2])
    
    # Fallback: og:description
    if not result["description"]:
        og_desc = soup.select_one("meta[property='og:description']")
        if og_desc and og_desc.get("content"):
            result["description"] = og_desc["content"]
    
    return result


def extract_arcub(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from ARCUB event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: try og:image first, then look for project images
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    else:
        img = soup.select_one(".project-image img, .event-image img, article img")
        if img and img.get("src"):
            result["image_url"] = img["src"]
    
    # Video: YouTube or Vimeo embeds
    iframe = soup.select_one("iframe[src*='youtube'], iframe[src*='vimeo']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    # Description: main content paragraphs
    content_sections = soup.select("article p, .content p, .event-description p, .post-content p")
    texts = []
    for p in content_sections:
        text = p.get_text(strip=True)
        if len(text) > 30:
            texts.append(text)
    
    if texts:
        result["description"] = " ".join(texts[:4])
    
    return result


def extract_mnac(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from MNAC event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # MNAC is Angular-based, may need JS rendering
    # Try og:image
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Try meta description as fallback
    meta_desc = soup.select_one("meta[name='description']")
    if meta_desc and meta_desc.get("content"):
        result["description"] = meta_desc["content"]
    
    return result


def extract_metropolis(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Metropolis event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: og:image
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Description: og:description
    og_desc = soup.select_one("meta[property='og:description']")
    if og_desc and og_desc.get("content"):
        result["description"] = og_desc["content"]
    
    # Video: YouTube watch links (trailer)
    video_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
    if video_link:
        href = video_link.get("href", "")
        if "youtube.com/watch" in href:
            video_id = re.search(r'v=([^&]+)', href)
            if video_id:
                result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
        elif "youtu.be" in href:
            video_id = href.split("/")[-1].split("?")[0]
            result["video_url"] = f"https://www.youtube.com/embed/{video_id}"
    
    return result


def extract_nottara(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Nottara event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: og:image
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Description: og:description
    og_desc = soup.select_one("meta[property='og:description']")
    if og_desc and og_desc.get("content"):
        result["description"] = og_desc["content"]
    
    # Video: YouTube embeds or links
    video_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
    if video_link:
        href = video_link.get("href", "")
        if "youtube.com/watch" in href:
            video_id = re.search(r'v=([^&]+)', href)
            if video_id:
                result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
        elif "youtu.be" in href:
            video_id = href.split("/")[-1].split("?")[0]
            result["video_url"] = f"https://www.youtube.com/embed/{video_id}"
    
    # Fallback to iframe
    if not result["video_url"]:
        iframe = soup.select_one("iframe[src*='youtube']")
        if iframe and iframe.get("src"):
            result["video_url"] = iframe["src"]
    
    return result


def extract_tnb(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Național București (TNB) event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # TNB is Angular-based, limited scraping capability
    # Image: og:image
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Description: og:description or meta description
    og_desc = soup.select_one("meta[property='og:description']")
    if og_desc and og_desc.get("content"):
        result["description"] = og_desc["content"]
    else:
        meta_desc = soup.select_one("meta[name='description']")
        if meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]
    
    return result


def extract_cuibul(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Cuibul Artiștilor event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: look for event images in /events_images/ path
    event_img = soup.select_one("img[src*='events_images']")
    if event_img and event_img.get("src"):
        result["image_url"] = event_img["src"]
    
    # Description: Cuibul uses Vue/Vuetify, paragraphs are in .occurence section
    paragraphs = soup.select(".occurence p")
    texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
    if texts:
        result["description"] = " ".join(texts[:3])
    
    # Video: YouTube embeds or links
    video_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
    if video_link:
        href = video_link.get("href", "")
        if "youtube.com/watch" in href:
            video_id = re.search(r'v=([^&]+)', href)
            if video_id:
                result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
        elif "youtu.be" in href:
            video_id = href.split("/")[-1].split("?")[0]
            result["video_url"] = f"https://www.youtube.com/embed/{video_id}"
    
    return result


def extract_godot(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Godot event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: Godot uses background images on carousel items
    # Try to find style attribute with background-image
    carousel_item = soup.select_one(".carousel-item.show-item[style*='background']")
    if carousel_item:
        style = carousel_item.get("style", "")
        match = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
        if match:
            result["image_url"] = match.group(1)
    
    # Fallback to og:image
    if not result["image_url"]:
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            img_url = og_image["content"]
            # Skip generic logo images
            if "logo" not in img_url.lower():
                result["image_url"] = img_url
    
    # Description: main section has show info
    main = soup.select_one("main")
    if main:
        text = main.get_text(" ", strip=True)
        # Extract meaningful description text (after show metadata)
        if len(text) > 100:
            result["description"] = text[:400]
    
    # Video: YouTube embeds
    iframe = soup.select_one("iframe[src*='youtube']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    return result


def extract_grivita53(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Grivița 53 event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: poster image - look for show poster, skip logo/footer images
    for img in soup.select("img[src*='/images/']"):
        src = img.get("src", "")
        # Skip logo and footer images
        if "logo" in src.lower() or "footer" in src.lower():
            continue
        # Look for poster images (usually have poster or show name)
        if "poster" in src.lower() or img.get("alt"):
            if not src.startswith("http"):
                src = "https://www.grivita53.ro" + src
            result["image_url"] = src
            break
    
    # Description: paragraphs after "DESPRE SPECTACOL" heading
    paragraphs = soup.select("p")
    texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
    if texts:
        result["description"] = " ".join(texts[:2])
    
    # Video: YouTube embeds or links
    iframe = soup.select_one("iframe[src*='youtube']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    else:
        yt_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
        if yt_link:
            href = yt_link.get("href", "")
            if "youtube.com/watch" in href:
                video_id = re.search(r'v=([^&]+)', href)
                if video_id:
                    result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
    
    return result


def extract_teatrulmic(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Teatrul Mic event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: WordPress featured image / poster
    featured_img = soup.select_one(".wp-post-image, img.size-full")
    if featured_img and featured_img.get("src"):
        result["image_url"] = featured_img["src"]
    
    # Fallback: gallery images
    if not result["image_url"]:
        gallery_link = soup.select_one("a[href*='wp-content/uploads'] img")
        if gallery_link:
            parent_link = gallery_link.find_parent("a")
            if parent_link:
                result["image_url"] = parent_link.get("href")
    
    # Description: look for meaningful text content
    # Try specific content patterns first
    all_text = []
    
    # Remove navigation, script, style elements from parsing
    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    
    # Look for text nodes directly
    for elem in soup.find_all(string=True):
        parent = elem.parent
        if parent.name in ['a', 'button', 'input']:
            continue
        text = elem.strip()
        # Must be substantial text, not navigation/metadata
        if len(text) > 100:
            # Skip navigation and meta content
            skip_patterns = [
                "Stagiunea", "STAGIUNEA", "SPECTACOLE", "TRUPA TM", "PROGRAM",
                "STIRI", "INTERVIURI", "CONTACT", "CALENDAR", "DISTRIBUTIE",
                "Cumpara Bilet", "Despre Spectacol", "Politica de", "Login",
                "ticketsys", "<a ", "class=", "style="
            ]
            if not any(skip in text for skip in skip_patterns):
                all_text.append(text)
    
    if all_text:
        result["description"] = " ".join(all_text[:2])[:400]
    
    # Try og:description as fallback
    if not result["description"]:
        og_desc = soup.select_one("meta[property='og:description']")
        if og_desc and og_desc.get("content"):
            result["description"] = og_desc["content"]
    
    # Video: YouTube embeds
    iframe = soup.select_one("iframe[src*='youtube']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    return result


def extract_improteca(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Improteca event pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Image: og:image (Elementor-based site)
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Fallback: featured image
    if not result["image_url"]:
        featured = soup.select_one(".elementor-widget-image img, article img")
        if featured and featured.get("src"):
            result["image_url"] = featured["src"]
    
    # Description: paragraphs from content
    paragraphs = soup.select(".elementor-widget-text-editor p, article p, .entry-content p")
    texts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        # Skip short paragraphs and emoji-only lines
        if len(text) > 30 and not text.startswith("📅") and not text.startswith("🗺️"):
            texts.append(text)
    
    if texts:
        result["description"] = " ".join(texts[:3])
    
    # Video: YouTube embeds or links
    iframe = soup.select_one("iframe[src*='youtube']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    else:
        yt_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
        if yt_link:
            href = yt_link.get("href", "")
            if "youtube.com/watch" in href:
                video_id = re.search(r'v=([^&]+)', href)
                if video_id:
                    result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
    
    return result


def extract_mare(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from MARe (Muzeul de Artă Recentă) exhibition pages."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    paragraphs = soup.select("p")
    texts = []
    skip_patterns = ["cookie", "consimțământ", "politica", "newsletter", "abonează"]
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 50:
            if not any(skip.lower() in text.lower() for skip in skip_patterns):
                texts.append(text)
    
    if texts:
        result["description"] = " ".join(texts[:2])[:500]
    
    iframe = soup.select_one("iframe[src*='youtube'], iframe[src*='vimeo']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    return result


def extract_elvirepopescu(soup: BeautifulSoup, url: str) -> dict:
    """Extract enrichment data from Cinema Elvire Popescu event pages (via eventbook.ro)."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    paragraphs = soup.select("p")
    texts = []
    skip_patterns = ["cookie", "subscribe", "eventbook", "bilete", "price"]
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 50:
            if not any(skip.lower() in text.lower() for skip in skip_patterns):
                texts.append(text)
    
    if texts:
        result["description"] = " ".join(texts[:2])[:500]
    
    iframe = soup.select_one("iframe[src*='youtube']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    return result


def extract_generic(soup: BeautifulSoup, url: str) -> dict:
    """Generic extractor for unknown sources."""
    result: dict = {"description": None, "image_url": None, "video_url": None}
    
    # Try og:image
    og_image = soup.select_one("meta[property='og:image']")
    if og_image and og_image.get("content"):
        result["image_url"] = og_image["content"]
    
    # Try og:description or meta description
    og_desc = soup.select_one("meta[property='og:description']")
    if og_desc and og_desc.get("content"):
        result["description"] = og_desc["content"]
    else:
        meta_desc = soup.select_one("meta[name='description']")
        if meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]
    
    # Look for video embeds (iframes)
    iframe = soup.select_one("iframe[src*='youtube'], iframe[src*='vimeo']")
    if iframe and iframe.get("src"):
        result["video_url"] = iframe["src"]
    
    # Also look for video links
    if not result["video_url"]:
        video_link = soup.select_one("a[href*='youtube.com/watch'], a[href*='youtu.be']")
        if video_link:
            href = video_link.get("href", "")
            if "youtube.com/watch" in href:
                video_id = re.search(r'v=([^&]+)', href)
                if video_id:
                    result["video_url"] = f"https://www.youtube.com/embed/{video_id.group(1)}"
            elif "youtu.be" in href:
                video_id = href.split("/")[-1].split("?")[0]
                result["video_url"] = f"https://www.youtube.com/embed/{video_id}"
    
    return result


# Map source names to their extractors
SOURCE_EXTRACTORS = {
    "bulandra": extract_bulandra,
    "arcub": extract_arcub,
    "mnac": extract_mnac,
    "metropolis": extract_metropolis,
    "nottara": extract_nottara,
    "tnb": extract_tnb,
    "cuibul": extract_cuibul,
    "godot": extract_godot,
    "grivita53": extract_grivita53,
    "teatrulmic": extract_teatrulmic,
    "improteca": extract_improteca,
    "mare": extract_mare,
    "elvirepopescu": extract_elvirepopescu,
}


def scrape_event_details(event: Event) -> dict:
    """Fetch and extract enrichment data from event detail page."""
    if not event.url:
        return {"description": None, "image_url": None, "video_url": None}
    
    try:
        # Most theatre sites need JS rendering
        html = fetch_page(event.url, needs_js=True, timeout=15000)
    except HttpError as e:
        print(f"  Failed to fetch {event.url}: {e}")
        return {"description": None, "image_url": None, "video_url": None}
    except Exception as e:
        print(f"  Unexpected error fetching {event.url}: {e}")
        return {"description": None, "image_url": None, "video_url": None}
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Use source-specific extractor if available
    extractor = SOURCE_EXTRACTORS.get(event.source, extract_generic)
    return extractor(soup, event.url)


def generate_ai_description(event: Event) -> str | None:
    """Generate description using Gemini AI."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""Ești un critic de teatru și cultură din București. 
Generează o descriere scurtă și captivantă (2-3 propoziții, max 150 cuvinte) pentru acest eveniment:

Titlu: {event.title}
Locație: {event.venue}
Categorie: {"Teatru" if event.category == "theatre" else "Cultură"}
{f"Artist/Autor: {event.artist}" if event.artist else ""}

Descrierea trebuie să fie în limba română, să sune natural și să incite curiozitatea spectatorului.
Nu inventa detalii specifice despre intrigă sau distribuție dacă nu sunt menționate.
Răspunde DOAR cu descrierea, fără prefixe sau explicații."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        # Clean up any markdown or quotes
        text = re.sub(r'^["\']|["\']$', '', text)
        return text if len(text) > 20 else None
    except Exception as e:
        print(f"  AI description failed for {event.title}: {e}")
        return None


def enrich_event(event: Event) -> Event:
    """Enrich a single event with description, image, and video."""
    # Skip music events
    if event.category == "music":
        return event
    
    # Skip if already enriched
    if event.description or event.image_url or event.video_url:
        return event
    
    # Try to scrape from source page
    details = scrape_event_details(event)
    
    description = details.get("description")
    description_source = "scraped" if description else None
    
    # If no description found, try AI fallback
    if not description:
        description = generate_ai_description(event)
        if description:
            description_source = "ai"
    
    # Truncate long descriptions
    if description and len(description) > 500:
        description = description[:497] + "..."
    
    return replace(
        event,
        description=description,
        description_source=description_source,
        image_url=details.get("image_url"),
        video_url=details.get("video_url"),
    )


def enrich_events(events: list[Event]) -> list[Event]:
    """Enrich all theatre/culture events with additional details."""
    enriched: list[Event] = []
    
    theatre_culture = [e for e in events if e.category in ("theatre", "culture")]
    total = len(theatre_culture)
    
    for i, event in enumerate(events):
        if event.category in ("theatre", "culture"):
            print(f"  [{i+1}/{total}] Enriching: {event.title[:40]}...", end=" ", flush=True)
            enriched_event = enrich_event(event)
            status = "✓" if enriched_event.description or enriched_event.image_url else "○"
            print(status)
            enriched.append(enriched_event)
        else:
            enriched.append(event)
    
    return enriched
