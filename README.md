# blockops

Reusable GitHub Actions for releasing Minecraft projects. A `primitive/<domain>/<thing>/<verb>`
action does one thing; a `composite/...` action combines them into a flow. Reference an action by
its major tag, for example `whereareiam/blockops/primitive/release/notes/format@v4`. General build
and registry actions live in [whereareiam/devops](https://github.com/whereareiam/devops).

| Task | Start here |
| --- | --- |
| Publish a release to Modrinth or Hangar | [Publishing distributions](#publishing-distributions) |
| Group a release draft by pull request title prefix | [Regrouping a release draft](#regrouping-a-release-draft) |
| Turn release notes into a Spigot post | [Formatting release notes](#formatting-release-notes) |
| Move a workflow from `v3` | [Moving from v3](#moving-from-v3) |

## All actions

| Action | Purpose |
| --- | --- |
| `composite/distribution/publish` | Resolves the plan and publishes every selected publication in one job. |
| `primitive/distribution/plan/resolve` | Resolves release metadata into a publication plan and a job matrix. |
| `primitive/distribution/publication/publish` | Publishes one publication of a resolved plan. |
| `primitive/release/draft/regroup` | Regroups a draft release body by title prefix and updates the draft. |
| `primitive/release/notes/format` | Converts release notes into another format, such as BBCode. |

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
        uses: whereareiam/blockops/primitive/distribution/plan/resolve@v4
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
      - uses: whereareiam/blockops/primitive/distribution/publication/publish@v4
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

## Regrouping a release draft

```yaml
- id: drafter
  uses: release-drafter/release-drafter@v7
- uses: whereareiam/blockops/primitive/release/draft/regroup@v4
  with:
    release-id: ${{ steps.drafter.outputs.id }}
    release-body: ${{ steps.drafter.outputs.body }}
```

The job needs `contents: write`. The action uses the job's token unless `token` is set.

## Formatting release notes

```yaml
- uses: whereareiam/blockops/primitive/release/notes/format@v4
  with:
    format: bbcode
    release-body: ${{ github.event.release.body }}
    output-file: output/release-notes-bbcode.txt
```

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
