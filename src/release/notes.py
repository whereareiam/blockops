from __future__ import annotations

from collections.abc import Callable

from release.formatters.bbcode import format_bbcode


FORMATTERS: dict[str, Callable[[str], str]] = {
    "bbcode": format_bbcode,
}


def format_release_notes(release_body: str, release_format: str) -> str:
    formatter = FORMATTERS.get(release_format)
    if formatter is None:
        raise ValueError(f"Unsupported release note format: {release_format}")

    return formatter(release_body)
