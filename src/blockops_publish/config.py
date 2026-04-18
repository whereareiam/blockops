from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the distribution configuration is invalid."""


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Manifest file does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"Expected a mapping in manifest: {path}")

    return data


def load_override_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}

    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ConfigError("Override YAML must be a mapping at the top level")

    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")

    providers = manifest.get("providers")
    variants = manifest.get("variants")

    if not isinstance(providers, dict) or not providers:
        raise ConfigError("providers must be a non-empty mapping")

    if not isinstance(variants, dict) or not variants:
        raise ConfigError("variants must be a non-empty mapping")

    for variant_name, variant in variants.items():
        if not isinstance(variant, dict):
            raise ConfigError(f"Variant {variant_name} must be a mapping")

        artifact = variant.get("artifact")
        game_versions = variant.get("game_versions")
        provider_map = variant.get("providers")

        if not isinstance(artifact, str) or not artifact:
            raise ConfigError(f"Variant {variant_name} must define artifact")

        if not isinstance(game_versions, list) or not all(isinstance(item, str) for item in game_versions):
            raise ConfigError(f"Variant {variant_name} must define game_versions as a list of strings")

        if not isinstance(provider_map, dict) or not provider_map:
            raise ConfigError(f"Variant {variant_name} must define providers")
