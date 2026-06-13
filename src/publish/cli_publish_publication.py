from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from publish.planner import deserialize_publish_plan, find_publication
from publish.runtime import (
    parse_bool,
    parse_provider_credentials,
    publish_single_target,
    resolve_artifact_path,
    write_step_summary,
)
from publish.manifest.config import ConfigError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a single resolved distribution publication")
    parser.add_argument("--plan-file", type=Path, required=True)
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--publication", required=True)
    parser.add_argument("--dry-run", default="false")
    parser.add_argument("--provider-credentials", default=os.environ.get("INPUT_PROVIDER_CREDENTIALS", ""))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = deserialize_publish_plan(args.plan_file.read_text(encoding="utf-8"))
        target = find_publication(plan, args.publication)
        artifact_path = resolve_artifact_path(args.artifact_directory.resolve(), target)
        provider_credentials = parse_provider_credentials(args.provider_credentials)
        message = publish_single_target(
            release=plan.release,
            target=target,
            artifact_path=artifact_path,
            dry_run=parse_bool(args.dry_run),
            provider_credentials=provider_credentials,
        )

        write_step_summary(
            "\n".join(
                [
                    "# Distribution Publication Run",
                    "",
                    f"- Publication: `{target.publication}`",
                    f"- Provider: `{target.provider_id}`",
                    f"- Artifact: `{target.artifact.artifact_name}`",
                    f"- Result: {message}",
                ]
            )
        )
        print(message)
        return 0
    except Exception as exc:  # noqa: BLE001
        write_step_summary(
            "\n".join(
                [
                    "# Distribution Publication Failed",
                    "",
                    f"- Publication: `{args.publication}`",
                    f"- Error: {exc}",
                ]
            )
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
