import responses
from publish.providers.modrinth.client import ModrinthApiError
from publish.providers.modrinth.publisher import ModrinthPublisher
from pathlib import Path


@responses.activate
def test_modrinth_publisher_creates_version(tmp_path: Path) -> None:
    publisher = ModrinthPublisher("token")

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"

    class DummyPlatform:
        loaders = ["velocity"]
        game_versions = ["26.1.2"]

    class DummyArtifact:
        name = "identica"
        artifact_name = "Identica-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        publication = "identica-modrinth"
        provider = {
            "id": "modrinth",
            "project_id": "D26hHMI2",
            "release_type_map": {"release": "release", "beta": "beta", "alpha": "alpha"},
        }
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    responses.get("https://api.modrinth.com/v3/project/D26hHMI2/version", json=[], status=200)
    responses.post("https://api.modrinth.com/v3/version", json={"id": "new-version"}, status=200)

    artifact_path = tmp_path / "Identica-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(DummyRelease(), DummyTarget(), artifact_path, dry_run=False)

    assert "Published Modrinth publication" in result


@responses.activate
def test_modrinth_publisher_uses_upload_loader_override(tmp_path: Path) -> None:
    publisher = ModrinthPublisher("token")

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"

    class DummyPlatform:
        loaders = ["velocity"]
        game_versions = ["26.1.2"]

    class DummyArtifact:
        name = "identica"
        artifact_name = "Identica-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        publication = "identica-modrinth"
        provider = {
            "id": "modrinth",
            "project_id": "D26hHMI2",
            "release_type_map": {"release": "release", "beta": "beta", "alpha": "alpha"},
            "upload_loaders": ["java-agent"],
            "reclassify": {"loaders": ["velocity"]},
        }
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    responses.get("https://api.modrinth.com/v3/project/D26hHMI2/version", json=[], status=200)
    responses.post("https://api.modrinth.com/v3/version", json={"id": "new-version"}, status=200)
    responses.patch("https://api.modrinth.com/v3/version/new-version", json={"id": "new-version"}, status=200)

    artifact_path = tmp_path / "Identica-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")
    publisher.publish(DummyRelease(), DummyTarget(), artifact_path, dry_run=False)

    assert '"loaders": ["java-agent"]' in responses.calls[1].request.body.decode()


@responses.activate
def test_modrinth_publisher_reports_api_error_body(tmp_path: Path) -> None:
    publisher = ModrinthPublisher("token")

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"

    class DummyPlatform:
        loaders = ["velocity"]
        game_versions = ["26.1.2"]

    class DummyArtifact:
        name = "identica"
        artifact_name = "Identica-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        publication = "identica-modrinth"
        provider = {
            "id": "modrinth",
            "project_id": "D26hHMI2",
            "release_type_map": {"release": "release", "beta": "beta", "alpha": "alpha"},
        }
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    responses.get("https://api.modrinth.com/v3/project/D26hHMI2/version", json=[], status=200)
    responses.post(
        "https://api.modrinth.com/v3/version",
        json={"error": "invalid_input", "description": "loader java-agent is not supported for plugins"},
        status=400,
    )

    artifact_path = tmp_path / "Identica-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")

    try:
        publisher.publish(DummyRelease(), DummyTarget(), artifact_path, dry_run=False)
    except ModrinthApiError as exc:
        assert str(exc) == (
            "Modrinth create version failed: 400 invalid_input: "
            "loader java-agent is not supported for plugins"
        )
    else:
        raise AssertionError("Expected ModrinthApiError")


@responses.activate
def test_modrinth_publisher_allows_same_project_same_version_for_different_variant(tmp_path: Path) -> None:
    publisher = ModrinthPublisher("token")

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"

    class DummyPlatform:
        loaders = ["velocity"]
        game_versions = ["26.1.2"]

    class DummyArtifact:
        name = "socialismus-velocity"
        artifact_name = "Socialismus-VELOCITY-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        publication = "socialismus-velocity-modrinth"
        provider = {
            "id": "modrinth",
            "project_id": "aeIrNw73",
            "release_type_map": {"release": "release", "beta": "beta", "alpha": "alpha"},
        }
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    responses.get(
        "https://api.modrinth.com/v3/project/aeIrNw73/version",
        json=[
            {
                "version_number": "2.0.0",
                "name": "Release",
                "changelog": "Body",
                "version_type": "release",
                "loaders": ["paper", "purpur"],
                "game_versions": ["26.1.2"],
                "files": [{"filename": "Socialismus-PAPER-2.0.0.jar"}],
            }
        ],
        status=200,
    )
    responses.post("https://api.modrinth.com/v3/version", json={"id": "new-version"}, status=200)

    artifact_path = tmp_path / "Socialismus-VELOCITY-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(DummyRelease(), DummyTarget(), artifact_path, dry_run=False)

    assert "Published Modrinth publication" in result
