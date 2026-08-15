#!/usr/bin/env python3
"""Combine scraper error artifacts produced by parallel scraper groups."""

import argparse
import json
from datetime import datetime
from pathlib import Path


def merge_error_files(input_dir: Path, output_file: Path) -> int:
    """Merge and deduplicate every nested scraper_errors.json file."""
    errors: list[dict] = []
    seen: set[tuple] = set()

    for error_file in sorted(input_dir.glob("**/scraper_errors.json")):
        data = json.loads(error_file.read_text())
        for error in data.get("errors", []):
            key = (
                error.get("scraper_name"),
                error.get("error_message"),
                error.get("category"),
                error.get("events_url"),
            )
            if key not in seen:
                seen.add(key)
                errors.append(error)

    if not errors:
        return 0

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(
            {"timestamp": datetime.now().isoformat(), "errors": errors},
            indent=2,
        )
    )
    return len(errors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    print(merge_error_files(args.input_dir, args.output))


if __name__ == "__main__":
    main()
