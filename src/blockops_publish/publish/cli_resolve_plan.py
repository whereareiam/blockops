from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from blockops_publish.publish.planner import (
    build_release_metadata,
    build_publication_matrix,
    resolve_publish_plan,
    serialize_publish_plan,
    write_text,
)
from blockops_publish.shared.config import ConfigError, load_override_file, load_yaml_file, validate_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve a release distribution publish plan")
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-name", default="")
    parser.add_argument("--release-body", default="")
    parser.add_argument("--release-url", default="")
    parser.add_argument("--manifest-path", default=".github/release-distribution.yml")
    parser.add_argument("--targets", default="")
    parser.add_argument("--override-yaml-file", type=Path)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--matrix-file", type=Path)
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
        )
        plan = resolve_publish_plan(
            release=release,
            manifest=manifest,
            targets_expression=args.targets,
            override=load_override_file(args.override_yaml_file),
        )

        serialized_plan = serialize_publish_plan(plan)
        matrix_json = json.dumps(build_publication_matrix(plan), separators=(",", ":"))

        if args.plan_file:
            write_text(args.plan_file, serialized_plan)
        else:
            print(serialized_plan)

        if args.matrix_file:
            write_text(args.matrix_file, matrix_json)

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
