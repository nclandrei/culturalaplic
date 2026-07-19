import sys
from unittest.mock import patch

from main import SCRAPER_GROUPS, main, run_music_scrapers, run_theatre_scrapers
from scrapers.music import hardrock
from scrapers.theatre import eventbook
from scripts.test_full_flow import SCRAPERS as INTEGRATION_SCRAPERS


def test_hardrock_is_registered_for_scheduled_and_local_runs():
    assert hardrock in SCRAPER_GROUPS[1]["music"]

    with (
        patch("main.should_run_festival_scrapers", return_value=False),
        patch("main.run_scraper_safely", return_value=[]) as run_scraper,
    ):
        run_music_scrapers()

    scheduled_scrapers = [call.args[0] for call in run_scraper.call_args_list]
    assert hardrock in scheduled_scrapers


def test_eventbook_is_registered_for_scheduled_and_local_runs():
    assert eventbook in SCRAPER_GROUPS[1]["theatre"]

    with patch("main.run_scraper_safely", return_value=[]) as run_scraper:
        run_theatre_scrapers()

    scheduled_scrapers = [call.args[0] for call in run_scraper.call_args_list]
    assert eventbook in scheduled_scrapers


def test_dry_run_lists_newly_registered_scrapers(capsys):
    with (
        patch.object(sys, "argv", ["main.py", "--dry-run"]),
        patch("main.should_run_festival_scrapers", return_value=False),
    ):
        main()

    output = capsys.readouterr().out
    assert "  - hardrock" in output
    assert "  - eventbook" in output


def test_full_flow_uses_scheduler_registry():
    for category in ("music", "theatre", "culture"):
        registered = {
            *SCRAPER_GROUPS[1][category],
            *SCRAPER_GROUPS[2][category],
        }
        assert registered.issubset(set(INTEGRATION_SCRAPERS[category]))
