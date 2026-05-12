from pathlib import Path

import pytest
import responses

from blockops_publish.publish.models import PublishArtifact, PublishTarget, ReleaseMetadata
from blockops_publish.providers.modrinth import ModrinthPublishError, ModrinthPublisher


def build_release() -> ReleaseMetadata:
    return ReleaseMetadata(
        repository="whereareiam/Socialismus",
        tag_name="2.0.0-RC6",
        version_number="2.0.0-RC6",
        title="Breaking Changes",
        changelog="Body",
        version_type="beta",
        html_url="https://github.com/whereareiam/Socialismus/releases/tag/2.0.0-RC6",
    )


def build_target(tmp_path: Path) -> PublishTarget:
    return PublishTarget(
        provider="modrinth",
        publication="paper-modrinth",
        artifact=PublishArtifact(
            name="paper",
            file_template="Socialismus-PAPER-{version}.jar",
            artifact_name="Socialismus-PAPER-2.0.0-RC6.jar",
            game_versions=["1.20.6", "1.21"],
            loaders=["paper", "purpur", "folia"],
            platform="paper",
        ),
        provider_config={"project_id": "aeIrNw73"},
    )


def build_target_with_dependencies() -> PublishTarget:
    target = build_target(Path("."))
    return PublishTarget(
        provider=target.provider,
        publication=target.publication,
        artifact=target.artifact,
        provider_config={
            "project_id": "aeIrNw73",
            "dependencies": [
                {
                    "project_id": "D26hHMI2",
                    "dependency_type": "required",
                }
            ],
        },
    )


@responses.activate
def test_publish_skips_identical_existing_version(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[
            {
                "version_number": "2.0.0-RC6",
                "name": "Breaking Changes",
                "changelog": "Body",
                "version_type": "beta",
                "loaders": ["folia", "paper", "purpur"],
                "game_versions": ["1.20.6", "1.21"],
                "files": [{"filename": "Socialismus-PAPER-2.0.0-RC6.jar"}],
            }
        ],
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert "Skipped existing" in result


@responses.activate
def test_publish_fails_for_conflicting_existing_version(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[
            {
                "version_number": "2.0.0-RC6",
                "name": "Different",
                "changelog": "Body",
                "version_type": "beta",
                "loaders": ["folia", "paper", "purpur"],
                "game_versions": ["1.20.6", "1.21"],
                "files": [{"filename": "Socialismus-PAPER-2.0.0-RC6.jar"}],
            }
        ],
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    with pytest.raises(ModrinthPublishError):
        publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)


@responses.activate
def test_publish_allows_new_version_when_only_loaders_match(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[
            {
                "version_number": "1.0.0",
                "name": "Old Release",
                "changelog": "Body",
                "version_type": "release",
                "loaders": ["folia", "paper", "purpur"],
                "game_versions": ["1.20.6", "1.21"],
                "files": [{"filename": "Socialismus-PAPER-1.0.0.jar"}],
            }
        ],
        status=200,
    )
    responses.post(
        "https://api.modrinth.com/v3/version",
        json={"id": "new-version"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert "Published Modrinth publication" in result


@responses.activate
def test_publish_creates_new_version(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[],
        status=200,
    )
    responses.post(
        "https://api.modrinth.com/v3/version",
        json={"id": "new-version"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert "Published Modrinth publication" in result


@responses.activate
def test_publish_dry_run_skips_api_mutation(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[],
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=True)

    assert "Dry run validated" in result
    assert len(responses.calls) == 1


def test_publish_fails_when_project_id_missing(tmp_path: Path) -> None:
    target = build_target(tmp_path)
    release = build_release()
    publisher = ModrinthPublisher("token")
    broken_target = PublishTarget(
        provider=target.provider,
        publication=target.publication,
        artifact=target.artifact,
        provider_config={},
    )
    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")

    with pytest.raises(ModrinthPublishError, match="project_id"):
        publisher.publish(release, broken_target, artifact_path=artifact_path, dry_run=True)


@responses.activate
def test_publish_includes_configured_dependencies(tmp_path: Path) -> None:
    target = build_target_with_dependencies()
    release = build_release()
    publisher = ModrinthPublisher("token")

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[],
        status=200,
    )
    responses.post(
        "https://api.modrinth.com/v3/version",
        json={"id": "new-version"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert '"project_id": "D26hHMI2"' in responses.calls[1].request.body.decode()
    assert '"dependency_type": "required"' in responses.calls[1].request.body.decode()
