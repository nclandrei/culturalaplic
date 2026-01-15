# AGENTS.md

## Commands
- **Run**: `python main.py`
- **Install deps**: `pip install -r requirements.txt`
- **Playwright setup**: `playwright install chromium`
- No test suite exists; add tests with pytest if needed

## Architecture
- **main.py**: Orchestrator - runs scrapers, matches artists, deduplicates, sends emails
- **models.py**: `Event` dataclass (title, artist, venue, date, url, source, category, price)
- **scrapers/**: Site-specific scrapers returning `list[Event]`
  - `music/`: iabilet, eventbook, control, expirat, quantic, jfr, hardrock
  - `theatre/`: bulandra
- **services/**: Shared utilities (http, spotify, dedup, email)
- **data/**: JSON output files (date-prefixed, 7-day retention)
- **tmp/**: Test data, screenshots, debug output (gitignored)

## Code Style
- Python 3.11+ with type hints (`str | None`, `list[Event]`)
- Dataclasses for models, absolute imports from project root
- Each scraper exposes a `scrape() -> list[Event]` function
- Use `services/http.fetch_page(url, needs_js=bool)` for HTTP requests
- Env vars: `SPOTIFY_*`, `OPENAI_API_KEY`, `RESEND_API_KEY`, `NOTIFY_EMAIL`
