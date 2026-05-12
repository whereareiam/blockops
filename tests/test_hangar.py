from pathlib import Path

import pytest
import responses

from blockops_publish.publish.models import PublishArtifact, PublishTarget, ReleaseMetadata
from blockops_publish.providers.hangar import HangarPublishError, HangarPublisher


def build_release() -> ReleaseMetadata:
    return ReleaseMetadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0-RC6",
        version_number="2.0.0-RC6",
        title="Breaking Changes",
        changelog="Body",
        version_type="beta",
        html_url="https://github.com/whereareiam/Identica/releases/tag/v2.0.0-RC6",
    )


def build_target() -> PublishTarget:
    return PublishTarget(
        provider="hangar",
        publication="identica-hangar",
        artifact=PublishArtifact(
            name="identica",
            file_template="Identica-VELOCITY-{version}.jar",
            artifact_name="Identica-VELOCITY-2.0.0-RC6.jar",
            game_versions=["1.20.6", "1.21"],
            loaders=["velocity"],
            platform="velocity",
        ),
        provider_config={
            "project_slug": "identica",
        },
    )


def build_target_with_dependencies() -> PublishTarget:
    target = build_target()
    return PublishTarget(
        provider=target.provider,
        publication=target.publication,
        artifact=target.artifact,
        provider_config={
            "project_slug": "identica",
            "dependencies": [
                {
                    "kind": "hangar",
                    "name": "Identica",
                    "required": True,
                }
            ],
        },
    )


@responses.activate
def test_publish_creates_new_hangar_version(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"token": "bearer-token"},
        status=200,
    )
    responses.post(
        "https://hangar.papermc.io/api/v1/projects/identica/upload",
        json={"result": "ok"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert "Published Hangar publication" in result
    assert len(responses.calls) == 2
    upload_request = responses.calls[1].request
    assert "Bearer bearer-token" == upload_request.headers["Authorization"]
    assert b"versionUpload" in upload_request.body
    assert b'"version": "2.0.0-RC6"' in upload_request.body
    assert b'"channel": "Beta"' in upload_request.body


@responses.activate
def test_publish_uses_release_channel_for_stable_versions(tmp_path: Path) -> None:
    target = build_target()
    release = ReleaseMetadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0",
        version_number="2.0.0",
        title="Stable",
        changelog="Body",
        version_type="release",
        html_url="https://github.com/whereareiam/Identica/releases/tag/v2.0.0",
    )
    publisher = HangarPublisher("token")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"token": "bearer-token"},
        status=200,
    )
    responses.post(
        "https://hangar.papermc.io/api/v1/projects/identica/upload",
        json={"result": "ok"},
        status=200,
    )

    artifact_path = tmp_path / "Identica-VELOCITY-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")
    publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    upload_request = responses.calls[1].request
    assert b'"channel": "Release"' in upload_request.body


def test_publish_dry_run_skips_api_mutation(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(release, target, artifact_path=artifact_path, dry_run=True)

    assert "Dry run validated" in result


@responses.activate
def test_publish_defaults_to_latest_platform_version_only(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"token": "bearer-token"},
        status=200,
    )
    responses.post(
        "https://hangar.papermc.io/api/v1/projects/identica/upload",
        json={"result": "ok"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert b'"platformDependencies": {"velocity": ["1.21"]}' in responses.calls[1].request.body


def test_publish_fails_when_project_slug_missing(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")
    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")

    with pytest.raises(HangarPublishError, match="project_slug"):
        publisher.publish(
            release,
            PublishTarget(
                provider=target.provider,
                publication=target.publication,
                artifact=target.artifact,
                provider_config={},
            ),
            artifact_path=artifact_path,
            dry_run=True,
        )


def test_publish_fails_without_token_for_real_publish(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("")
    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")

    with pytest.raises(HangarPublishError, match="token is required"):
        publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)


@responses.activate
def test_publish_reports_authentication_failure(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")
    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"message": "nope"},
        status=401,
    )

    with pytest.raises(HangarPublishError, match="Failed to authenticate"):
        publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)


@responses.activate
def test_publish_reports_upload_failure(tmp_path: Path) -> None:
    target = build_target()
    release = build_release()
    publisher = HangarPublisher("token")
    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"token": "bearer-token"},
        status=200,
    )
    responses.post(
        "https://hangar.papermc.io/api/v1/projects/identica/upload",
        json={"message": "bad request"},
        status=400,
    )

    with pytest.raises(HangarPublishError, match="Failed to upload Hangar version"):
        publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)


@responses.activate
def test_publish_includes_configured_hangar_dependencies(tmp_path: Path) -> None:
    target = build_target_with_dependencies()
    release = build_release()
    publisher = HangarPublisher("token")

    responses.post(
        "https://hangar.papermc.io/api/v1/authenticate",
        json={"token": "bearer-token"},
        status=200,
    )
    responses.post(
        "https://hangar.papermc.io/api/v1/projects/identica/upload",
        json={"result": "ok"},
        status=200,
    )

    artifact_path = tmp_path / target.artifact.artifact_name
    artifact_path.write_bytes(b"jar-data")
    publisher.publish(release, target, artifact_path=artifact_path, dry_run=False)

    assert b'"pluginDependencies": {"velocity": [{"name": "Identica", "required": true}]}' in responses.calls[1].request.body
