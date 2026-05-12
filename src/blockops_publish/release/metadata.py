from __future__ import annotations

import re
from typing import Any

from blockops_publish.manifest.config import ConfigError


H1_PATTERN = re.compile(r"^\s*#\s+(?P<title>.+?)\s*$", re.MULTILINE)
ALLOWED_PHASES = {"release", "beta", "alpha"}
DEFAULT_CLASSIFICATION_RULES = [
    {"phase": "alpha", "patterns": [r"alpha"]},
    {"phase": "beta", "patterns": [r"beta", r"rc"]},
]


def derive_version_number(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def classify_version(tag: str, release_config: dict[str, Any] | None = None) -> str:
    classification = (release_config or {}).get("classification", {})
    rules = classification.get("rules", DEFAULT_CLASSIFICATION_RULES)
    default_phase = classification.get("default_phase", "release")

    if default_phase not in ALLOWED_PHASES:
        raise ConfigError(f"Unsupported release default phase: {default_phase}")

    normalized = tag.lower()
    for rule in rules:
        phase = rule.get("phase")
        patterns = rule.get("patterns")
        if phase not in ALLOWED_PHASES:
            raise ConfigError(f"Unsupported release phase in classification rule: {phase}")
        if not isinstance(patterns, list) or not all(isinstance(pattern, str) and pattern for pattern in patterns):
            raise ConfigError(f"Release classification rule for {phase} must define non-empty string patterns")
        for pattern in patterns:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return phase

    return default_phase


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
