from unittest.mock import patch

from main import SCRAPER_GROUPS, run_music_scrapers
from scrapers.music import hardrock


def test_hardrock_is_registered_for_scheduled_and_local_runs():
    assert hardrock in SCRAPER_GROUPS[1]["music"]

    with (
        patch("main.should_run_festival_scrapers", return_value=False),
        patch("main.run_scraper_safely", return_value=[]) as run_scraper,
    ):
        run_music_scrapers()

    scheduled_scrapers = [call.args[0] for call in run_scraper.call_args_list]
    assert hardrock in scheduled_scrapers
