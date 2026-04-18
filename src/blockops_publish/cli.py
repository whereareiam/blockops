from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from blockops_publish.config import ConfigError, deep_merge, load_override_file, load_yaml_file, validate_manifest
from blockops_publish.github_api import GitHubClient, GitHubRelease
from blockops_publish.metadata import classify_version, derive_release_title, derive_version_number, trim_release_body
from blockops_publish.models import PublishPlan, PublishTarget, ReleaseMetadata
from blockops_publish.providers.modrinth import ModrinthPublisher


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish release distributions to external providers")
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--manifest-path", default=".github/release-distribution.yml")
    parser.add_argument("--targets", default="")
    parser.add_argument("--dry-run", default="false")
    parser.add_argument("--override-yaml-file", type=Path)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
    parser.add_argument("--github-token", default=os.environ.get("INPUT_GITHUB_TOKEN", ""))
    parser.add_argument("--modrinth-token", default=os.environ.get("INPUT_MODRINTH_TOKEN", ""))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repository = args.repository.strip()
        if not repository:
            raise ConfigError("GITHUB_REPOSITORY or --repository is required")
        if not args.github_token:
            raise ConfigError("GitHub token is required")

        workspace = Path(args.workspace).resolve()
        manifest_path = workspace / args.manifest_path
        manifest = load_yaml_file(manifest_path)
        validate_manifest(manifest)

        github = GitHubClient(repository, args.github_token)
        release = github.get_release_by_tag(args.release_tag)

        plan = build_publish_plan(
            repository=repository,
            release=release,
            manifest=manifest,
            targets_expression=args.targets,
            override=load_override_file(args.override_yaml_file),
            asset_dir=Path(tempfile.mkdtemp(prefix="blockops-assets-")),
            github=github,
        )

        dry_run = parse_bool(args.dry_run)
        summary_lines = [
            f"# Distribution Publish {'Dry Run' if dry_run else 'Run'}",
            "",
            f"- Repository: `{plan.release.repository}`",
            f"- Release tag: `{plan.release.tag_name}`",
            f"- Version number: `{plan.release.version_number}`",
            f"- Version title: `{plan.release.title}`",
            f"- Version type: `{plan.release.version_type}`",
            "",
            "## Targets",
        ]

        for target in plan.targets:
            summary_lines.append(
                f"- `{target.provider}:{target.variant}` -> `{target.artifact_name}` "
                f"(project `{target.project_id}`)"
            )

        provider_clients: dict[str, Any] = {}

        for target in plan.targets:
            if target.provider == "modrinth":
                provider_clients.setdefault("modrinth", ModrinthPublisher(args.modrinth_token))
                message = provider_clients["modrinth"].publish(plan.release, target, dry_run=dry_run)
            else:
                raise ConfigError(f"Unsupported provider: {target.provider}")

            summary_lines.append(f"- Result: {message}")
            print(message)

        write_step_summary("\n".join(summary_lines))
        return 0
    except Exception as exc:  # noqa: BLE001
        write_step_summary(f"# Distribution Publish Failed\n\n- Error: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_publish_plan(
    repository: str,
    release: GitHubRelease,
    manifest: dict[str, Any],
    targets_expression: str,
    override: dict[str, Any],
    asset_dir: Path,
    github: GitHubClient,
) -> PublishPlan:
    release_data = {
        "release": {
            "repository": repository,
            "tag_name": release.tag_name,
            "version_number": derive_version_number(release.tag_name),
            "title": derive_release_title(release.body, release.name),
            "changelog": trim_release_body(release.body),
            "version_type": classify_version(release.tag_name),
            "html_url": release.html_url,
        },
        "providers": manifest["providers"],
        "variants": manifest["variants"],
    }
    resolved = deep_merge(release_data, override)

    assets_by_name = {asset.name: asset for asset in release.assets}
    selected_targets = parse_targets_expression(targets_expression, manifest)
    release_meta = ReleaseMetadata(**resolved["release"])
    publish_targets: list[PublishTarget] = []

    for provider_name, variant_name in selected_targets:
        variant_config = resolved["variants"][variant_name]
        provider_config = variant_config["providers"].get(provider_name)
        if not isinstance(provider_config, dict):
            raise ConfigError(f"Variant {variant_name} does not define provider {provider_name}")

        artifact_name = resolve_artifact_name(
            template=variant_config["artifact"],
            tag_name=release_meta.tag_name,
            version_number=release_meta.version_number,
        )
        asset = assets_by_name.get(artifact_name)
        if asset is None:
            available_assets = ", ".join(sorted(assets_by_name))
            raise ConfigError(f"Release asset {artifact_name} not found. Available assets: {available_assets}")

        artifact_path = github.download_asset(asset, asset_dir / artifact_name)
        project_id = str(provider_config.get("project_id") or resolved["providers"][provider_name]["project_id"])
        loaders = provider_config.get("loaders")
        if not isinstance(loaders, list) or not all(isinstance(item, str) for item in loaders):
            raise ConfigError(f"Variant {variant_name} must define {provider_name} loaders")

        game_versions = variant_config["game_versions"]
        publish_targets.append(
            PublishTarget(
                provider=provider_name,
                variant=variant_name,
                artifact_name=artifact_name,
                artifact_path=artifact_path,
                game_versions=game_versions,
                loader_values=loaders,
                project_id=project_id,
            )
        )

    return PublishPlan(release=release_meta, targets=publish_targets)


def parse_targets_expression(targets_expression: str, manifest: dict[str, Any]) -> list[tuple[str, str]]:
    if not targets_expression.strip():
        resolved: list[tuple[str, str]] = []
        for variant_name, variant in manifest["variants"].items():
            for provider_name in variant["providers"]:
                resolved.append((provider_name, variant_name))
        return resolved

    targets: list[tuple[str, str]] = []
    for raw_target in targets_expression.split(","):
        target = raw_target.strip()
        if not target:
            continue

        if ":" not in target:
            raise ConfigError(f"Target selector must use provider:variant format: {target}")

        provider_name, variant_name = [part.strip() for part in target.split(":", 1)]
        if variant_name not in manifest["variants"]:
            raise ConfigError(f"Unknown variant in target selector: {target}")
        if provider_name not in manifest["variants"][variant_name]["providers"]:
            raise ConfigError(f"Unknown provider in target selector: {target}")

        targets.append((provider_name, variant_name))

    if not targets:
        raise ConfigError("No valid publish targets were selected")
    return targets


def resolve_artifact_name(template: str, tag_name: str, version_number: str) -> str:
    return template.format(tag=tag_name, version=version_number)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def write_step_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown)
        handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
