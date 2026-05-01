from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from blockops_publish.publish.models import PublishArtifact, PublishPlan, PublishTarget, ReleaseMetadata
from blockops_publish.shared.config import ConfigError, deep_merge
from blockops_publish.shared.metadata import classify_version, derive_release_title, derive_version_number, trim_release_body


def resolve_publish_plan(
    release: ReleaseMetadata,
    manifest: dict[str, Any],
    targets_expression: str,
    override: dict[str, Any] | None = None,
) -> PublishPlan:
    release_data = {"release": asdict(release)}
    resolved = deep_merge(manifest, release_data)
    if override:
        resolved = deep_merge(resolved, override)

    selected_targets = parse_targets_expression(targets_expression, resolved)
    release_meta = ReleaseMetadata(**resolved["release"])
    publish_targets: list[PublishTarget] = []

    for publication_name in selected_targets:
        publication_config = resolved["publications"][publication_name]
        provider_name = publication_config["provider"]
        artifact_key = publication_config["artifact"]
        artifact_config = resolved["artifacts"][artifact_key]

        artifact_name = resolve_artifact_name(
            template=artifact_config["file"],
            tag_name=release_meta.tag_name,
            version_number=release_meta.version_number,
        )
        artifact = PublishArtifact(
            name=artifact_key,
            file_template=artifact_config["file"],
            artifact_name=artifact_name,
            game_versions=artifact_config["game_versions"],
            loaders=artifact_config.get("loaders", []),
            platform=artifact_config.get("platform"),
        )
        provider_config = {
            key: value
            for key, value in publication_config.items()
            if key not in {"provider", "artifact"}
        }
        publish_targets.append(
            PublishTarget(
                provider=provider_name,
                publication=publication_name,
                artifact=artifact,
                provider_config=provider_config,
            )
        )

    return PublishPlan(release=release_meta, targets=publish_targets)


def parse_targets_expression(targets_expression: str, manifest: dict[str, Any]) -> list[str]:
    if not targets_expression.strip():
        return list(manifest["publications"].keys())

    targets: list[str] = []
    for raw_selector in targets_expression.split(","):
        selector = raw_selector.strip()
        if not selector:
            continue

        if selector not in manifest["publications"]:
            raise ConfigError(f"Unknown publication in target selector: {selector}")

        targets.append(selector)

    if not targets:
        raise ConfigError("No valid publish targets were selected")
    return targets


def resolve_artifact_name(template: str, tag_name: str, version_number: str) -> str:
    return template.format(tag=tag_name, version=version_number)


def find_publication(plan: PublishPlan, publication: str) -> PublishTarget:
    for target in plan.targets:
        if target.publication == publication:
            return target
    raise ConfigError(f"Publication not found in plan: {publication}")


def build_publication_matrix(plan: PublishPlan) -> list[dict[str, str]]:
    return [
        {
            "publication": target.publication,
            "provider": target.provider,
            "artifact": target.artifact.name,
        }
        for target in plan.targets
    ]


def serialize_publish_plan(plan: PublishPlan) -> str:
    return json.dumps(serialize_publish_plan_to_data(plan), separators=(",", ":"))


def serialize_publish_plan_to_data(plan: PublishPlan) -> dict[str, Any]:
    return {
        "release": asdict(plan.release),
        "targets": [
            {
                "provider": target.provider,
                "publication": target.publication,
                "artifact": asdict(target.artifact),
                "provider_config": target.provider_config,
            }
            for target in plan.targets
        ],
    }


def deserialize_publish_plan(serialized: str) -> PublishPlan:
    return deserialize_publish_plan_from_data(json.loads(serialized))


def deserialize_publish_plan_from_data(data: dict[str, Any]) -> PublishPlan:
    release = ReleaseMetadata(**data["release"])
    targets = [
        PublishTarget(
            provider=target["provider"],
            publication=target["publication"],
            artifact=PublishArtifact(**target["artifact"]),
            provider_config=target["provider_config"],
        )
        for target in data["targets"]
    ]
    return PublishPlan(release=release, targets=targets)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_metadata(
    repository: str,
    tag_name: str,
    release_name: str,
    release_body: str,
    html_url: str,
) -> ReleaseMetadata:
    return ReleaseMetadata(
        repository=repository,
        tag_name=tag_name,
        version_number=derive_version_number(tag_name),
        title=derive_release_title(release_body, release_name or tag_name),
        changelog=trim_release_body(release_body),
        version_type=classify_version(tag_name),
        html_url=html_url,
    )
