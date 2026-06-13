from __future__ import annotations

import re


BULLET_PATTERN = re.compile(r"^\* (?P<entry>.+)$")
PREFIX_PATTERN = re.compile(r"^(?P<prefix>[^:]+):\s+(?P<rest>.+)$")


def group_by_title_prefix(body: str) -> str:
    lines = body.splitlines()
    rewritten: list[str] = []
    index = 0

    while index < len(lines):
        if not _is_prefixed_bullet(lines[index]):
            rewritten.append(lines[index])
            index += 1
            continue

        block: list[str] = []
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                block.append(lines[index])
                index += 1
                continue
            if not BULLET_PATTERN.match(stripped):
                break
            block.append(lines[index])
            index += 1

        rewritten.extend(_group_block(block))

    return "\n".join(rewritten).rstrip() + "\n"


def _group_block(lines: list[str]) -> list[str]:
    prefixed_entries: list[tuple[str, int, str]] = []
    other_entries: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        match = BULLET_PATTERN.match(line.strip())
        if not match:
            continue

        entry = match.group("entry")
        prefix_match = PREFIX_PATTERN.match(entry)
        if not prefix_match:
            other_entries.append((index, entry))
            continue

        prefix = prefix_match.group("prefix").strip()
        prefixed_entries.append((prefix.lower(), index, entry))

    if len(prefixed_entries) <= 1:
        return [line for line in lines if line.strip()]

    sorted_prefixed = [entry for _, _, entry in sorted(prefixed_entries, key=lambda item: (item[0], item[1]))]
    rewritten: list[str] = []
    prefixed_index = 0
    other_index = 0

    for line in lines:
        match = BULLET_PATTERN.match(line.strip())
        if not match:
            continue

        entry = match.group("entry")
        prefix_match = PREFIX_PATTERN.match(entry)
        if prefix_match:
            rewritten.append(f"* {sorted_prefixed[prefixed_index]}")
            prefixed_index += 1
            continue

        rewritten.append(f"* {other_entries[other_index][1]}")
        other_index += 1

    return rewritten


def _is_prefixed_bullet(line: str) -> bool:
    match = BULLET_PATTERN.match(line.strip())
    if not match:
        return False
    return PREFIX_PATTERN.match(match.group("entry")) is not None
