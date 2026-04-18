from pathlib import Path

import pytest

from blockops_publish.config import ConfigError, deep_merge, load_override_file, validate_manifest


def test_deep_merge_overrides_nested_values() -> None:
    base = {"release": {"title": "Old", "version_type": "beta"}, "variants": {"paper": {"artifact": "a"}}}
    override = {"release": {"title": "New"}, "variants": {"paper": {"artifact": "b"}}}

    merged = deep_merge(base, override)

    assert merged["release"]["title"] == "New"
    assert merged["release"]["version_type"] == "beta"
    assert merged["variants"]["paper"]["artifact"] == "b"


def test_load_override_file_requires_mapping(tmp_path: Path) -> None:
    override = tmp_path / "override.yml"
    override.write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_override_file(override)


def test_validate_manifest_requires_expected_shape() -> None:
    manifest = {
        "schema_version": 1,
        "providers": {"modrinth": {"project_id": "abc"}},
        "variants": {
            "paper": {
                "artifact": "Socialismus-PAPER-{version}.jar",
                "game_versions": ["1.20.6"],
                "providers": {"modrinth": {"loaders": ["paper"]}},
            }
        },
    }

    validate_manifest(manifest)
