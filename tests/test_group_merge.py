import json

import pytest

import main


def write_group_artifact(
    path,
    group: int,
    *,
    successful_sources: dict[str, list[str]] | None = None,
    music_events: list[dict] | None = None,
    theatre_events: list[dict] | None = None,
    culture_events: list[dict] | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "scraped_at": "2026-08-15T09:00:00",
                "group": group,
                "successful_sources": successful_sources
                or {"music": [], "theatre": [], "culture": []},
                "music_events": music_events or [],
                "theatre_events": theatre_events or [],
                "culture_events": culture_events or [],
            }
        )
    )


def event(title: str, source: str, category: str = "culture") -> dict:
    return {
        "title": title,
        "artist": None,
        "venue": "Test venue",
        "date": "2099-08-15T11:00:00",
        "url": f"https://example.com/{title.lower().replace(' ', '-')}",
        "source": source,
        "category": category,
    }


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


def test_merge_replaces_events_only_for_successfully_scraped_sources(
    tmp_path, monkeypatch
):
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
                "culture_events": [
                    event("Stale Improteca rollover", "improteca"),
                    event("Preserved failed feed", "mnac"),
                ],
            }
        )
    )
    write_group_artifact(
        artifacts_dir / "events_group_1.json",
        group=1,
        successful_sources={"music": [], "theatre": [], "culture": []},
    )
    write_group_artifact(
        artifacts_dir / "events_group_2.json",
        group=2,
        successful_sources={
            "music": [],
            "theatre": [],
            "culture": ["improteca"],
        },
        culture_events=[event("Current Improteca event", "improteca")],
    )

    monkeypatch.setattr(main, "ARTIFACTS_DIR", artifacts_dir)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "EVENTS_FILE", events_file)

    main.merge_group_artifacts()

    merged = json.loads(events_file.read_text())
    titles = {item["title"] for item in merged["culture_events"]}
    assert titles == {"Current Improteca event", "Preserved failed feed"}
