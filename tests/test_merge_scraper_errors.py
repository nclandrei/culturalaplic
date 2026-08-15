import json

from scripts.merge_scraper_errors import merge_error_files


def write_errors(path, errors):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timestamp": "2026-08-15T09:00:00", "errors": errors}))


def test_merge_error_files_combines_matrix_artifacts(tmp_path):
    input_dir = tmp_path / "all-errors"
    output_file = tmp_path / "artifacts" / "scraper_errors.json"
    eventbook_error = {
        "scraper_name": "eventbook",
        "error_message": "returned 0 events",
        "traceback": "returned 0 events",
        "category": "theatre",
        "events_url": "https://eventbook.ro/city/bucuresti",
    }
    elvire_error = {
        "scraper_name": "elvirepopescu",
        "error_message": "returned 0 events",
        "traceback": "returned 0 events",
        "category": "culture",
        "events_url": "https://example.com/elvire",
    }
    write_errors(
        input_dir / "scraper-errors-group-1" / "scraper_errors.json",
        [eventbook_error],
    )
    write_errors(
        input_dir / "scraper-errors-group-2" / "scraper_errors.json",
        [elvire_error, eventbook_error],
    )

    count = merge_error_files(input_dir, output_file)

    assert count == 2
    merged = json.loads(output_file.read_text())
    assert [error["scraper_name"] for error in merged["errors"]] == [
        "eventbook",
        "elvirepopescu",
    ]


def test_merge_error_files_does_not_create_empty_artifact(tmp_path):
    output_file = tmp_path / "artifacts" / "scraper_errors.json"

    count = merge_error_files(tmp_path / "missing", output_file)

    assert count == 0
    assert not output_file.exists()
