from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from publish.manifest.config import ConfigError, deep_merge, parse_manifest
from publish.providers.registry import ProviderRegistry
from publish.models import (
    ReleaseMetadata,
    ResolvedArtifact,
    ResolvedArtifactPlatform,
    ResolvedPublishPlan,
    ResolvedPublishTarget,
)
from release.metadata import classify_version, derive_release_title, derive_version_number, trim_release_body
from publish.version_sources.resolver import VersionSourceResolver


def resolve_publish_plan(
    release: ReleaseMetadata,
    manifest: dict[str, Any],
    targets_expression: str,
    override: dict[str, Any] | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> ResolvedPublishPlan:
    version_source_resolver = VersionSourceResolver()
    provider_registry = provider_registry or ProviderRegistry()
    resolved = deep_merge(manifest, {})
    manifest_release = manifest.get("release")
    release_config = dict(manifest_release) if isinstance(manifest_release, dict) else {}
    resolved_release = asdict(release)
    release_config.update(resolved_release)
    resolved["release"] = release_config
    if override:
        resolved = deep_merge(resolved, override)

    parsed_manifest = parse_manifest(resolved)
    selected_targets = parse_targets_expression(targets_expression, resolved)
    release_payload = {
        key: value
        for key, value in resolved["release"].items()
        if key in {"repository", "tag_name", "version_number", "title", "changelog", "version_type", "html_url"}
    }
    release_meta = ReleaseMetadata(**release_payload)
    publish_targets: list[ResolvedPublishTarget] = []

    for publication_name in selected_targets:
        publication_spec = parsed_manifest.publications[publication_name]
        artifact_spec = parsed_manifest.artifacts[publication_spec.artifact_name]
        artifact_name = resolve_artifact_name(
            template=artifact_spec.file_template,
            tag_name=release_meta.tag_name,
            version_number=release_meta.version_number,
        )
        selected_platforms = publication_spec.platforms or list(artifact_spec.platforms.keys())
        provider = provider_registry.get_provider(publication_spec.provider_id)
        resolved_artifact = ResolvedArtifact(
            name=artifact_spec.name,
            file_template=artifact_spec.file_template,
            artifact_name=artifact_name,
            platforms={
                key: ResolvedArtifactPlatform(
                    key=platform.key,
                    loaders=list(platform.loaders),
                    game_versions=list(platform.game_versions),
                    platform_versions=list(platform.platform_versions),
                )
                for key, platform in artifact_spec.platforms.items()
                if key in selected_platforms
            },
        )
        target = ResolvedPublishTarget(
            provider_id=publication_spec.provider_id,
            publication=publication_spec.publication,
            artifact=resolved_artifact,
            selected_platforms=selected_platforms,
            provider=provider.parse_provider(publication_name, dict(publication_spec.provider)),
        )
        apply_shared_platform_defaults(target, artifact_spec.platforms, version_source_resolver)
        provider.resolve_target(target=target, release=release_meta, unresolved_platforms=artifact_spec.platforms, resolver=version_source_resolver)
        publish_targets.append(target)

    return ResolvedPublishPlan(release=release_meta, targets=publish_targets)


def apply_shared_platform_defaults(
    target: ResolvedPublishTarget,
    unresolved_platforms,
    resolver: VersionSourceResolver,
) -> None:
    for platform in target.selected_platforms:
        unresolved_platform = unresolved_platforms[platform]
        resolved_platform = target.artifact.platforms[platform]
        if not resolved_platform.game_versions and unresolved_platform.game_versions_source is not None:
            resolved_platform.game_versions = resolver.resolve_latest(unresolved_platform.game_versions_source, "game_versions")
        elif not resolved_platform.game_versions:
            resolved_platform.game_versions = resolver.resolve_latest_default("game_versions")


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


def find_publication(plan: ResolvedPublishPlan, publication: str) -> ResolvedPublishTarget:
    for target in plan.targets:
        if target.publication == publication:
            return target
    raise ConfigError(f"Publication not found in plan: {publication}")


def build_publication_matrix(plan: ResolvedPublishPlan) -> list[dict[str, str]]:
    return [
        {
            "publication": target.publication,
            "provider": target.provider_id,
            "artifact": target.artifact.name,
        }
        for target in plan.targets
    ]


def serialize_publish_plan(plan: ResolvedPublishPlan) -> str:
    return json.dumps(serialize_publish_plan_to_data(plan), separators=(",", ":"))


def serialize_publish_plan_to_data(plan: ResolvedPublishPlan) -> dict[str, Any]:
    return {
        "release": asdict(plan.release),
        "targets": [
            {
                "provider_id": target.provider_id,
                "publication": target.publication,
                "artifact": asdict(target.artifact),
                "selected_platforms": target.selected_platforms,
                "provider": target.provider,
            }
            for target in plan.targets
        ],
    }


def deserialize_publish_plan(serialized: str) -> ResolvedPublishPlan:
    return deserialize_publish_plan_from_data(json.loads(serialized))


def deserialize_publish_plan_from_data(data: dict[str, Any]) -> ResolvedPublishPlan:
    release = ReleaseMetadata(**data["release"])
    targets = [
        ResolvedPublishTarget(
            provider_id=target["provider_id"],
            publication=target["publication"],
            artifact=ResolvedArtifact(
                name=target["artifact"]["name"],
                file_template=target["artifact"]["file_template"],
                artifact_name=target["artifact"]["artifact_name"],
                platforms={
                    key: ResolvedArtifactPlatform(**platform)
                    for key, platform in target["artifact"]["platforms"].items()
                },
            ),
            selected_platforms=target["selected_platforms"],
            provider=target["provider"],
        )
        for target in data["targets"]
    ]
    return ResolvedPublishPlan(release=release, targets=targets)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_metadata(
    repository: str,
    tag_name: str,
    release_name: str,
    release_body: str,
    html_url: str,
    release_config: dict[str, Any] | None = None,
) -> ReleaseMetadata:
    return ReleaseMetadata(
        repository=repository,
        tag_name=tag_name,
        version_number=derive_version_number(tag_name),
        title=derive_release_title(release_body, release_name or tag_name),
        changelog=trim_release_body(release_body),
        version_type=classify_version(tag_name, release_config),
        html_url=html_url,
    )
