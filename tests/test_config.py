from pathlib import Path

import pytest

from blockops_publish.shared.config import ConfigError, deep_merge, load_override_file, validate_manifest


def test_deep_merge_overrides_nested_values() -> None:
    base = {"release": {"title": "Old", "version_type": "beta"}, "artifacts": {"paper": {"file": "a"}}}
    override = {"release": {"title": "New"}, "artifacts": {"paper": {"file": "b"}}}

    merged = deep_merge(base, override)

    assert merged["release"]["title"] == "New"
    assert merged["release"]["version_type"] == "beta"
    assert merged["artifacts"]["paper"]["file"] == "b"


def test_load_override_file_requires_mapping(tmp_path: Path) -> None:
    override = tmp_path / "override.yml"
    override.write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_override_file(override)


def test_validate_manifest_requires_expected_shape() -> None:
    manifest = {
        "artifacts": {
            "paper": {
                "file": "Socialismus-PAPER-{version}.jar",
                "game_versions": ["1.20.6"],
                "loaders": ["paper"],
            }
        },
        "publications": {
            "paper-modrinth": {
                "provider": "modrinth",
                "artifact": "paper",
                "project_id": "abc",
            }
        },
    }

    validate_manifest(manifest)


def test_validate_manifest_requires_known_publication_artifact() -> None:
    manifest = {
        "artifacts": {
            "paper": {
                "file": "Socialismus-PAPER-{version}.jar",
                "game_versions": ["1.20.6"],
            }
        },
        "publications": {
            "paper-modrinth": {
                "provider": "modrinth",
                "artifact": "missing",
                "project_id": "abc",
            }
        },
    }

    with pytest.raises(ConfigError, match="unknown artifact"):
        validate_manifest(manifest)
