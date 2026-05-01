from __future__ import annotations

import re


H1_PATTERN = re.compile(r"^\s*#\s+(?P<title>.+?)\s*$", re.MULTILINE)


def derive_version_number(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def classify_version(tag: str) -> str:
    normalized = tag.lower()
    if "alpha" in normalized:
        return "alpha"
    if "beta" in normalized or "rc" in normalized:
        return "beta"
    return "release"


def derive_release_title(body: str, fallback_name: str) -> str:
    match = H1_PATTERN.search(body or "")
    if not match:
        return fallback_name

    title = match.group("title").strip()
    for separator in (" – ", " - "):
        if separator in title:
            _, _, trailing = title.partition(separator)
            trailing = trailing.strip()
            if trailing:
                return trailing
    return title or fallback_name


def trim_release_body(body: str) -> str:
    if not body.strip():
        return ""

    match = H1_PATTERN.search(body)
    if not match:
        return body.strip()

    remainder = body[match.end():]
    remainder = re.sub(r"^\s*\n+", "", remainder, count=1)
    return remainder.strip()
