from pathlib import Path

import pytest

from publish.manifest.config import ConfigError, deep_merge, load_override_file, validate_manifest


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


def test_validate_manifest_accepts_multiplatform_artifact() -> None:
    manifest = {
        "release": {
            "classification": {
                "rules": [
                    {"phase": "release", "patterns": [r"^v?\\d+\\.\\d+\\.\\d+$"]},
                    {"phase": "beta", "patterns": [r"rc"]},
                    {"phase": "alpha", "patterns": [r"^dev-"]},
                ],
                "default_phase": "release",
            }
        },
        "artifacts": {
            "identica": {
                "file": "Identica-{version}.jar",
                "platforms": {
                    "velocity": {"loaders": ["velocity"], "game_versions": ["1.21.11"], "platform_versions": ["3.5"]},
                    "paper": {"loaders": ["paper"], "game_versions": ["1.21.11"], "platform_versions": ["1.21.11"]},
                },
            }
        },
        "publications": {
            "identica-modrinth": {
                "provider": {
                    "id": "modrinth",
                    "project_id": "abc",
                    "release_type_map": {
                        "release": "release",
                        "beta": "beta",
                        "alpha": "alpha",
                    },
                },
                "artifact": "identica",
                "platforms": ["velocity", "paper"],
            }
        },
    }

    validate_manifest(manifest)
