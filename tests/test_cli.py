from pathlib import Path

import pytest

from blockops_publish.cli import build_publish_plan, parse_targets_expression
from blockops_publish.config import ConfigError
from blockops_publish.github_api import GitHubAsset, GitHubRelease


class FakeGitHubClient:
    def download_asset(self, asset: GitHubAsset, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jar-data")
        return destination


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


def build_release() -> GitHubRelease:
    return GitHubRelease(
        tag_name="v2.0.0",
        name="2.0.0",
        body="Release body",
        html_url="https://github.com/whereareiam/Identica/releases/tag/v2.0.0",
        assets=[
            GitHubAsset(
                name="Identica-VELOCITY-2.0.0.jar",
                api_url="https://api.github.com/assets/1",
                browser_download_url="https://example.com/1",
            ),
            GitHubAsset(
                name="Identica-Cracked-2.0.0.jar",
                api_url="https://api.github.com/assets/2",
                browser_download_url="https://example.com/2",
            ),
        ],
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


def test_build_publish_plan_resolves_artifact_and_publication(tmp_path: Path) -> None:
    plan = build_publish_plan(
        repository="whereareiam/Identica",
        release=build_release(),
        manifest=build_manifest(),
        targets_expression="identica-modrinth",
        override={},
        asset_dir=tmp_path,
        github=FakeGitHubClient(),
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
