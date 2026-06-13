from __future__ import annotations

import argparse
from pathlib import Path

from release.notes import format_release_notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Format release notes for external platforms.")
    parser.add_argument("--format", dest="release_format", required=True)
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()

    release_body = args.input_file.read_text(encoding="utf-8")
    formatted = format_release_notes(release_body, args.release_format)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(formatted, encoding="utf-8")


if __name__ == "__main__":
    main()
