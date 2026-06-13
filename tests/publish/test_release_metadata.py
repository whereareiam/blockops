from publish.planner import build_release_metadata


def test_build_release_metadata_uses_release_name_when_body_has_no_heading() -> None:
    metadata = build_release_metadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0",
        release_name="Identica 2.0.0",
        release_body="Release body",
        html_url="https://example.com/release",
    )

    assert metadata.version_number == "2.0.0"
    assert metadata.title == "Identica 2.0.0"
    assert metadata.version_type == "release"


def test_build_release_metadata_uses_heading_when_present() -> None:
    metadata = build_release_metadata(
        repository="whereareiam/Identica",
        tag_name="v2.0.0-RC1",
        release_name="",
        release_body="# Custom Title\n\nBody",
        html_url="https://example.com/release",
    )

    assert metadata.title == "Custom Title"
    assert metadata.version_type == "beta"


def test_build_release_metadata_uses_manifest_classification_rules() -> None:
    metadata = build_release_metadata(
        repository="whereareiam/Identica",
        tag_name="dev-abcdef1",
        release_name="",
        release_body="Body",
        html_url="https://example.com/release",
        release_config={
            "classification": {
                "rules": [
                    {"phase": "release", "patterns": [r"^v?\d+\.\d+\.\d+$"]},
                    {"phase": "beta", "patterns": [r"^v?\d+\.\d+\.\d+-rc\d+$"]},
                    {"phase": "alpha", "patterns": [r"^dev-[0-9a-f]+$"]},
                ],
                "default_phase": "release",
            }
        },
    )

    assert metadata.version_type == "alpha"
