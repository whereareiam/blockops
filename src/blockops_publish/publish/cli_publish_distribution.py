from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from blockops_publish.publish.planner import build_release_metadata, resolve_publish_plan
from blockops_publish.publish.runtime import (
    parse_bool,
    parse_provider_credentials,
    publish_single_target,
    resolve_artifact_path,
    write_step_summary,
)
from blockops_publish.manifest.config import ConfigError, load_override_file, load_yaml_file, validate_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish release distributions to external providers")
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-name", default="")
    parser.add_argument("--release-body", default="")
    parser.add_argument("--release-url", default="")
    parser.add_argument("--manifest-path", default=".github/release-distribution.yml")
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--targets", default="")
    parser.add_argument("--dry-run", default="false")
    parser.add_argument("--override-yaml-file", type=Path)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
    parser.add_argument("--provider-credentials", default=os.environ.get("INPUT_PROVIDER_CREDENTIALS", ""))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repository = args.repository.strip()
        if not repository:
            raise ConfigError("GITHUB_REPOSITORY or --repository is required")

        workspace = Path(args.workspace).resolve()
        manifest_path = workspace / args.manifest_path
        manifest = load_yaml_file(manifest_path)
        validate_manifest(manifest)

        release = build_release_metadata(
            repository=repository,
            tag_name=args.release_tag,
            release_name=args.release_name,
            release_body=args.release_body,
            html_url=args.release_url,
            release_config=manifest.get("release"),
        )
        plan = resolve_publish_plan(
            release=release,
            manifest=manifest,
            targets_expression=args.targets,
            override=load_override_file(args.override_yaml_file),
        )
        dry_run = parse_bool(args.dry_run)
        provider_credentials = parse_provider_credentials(args.provider_credentials)

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

        artifact_directory = args.artifact_directory.resolve()

        for target in plan.targets:
            summary_lines.append(
                f"- `{target.publication}` ({target.provider_id}) -> `{target.artifact.artifact_name}`"
            )

            artifact_path = resolve_artifact_path(artifact_directory, target)
            message = publish_single_target(
                release=plan.release,
                target=target,
                artifact_path=artifact_path,
                dry_run=dry_run,
                provider_credentials=provider_credentials,
            )
            summary_lines.append(f"- Result: {message}")
            print(message)

        write_step_summary("\n".join(summary_lines))
        return 0
    except Exception as exc:  # noqa: BLE001
        write_step_summary(f"# Distribution Publish Failed\n\n- Error: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
