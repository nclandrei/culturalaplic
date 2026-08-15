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


def test_auto_fix_workflow_handles_every_reported_scraper():
    workflow = (ROOT / ".github/workflows/fix-scrapers.yml").read_text()

    assert "['errors'][0]" not in workflow
    assert "Fix every scraper listed below" in workflow
    assert 'git add scrapers/ services/enrichment.py' in workflow


def test_auto_fix_workflow_uses_the_current_amp_cli():
    workflow = (ROOT / ".github/workflows/fix-scrapers.yml").read_text()

    assert "npm install -g @ampcode/cli" in workflow
    assert "@anthropic-ai/amp" not in workflow
    assert '"amp.dangerouslyAllowAll": true' in workflow
    assert "--dangerously-allow-all" not in workflow


def test_auto_fix_workflow_can_push_and_open_pull_request():
    workflow = (ROOT / ".github/workflows/fix-scrapers.yml").read_text()

    assert "permissions:\n  contents: write\n  pull-requests: write" in workflow


def test_auto_fix_workflow_detects_amp_errors_with_zero_exit_status():
    workflow = (ROOT / ".github/workflows/fix-scrapers.yml").read_text()

    assert "AMP_STATUS=${PIPESTATUS[1]}" in workflow
    assert 'grep -qi "Error: Out of Credits"' in workflow
    assert 'if [ "$DRY_RUN" != "true" ]; then' in workflow
