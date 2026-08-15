import json

import pytest

import main


def write_group_artifact(path, group: int) -> None:
    path.write_text(
        json.dumps(
            {
                "scraped_at": "2026-08-15T09:00:00",
                "group": group,
                "music_events": [],
                "theatre_events": [],
                "culture_events": [],
            }
        )
    )


def test_merge_refuses_to_publish_when_a_group_artifact_is_missing(
    tmp_path, monkeypatch
):
    artifacts_dir = tmp_path / "artifacts"
    data_dir = tmp_path / "data"
    artifacts_dir.mkdir()
    data_dir.mkdir()
    events_file = data_dir / "events.json"
    original = {
        "scraped_at": "2026-08-14T09:00:00",
        "music_events": [],
        "theatre_events": [],
        "culture_events": [],
    }
    events_file.write_text(json.dumps(original))
    write_group_artifact(artifacts_dir / "events_group_1.json", group=1)

    monkeypatch.setattr(main, "ARTIFACTS_DIR", artifacts_dir)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "EVENTS_FILE", events_file)

    with pytest.raises(FileNotFoundError, match="events_group_2.json"):
        main.merge_group_artifacts()

    assert json.loads(events_file.read_text()) == original


def test_merge_accepts_a_complete_pair_of_group_artifacts(tmp_path, monkeypatch):
    artifacts_dir = tmp_path / "artifacts"
    data_dir = tmp_path / "data"
    artifacts_dir.mkdir()
    data_dir.mkdir()
    events_file = data_dir / "events.json"
    events_file.write_text(
        json.dumps(
            {
                "scraped_at": "2026-08-14T09:00:00",
                "music_events": [],
                "theatre_events": [],
                "culture_events": [],
            }
        )
    )
    write_group_artifact(artifacts_dir / "events_group_1.json", group=1)
    write_group_artifact(artifacts_dir / "events_group_2.json", group=2)

    monkeypatch.setattr(main, "ARTIFACTS_DIR", artifacts_dir)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "EVENTS_FILE", events_file)

    main.merge_group_artifacts()

    merged = json.loads(events_file.read_text())
    assert merged["scraped_at"] != "2026-08-14T09:00:00"

