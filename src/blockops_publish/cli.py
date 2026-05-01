from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from blockops_publish.config import ConfigError, deep_merge, load_override_file, load_yaml_file, validate_manifest
from blockops_publish.github_api import GitHubClient, GitHubRelease
from blockops_publish.metadata import classify_version, derive_release_title, derive_version_number, trim_release_body
from blockops_publish.models import PublishArtifact, PublishPlan, PublishTarget, ReleaseMetadata
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
                f"- `{target.publication}` ({target.provider}) -> `{target.artifact.artifact_name}`"
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
    }
    resolved = deep_merge(manifest, release_data)
    resolved = deep_merge(resolved, override)

    assets_by_name = {asset.name: asset for asset in release.assets}
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
        asset = assets_by_name.get(artifact_name)
        if asset is None:
            available_assets = ", ".join(sorted(assets_by_name))
            raise ConfigError(f"Release asset {artifact_name} not found. Available assets: {available_assets}")

        artifact_path = github.download_asset(asset, asset_dir / artifact_name)
        artifact = PublishArtifact(
            name=artifact_key,
            file_template=artifact_config["file"],
            artifact_name=artifact_name,
            artifact_path=artifact_path,
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
