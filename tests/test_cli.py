import pytest

from blockops_publish.publish.cli_publish_distribution import parse_args as parse_distribution_args
from blockops_publish.publish.cli_publish_publication import parse_args as parse_publication_args
from blockops_publish.publish.models import ReleaseMetadata
from blockops_publish.publish.planner import (
    build_release_metadata,
    build_publication_matrix,
    deserialize_publish_plan,
    parse_targets_expression,
    resolve_publish_plan,
    serialize_publish_plan,
)
from blockops_publish.shared.config import ConfigError


def build_manifest() -> dict:
    return {
        "artifacts": {
            "velocity": {
                "file": "Identica-VELOCITY-{version}.jar",
                "platform": "velocity",
                "game_versions": ["1.20.6", "1.21"],
                "loaders": ["velocity"],
            },
            "cracked-provider": {
                "file": "Identica-Cracked-{version}.jar",
                "platform": "velocity",
                "game_versions": ["1.20.6", "1.21"],
                "loaders": ["velocity"],
            },
        },
        "publications": {
            "identica-modrinth": {
                "provider": "modrinth",
                "artifact": "velocity",
                "project_id": "D26hHMI2",
            },
            "cracked-modrinth": {
                "provider": "modrinth",
                "artifact": "cracked-provider",
                "project_id": "cFnEyCND",
            },
        },
    }


def build_release() -> ReleaseMetadata:
    return ReleaseMetadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0",
        version_number="2.0.0",
        title="2.0.0",
        changelog="Release body",
        version_type="release",
        html_url="https://github.com/whereareiam/Identica/releases/tag/v2.0.0",
    )


def test_parse_targets_expression_defaults_to_all_publications() -> None:
    targets = parse_targets_expression("", build_manifest())

    assert targets == ["identica-modrinth", "cracked-modrinth"]


def test_parse_targets_expression_accepts_publication_names() -> None:
    targets = parse_targets_expression("cracked-modrinth", build_manifest())

    assert targets == ["cracked-modrinth"]


def test_parse_targets_expression_rejects_unknown_publication() -> None:
    with pytest.raises(ConfigError, match="Unknown publication"):
        parse_targets_expression("missing", build_manifest())


def test_resolve_publish_plan_resolves_artifact_and_publication() -> None:
    plan = resolve_publish_plan(
        release=build_release(),
        manifest=build_manifest(),
        targets_expression="identica-modrinth",
    )

    assert plan.release.version_number == "2.0.0"
    assert len(plan.targets) == 1

    target = plan.targets[0]
    assert target.provider == "modrinth"
    assert target.publication == "identica-modrinth"
    assert target.provider_config["project_id"] == "D26hHMI2"
    assert target.artifact.name == "velocity"
    assert target.artifact.platform == "velocity"
    assert target.artifact.artifact_name == "Identica-VELOCITY-2.0.0.jar"
    assert target.artifact.game_versions == ["1.20.6", "1.21"]


def test_serialize_publish_plan_round_trips() -> None:
    plan = resolve_publish_plan(
        release=build_release(),
        manifest=build_manifest(),
        targets_expression="identica-modrinth",
    )

    restored = deserialize_publish_plan(serialize_publish_plan(plan))

    assert restored == plan


def test_build_publication_matrix_includes_publication_metadata() -> None:
    plan = resolve_publish_plan(
        release=build_release(),
        manifest=build_manifest(),
        targets_expression="",
    )

    assert build_publication_matrix(plan) == [
        {"publication": "identica-modrinth", "provider": "modrinth", "artifact": "velocity"},
        {"publication": "cracked-modrinth", "provider": "modrinth", "artifact": "cracked-provider"},
    ]


def test_build_release_metadata_derives_release_fields() -> None:
    release = build_release_metadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0-RC1",
        release_name="2.0.0-RC1",
        release_body="# Update v2.0.0-RC1 - Breaking Changes\n\nBody",
        html_url="https://github.com/whereareiam/Identica/releases/tag/v2.0.0-RC1",
    )

    assert release.version_number == "2.0.0-RC1"
    assert release.title == "Breaking Changes"
    assert release.changelog == "Body"
    assert release.version_type == "beta"


def test_publish_publication_cli_accepts_hangar_token(tmp_path) -> None:
    args = parse_publication_args(
        [
            "--plan-file",
            str(tmp_path / "plan.json"),
            "--artifact-directory",
            str(tmp_path),
            "--publication",
            "identica-hangar",
            "--hangar-token",
            "hangar-secret",
        ]
    )

    assert args.hangar_token == "hangar-secret"


def test_publish_distribution_cli_accepts_hangar_token(tmp_path) -> None:
    args = parse_distribution_args(
        [
            "--release-tag",
            "v2.0.0",
            "--artifact-directory",
            str(tmp_path),
            "--hangar-token",
            "hangar-secret",
        ]
    )

    assert args.hangar_token == "hangar-secret"
