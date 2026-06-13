from __future__ import annotations

import re
from collections import OrderedDict


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
    prefix_groups: OrderedDict[str, list[str]] = OrderedDict()
    other_changes: list[str] = []

    for line in lines:
        match = BULLET_PATTERN.match(line.strip())
        if not match:
            continue

        entry = match.group("entry")
        prefix_match = PREFIX_PATTERN.match(entry)
        if not prefix_match:
            other_changes.append(entry)
            continue

        prefix = prefix_match.group("prefix").strip()
        rest = prefix_match.group("rest").strip()
        prefix_groups.setdefault(prefix, []).append(rest)

    if len(prefix_groups) <= 1 and not other_changes:
        return [line for line in lines if line.strip()]

    rewritten: list[str] = []

    for prefix, entries in prefix_groups.items():
        rewritten.append(f"## {prefix}")
        rewritten.append("")
        for entry in entries:
            rewritten.append(f"* {entry}")
        rewritten.append("")

    if other_changes:
        rewritten.append("## Other changes")
        rewritten.append("")
        for entry in other_changes:
            rewritten.append(f"* {entry}")
        rewritten.append("")

    while rewritten and rewritten[-1] == "":
        rewritten.pop()

    rewritten.append("")
    return rewritten


def _is_prefixed_bullet(line: str) -> bool:
    match = BULLET_PATTERN.match(line.strip())
    if not match:
        return False
    return PREFIX_PATTERN.match(match.group("entry")) is not None
