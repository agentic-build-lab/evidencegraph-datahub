# DataHub Open-Source Contributions

EvidenceGraph's integration and security review produced four focused contributions to the official
[`datahub-project/datahub-skills`](https://github.com/datahub-project/datahub-skills) repository.
Each pull request fixes an independently reproducible problem and is intentionally separate from the
EvidenceGraph application.

## Contribution portfolio

| Pull request                                                       | Upstream issue                                                       | Contribution                                                                                                                                                       | Validation                                                                                             |
| ------------------------------------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| [#101](https://github.com/datahub-project/datahub-skills/pull/101) | [#100](https://github.com/datahub-project/datahub-skills/issues/100) | Aligns `datahub-enrich` guidance with the mutation tools registered by `mcp-server-datahub` v0.6.0, including feature gates and bulk or column-level capabilities. | Published package metadata and registration source, Prettier, markdownlint, and `git diff --check`.    |
| [#103](https://github.com/datahub-project/datahub-skills/pull/103) | [#102](https://github.com/datahub-project/datahub-skills/issues/102) | Removes routing to the non-existent `/datahub-govern` command and keeps governance metadata operations in `/datahub-enrich`.                                       | Repository-wide dead-reference search, Prettier, markdownlint, and `git diff --check`.                 |
| [#105](https://github.com/datahub-project/datahub-skills/pull/105) | [#104](https://github.com/datahub-project/datahub-skills/issues/104) | Hardens `datahub-setup` so agents do not read credential files, request PATs in chat, or receive an unused arbitrary Python auto-approval.                         | `npx skills add . --list`, static security assertions, Prettier, markdownlint, and `git diff --check`. |
| [#107](https://github.com/datahub-project/datahub-skills/pull/107) | [#106](https://github.com/datahub-project/datahub-skills/issues/106) | Fixes the Bash test runner exiting on its first pass, failure, or skip counter update under `set -e`.                                                              | `bash -n` plus a stubbed full-skip run reaching `Results: 0 passed, 0 failed, 3 skipped`.              |

## Status snapshot

As of **August 7, 2026**, all four pull requests are open and non-draft. Their conventional-title
checks pass. Relevant local checks pass; the upstream `Lint` workflows require a DataHub maintainer
to approve execution for this first-time fork contributor. None of these contributions is described
as accepted or merged.

EvidenceGraph does not depend on these pull requests being accepted. The contribution links are
provided as public, reviewable evidence for the hackathon's optional open-source contribution bonus.
