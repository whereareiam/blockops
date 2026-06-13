import responses

from publish.models import ReleaseMetadata
from publish.planner import (
    build_publication_matrix,
    deserialize_publish_plan,
    parse_targets_expression,
    resolve_publish_plan,
    serialize_publish_plan,
)


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


def build_manifest() -> dict:
    return {
        "artifacts": {
            "identica": {
                "file": "Identica-{version}.jar",
                "platforms": {
                    "velocity": {"loaders": ["velocity"]},
                    "paper": {"loaders": ["paper"]},
                },
            }
        },
        "publications": {
            "identica-modrinth": {
                "provider": {
                    "id": "modrinth",
                    "project_id": "D26hHMI2",
                },
                "artifact": "identica",
                "platforms": ["velocity"],
            },
            "identica-hangar": {
                "provider": {
                    "id": "hangar",
                    "project_slug": "whereareiam/Identica",
                },
                "artifact": "identica",
                "platforms": ["velocity"],
            },
        },
    }


def test_parse_targets_expression_defaults_to_all_publications() -> None:
    targets = parse_targets_expression("", build_manifest())
    assert targets == ["identica-modrinth", "identica-hangar"]


@responses.activate
def test_resolve_publish_plan_resolves_provider_specific_fallbacks() -> None:
    responses.get(
        "https://fill.papermc.io/v3/projects/paper",
        json={"versions": {"26.1": ["26.1.2"]}},
        status=200,
    )
    responses.get(
        "https://fill.papermc.io/v3/projects/velocity",
        json={"versions": {"3.0.0": ["3.5.0-SNAPSHOT"]}},
        status=200,
    )

    plan = resolve_publish_plan(build_release(), build_manifest(), "")

    matrix = build_publication_matrix(plan)
    assert matrix == [
        {"publication": "identica-modrinth", "provider": "modrinth", "artifact": "identica"},
        {"publication": "identica-hangar", "provider": "hangar", "artifact": "identica"},
    ]
    modrinth_target = next(target for target in plan.targets if target.provider_id == "modrinth")
    hangar_target = next(target for target in plan.targets if target.provider_id == "hangar")
    assert modrinth_target.artifact.platforms["velocity"].game_versions == ["26.1.2"]
    assert hangar_target.artifact.platforms["velocity"].platform_versions == ["3.5"]


@responses.activate
def test_serialize_publish_plan_round_trips() -> None:
    responses.get(
        "https://fill.papermc.io/v3/projects/paper",
        json={"versions": {"26.1": ["26.1.2"]}},
        status=200,
    )
    responses.get(
        "https://fill.papermc.io/v3/projects/velocity",
        json={"versions": {"3.0.0": ["3.5.0-SNAPSHOT"]}},
        status=200,
    )
    plan = resolve_publish_plan(build_release(), build_manifest(), "identica-modrinth")
    restored = deserialize_publish_plan(serialize_publish_plan(plan))
    assert restored.release == plan.release
    assert restored.targets[0].provider_id == plan.targets[0].provider_id
    assert restored.targets[0].artifact.artifact_name == plan.targets[0].artifact.artifact_name
