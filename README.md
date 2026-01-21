# Cultură la plic

Weekly event aggregator that matches upcoming concerts and theatre shows in Bucharest against your Spotify followed artists, then sends you an email digest.

## How it works

1. **Scrapes** event listings from Romanian ticketing sites (iaBilet, Control, Expirat, Quantic, JFR) and theatres (Bulandra)
2. **Fetches** your followed artists from Spotify
3. **Matches** events to artists using fuzzy string matching
4. **Deduplicates** events using LLM-assisted comparison
5. **Emails** you a digest of new events via Resend

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SPOTIFY_CLIENT_ID` | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | OAuth refresh token (use `scripts/get_refresh_token.py`) |
| `GEMINI_API_KEY` | Gemini API key for LLM deduplication |
| `RESEND_API_KEY` | Resend API key for sending emails |
| `NOTIFY_EMAIL` | Email address to receive digests |

### Getting Spotify Credentials

1. Create a Spotify app at [developer.spotify.com](https://developer.spotify.com/dashboard)
2. Add `http://localhost:8888/callback` as a redirect URI
3. Run `python scripts/get_refresh_token.py` to get your refresh token

## Usage

```bash
python main.py
```

## Automation

A GitHub Actions workflow runs every Monday at 9am UTC. Configure the secrets listed above in your repository settings.

## Project Structure

```
├── main.py              # Orchestrator
├── models.py            # Event dataclass
├── scrapers/
│   ├── music/           # Concert scrapers (iabilet, control, expirat, etc.)
│   └── theatre/         # Theatre scrapers (bulandra)
├── services/
│   ├── http.py          # HTTP/Playwright fetching
│   ├── spotify.py       # Spotify API client
│   ├── dedup.py         # Event deduplication
│   └── email.py         # Email digest via Resend
├── scripts/             # Utility scripts
└── data/                # JSON output (retains events from 1st of current month onwards)
```

## Adding a New Scraper

Create a module in `scrapers/music/` or `scrapers/theatre/` with a `scrape() -> list[Event]` function:

```python
from models import Event
from services.http import fetch_page

def scrape() -> list[Event]:
    html = fetch_page("https://example.com/events", needs_js=False)
    # Parse and return events
    return events
```

Then import and add it to the scraper list in `main.py`.
