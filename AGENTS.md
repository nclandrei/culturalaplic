# AGENTS.md

## Commands
- **Run**: `python main.py`
- **Install deps**: `pip install -r requirements.txt`
- **Playwright setup**: `playwright install chromium`
- **Unit tests**: `pytest tests/`
- **Integration test**: `python scripts/test_full_flow.py`
- **Integration test + alert**: `python scripts/test_full_flow.py --alert`
- **Test alert only**: `python scripts/test_full_flow.py --alert-only`

### Web (Next.js)
- **Dev server**: `cd web && pnpm dev`
- **Build**: `cd web && pnpm build`
- **Install deps**: `cd web && pnpm install`

## Architecture
- **main.py**: Orchestrator - runs scrapers, matches artists, deduplicates, sends emails
- **models.py**: `Event` dataclass (title, artist, venue, date, url, source, category, price)
- **scrapers/**: Site-specific scrapers returning `list[Event]`
  - `music/`: iabilet, eventbook, control, expirat, quantic, jfr, hardrock
  - `theatre/`: bulandra
  - `culture/`: arcub
- **services/**: Shared utilities (http, spotify, dedup, email)
- **data/**: JSON output files (date-prefixed, 7-day retention)
- **tmp/**: Test data, screenshots, debug output (gitignored)
- **web/**: Next.js frontend ("Calendarul Hipsterului")
  - `src/app/`: App router pages and layout
  - `src/components/`: React components (EventCard, EventCalendar, EventList, Header)
  - `src/components/ui/`: neobrutalism.dev UI components
  - `src/types/`: TypeScript types (Event)
  - `src/data/`: Sample JSON data for development

## Code Style
- Python 3.11+ with type hints (`str | None`, `list[Event]`)
- Dataclasses for models, absolute imports from project root
- Each scraper exposes a `scrape() -> list[Event]` function
- Use `services/http.fetch_page(url, needs_js=bool)` for HTTP requests
- Env vars: `SPOTIFY_*`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `NOTIFY_EMAIL`
