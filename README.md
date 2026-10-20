# blockops

Reusable GitHub Actions for releasing Minecraft projects. A `primitive/<domain>/<thing>/<verb>`
action does one thing; a `composite/...` action combines them into a flow. Reference an action by
its major tag, for example `whereareiam/blockops/primitive/distribution/plan/resolve@v5`. General build,
registry and release notes actions live in [whereareiam/devops](https://github.com/whereareiam/devops).

| Task | Start here |
| --- | --- |
| Publish a release to Modrinth or Hangar | [Publishing distributions](#publishing-distributions) |
| Move a workflow from `v4` | [Moving from v4](#moving-from-v4) |
| Move a workflow from `v3` | [Moving from v3](#moving-from-v3) |

## All actions

| Action | Purpose |
| --- | --- |
| `composite/distribution/publish` | Resolves the plan and publishes every selected publication in one job. |
| `primitive/distribution/plan/resolve` | Resolves release metadata into a publication plan and a job matrix. |
| `primitive/distribution/publication/publish` | Publishes one publication of a resolved plan. |

## Publishing distributions

The consumer repository describes its artifacts and publications in
`.github/release-distribution.yml`. One job resolves the plan; a matrix job publishes each
publication, so a failed store can be re-run alone.

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      plan-json: ${{ steps.plan.outputs.plan-json }}
      matrix-json: ${{ steps.plan.outputs.matrix-json }}
    steps:
      - uses: actions/checkout@v7
      - id: plan
        uses: whereareiam/blockops/primitive/distribution/plan/resolve@v5
        with:
          release-tag: ${{ github.event.release.tag_name }}
          release-name: ${{ github.event.release.name }}
          release-body: ${{ github.event.release.body }}
          release-url: ${{ github.event.release.html_url }}

  publish:
    needs: plan
    if: needs.plan.outputs.matrix-json != '[]'
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        publication: ${{ fromJson(needs.plan.outputs.matrix-json) }}
    steps:
      # Download the built artifacts into ./output first.
      - uses: whereareiam/blockops/primitive/distribution/publication/publish@v5
        with:
          provider-credentials: |
            modrinth: ${{ secrets.MODRINTH_TOKEN }}
          plan-json: ${{ needs.plan.outputs.plan-json }}
          artifact-directory: output
          publication: ${{ matrix.publication.publication }}
```

`targets` limits the plan to named publications, `override-yaml` patches the resolved data, and
`dry-run: "true"` validates without publishing. `composite/distribution/publish` takes the inputs of
both actions and does everything in one job.

### Modrinth options

A Modrinth publication names its project and, where needed, how its version is created:

```yaml
publications:
  provider-modrinth:
    provider:
      id: modrinth
      project_id: 7mTkb4OS
      release_type_map:
        release: release
        beta: beta
        alpha: alpha
      upload_loaders:
        - java-agent
      loader_fields:
        environment: server_only
      reclassify:
        loaders: [bungeecord, velocity, waterfall]
      dependencies:
        - project_id: DDxUcAy9
          dependency_type: required
    artifact: provider
```

| Option | Purpose |
| --- | --- |
| `project_id` | The Modrinth project the version is created in. Required. |
| `release_type_map` | Maps the release phase (`release`, `beta`, `alpha`) to a Modrinth version type. |
| `dependencies` | Dependencies of the version: `dependency_type` and one of `project_id`, `version_id` or `file_name`. |
| `upload_loaders` | Loaders to create the version with, instead of the loaders of the artifact's platforms. |
| `loader_fields` | Loader fields sent with the new version, such as `environment`. |
| `reclassify` | Changes the version right after it is created: `loaders` (default: the artifact's loaders), `version_type` and `status`. |

Modrinth refuses a version that lacks a mandatory field of one of its loaders. Mod loaders such as
`java-agent` or `fabric` need `environment`, one of `client_and_server`, `client_only`,
`client_only_server_optional`, `client_or_server`, `client_or_server_prefers_both`,
`dedicated_server_only`, `server_only`, `server_only_client_optional` or `singleplayer_only`.
Plugin loaders such as `velocity` or `paper` have no `environment`, and Modrinth refuses it for
them. <https://api.modrinth.com/v3/tag/loader> lists the fields of each loader under
`supported_fields`, and `https://api.modrinth.com/v3/loader_field?loader_field=<field>` the values of
a field. A loader field cannot replace what the publisher sets itself, such as `loaders` or
`game_versions`. `reclassify` does not send loader fields, so a version created as `java-agent` can
move to plugin loaders.

## Moving from v4

The release notes actions moved to [whereareiam/devops](https://github.com/whereareiam/devops) unchanged;
switch their major tag along with the repository. The distribution actions keep their inputs and outputs.

| v4 | v5 |
| --- | --- |
| `whereareiam/blockops/primitive/release/draft/regroup@v4` | `whereareiam/devops/primitive/release/draft/regroup@v3` |
| `whereareiam/blockops/primitive/release/notes/format@v4` | `whereareiam/devops/primitive/release/notes/format@v3` |
| `whereareiam/blockops/...@v4` (distribution actions) | `whereareiam/blockops/...@v5` |

## Moving from v3

| v3 | v4 |
| --- | --- |
| `actions/publish/publish-distribution` | `composite/distribution/publish` |
| `actions/publish/resolve-distribution-plan` | `primitive/distribution/plan/resolve` |
| `actions/publish/publish-publication` | `primitive/distribution/publication/publish` |
| `actions/release/regroup-draft-release` | `primitive/release/draft/regroup` |
| `actions/release/format-release-notes` | `primitive/release/notes/format` |

Inputs and outputs are unchanged, with one exception: `primitive/release/draft/regroup` takes the
token through its `token` input, which defaults to the job's token, instead of a `GITHUB_TOKEN`
environment variable.

## Development

```shell
uv run --extra test pytest
```
