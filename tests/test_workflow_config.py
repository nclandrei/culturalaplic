from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_scrape_workflow_uploads_results_before_reporting_scraper_failure():
    workflow = (ROOT / ".github/workflows/scrape.yml").read_text()

    upload_step = workflow.split("- name: Upload group events", 1)[1].split(
        "- name: Upload scraper errors", 1
    )[0]
    assert "if: always()" in upload_step
    assert "if-no-files-found: error" in upload_step
    assert "if: steps.scrape.outcome == 'success'" not in workflow
    assert "- name: Report scraper failure" in workflow
    assert "if: steps.scrape.outcome == 'failure'" in workflow


def test_scrape_workflow_requires_both_group_artifacts_before_merge():
    workflow = (ROOT / ".github/workflows/scrape.yml").read_text()

    group_downloads = workflow.split("- name: Download group 1 events", 1)[1].split(
        "- name: Merge group results", 1
    )[0]
    assert "name: events-group-1" in group_downloads
    assert "name: events-group-2" in group_downloads
    assert "continue-on-error" not in group_downloads
    assert "if ls artifacts/events_group_*.json" not in workflow
    assert "run: python3 main.py --merge" in workflow


def test_workflows_publish_and_require_the_same_combined_error_artifact():
    scrape_workflow = (ROOT / ".github/workflows/scrape.yml").read_text()
    fix_workflow = (ROOT / ".github/workflows/fix-scrapers.yml").read_text()

    assert "merge-multiple: true" not in scrape_workflow
    assert "python3 scripts/merge_scraper_errors.py" in scrape_workflow
    assert "name: scraper-errors\n" in scrape_workflow
    assert "name: scraper-errors\n" in fix_workflow
    download_step = fix_workflow.split(
        "- name: Download scraper errors artifact", 1
    )[1].split("- name: Validate scraper errors artifact", 1)[0]
    assert "continue-on-error" not in download_step
    assert "test -s artifacts/scraper_errors.json" in fix_workflow
