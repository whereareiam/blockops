from __future__ import annotations

from collections.abc import Callable

from release.formatters.bbcode import format_bbcode
from release.groupers.title_prefix import group_by_title_prefix


FORMATTERS: dict[str, Callable[[str], str]] = {
    "bbcode": format_bbcode,
}

GROUPERS: dict[str, Callable[[str], str]] = {
    "title-prefix": group_by_title_prefix,
}

def format_release_notes(release_body: str, release_format: str, grouping: str = "") -> str:
    if grouping:
        grouper = GROUPERS.get(grouping)
        if grouper is None:
            raise ValueError(f"Unsupported release note grouping: {grouping}")
        release_body = grouper(release_body)

    if release_format == "markdown":
        return release_body if release_body.endswith("\n") else release_body + "\n"

    formatter = FORMATTERS.get(release_format)
    if formatter is None:
        raise ValueError(f"Unsupported release note format: {release_format}")

    return formatter(release_body)
