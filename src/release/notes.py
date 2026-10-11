from __future__ import annotations

from collections.abc import Callable, Sequence

from release.formatters.bbcode import format_bbcode
from release.groupers.title_prefix import DEFAULT_DEVELOPER_TITLE, group_by_title_prefix


FORMATTERS: dict[str, Callable[[str], str]] = {
    "bbcode": format_bbcode,
}

def format_release_notes(
    release_body: str,
    release_format: str,
    grouping: str = "",
    developer_prefixes: Sequence[str] = (),
    developer_title: str = DEFAULT_DEVELOPER_TITLE,
) -> str:
    if grouping == "title-prefix":
        release_body = group_by_title_prefix(release_body, developer_prefixes, developer_title or DEFAULT_DEVELOPER_TITLE)
    elif grouping:
        raise ValueError(f"Unsupported release note grouping: {grouping}")

    if release_format == "markdown":
        return release_body if release_body.endswith("\n") else release_body + "\n"

    formatter = FORMATTERS.get(release_format)
    if formatter is None:
        raise ValueError(f"Unsupported release note format: {release_format}")

    return formatter(release_body)


def parse_prefixes(value: str) -> list[str]:
    return [prefix.strip() for prefix in value.replace("\n", ",").split(",") if prefix.strip()]
