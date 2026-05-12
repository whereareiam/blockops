from blockops_publish.providers.modrinth.existing_version import ModrinthExistingVersionChecker


def test_existing_version_checker_allows_new_version_when_only_loaders_match() -> None:
    checker = ModrinthExistingVersionChecker()

    class DummyRelease:
        version_number = "2.0.0"
        title = "Release"
        changelog = "Body"
        version_type = "release"

    class DummyPlatform:
        loaders = ["velocity"]
        game_versions = ["26.1.2"]

    class DummyArtifact:
        artifact_name = "Identica-2.0.0.jar"
        platforms = {"velocity": DummyPlatform()}

    class DummyTarget:
        artifact = DummyArtifact()
        selected_platforms = ["velocity"]

    result = checker.classify(
        DummyRelease(),
        DummyTarget(),
        [
            {
                "version_number": "1.0.0",
                "name": "Old",
                "changelog": "Body",
                "version_type": "release",
                "loaders": ["velocity"],
                "game_versions": ["26.1.2"],
                "files": [{"filename": "Identica-1.0.0.jar"}],
            }
        ],
    )

    assert result == "publish"
