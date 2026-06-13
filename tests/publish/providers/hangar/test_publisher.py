from pathlib import Path

import responses

from publish.providers.hangar.publisher import HangarPublisher


@responses.activate
def test_hangar_publisher_uploads_version(tmp_path: Path) -> None:
    publisher = HangarPublisher("token")

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"
        html_url = "https://example.com"

    class DummyPlatform:
        platform_versions = ["3.5"]
        loaders = ["velocity"]

    class DummyArtifact:
        artifact_name = "Identica-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        publication = "identica-hangar"
        provider = {
            "id": "hangar",
            "project_slug": "whereareiam/Identica",
            "release_type_map": {"release": "Release", "beta": "Beta", "alpha": "Beta"},
        }
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    responses.post("https://hangar.papermc.io/api/v1/authenticate", json={"token": "bearer"}, status=200)
    responses.post("https://hangar.papermc.io/api/v1/projects/whereareiam/Identica/upload", json={"ok": True}, status=200)

    artifact_path = tmp_path / "Identica-2.0.0.jar"
    artifact_path.write_bytes(b"jar-data")
    result = publisher.publish(DummyRelease(), DummyTarget(), artifact_path, dry_run=False)

    assert "Published Hangar publication" in result
