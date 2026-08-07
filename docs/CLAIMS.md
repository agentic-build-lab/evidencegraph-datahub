# Public Claims Ledger

This file is the source of truth for quantitative and capability claims used in
the README, public demo, video, and Devpost submission. Claims must be removed
or revised if their release evidence does not match the final commit.

## Verified claims

| ID    | Approved public wording                                                                                                                                                                                                     | Evidence boundary                                                                                                                                                                   |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C-001 | The flagship `customer_tier` proposal has seven affected downstream assets in the frozen synthetic platform.                                                                                                                | Fixture truth set and EvidenceGraph impact ledger.                                                                                                                                  |
| C-002 | Repository-only analysis finds 3 of 7 affected assets, while DataHub-grounded analysis finds 7 of 7.                                                                                                                        | Deterministic ablation against the same frozen truth set.                                                                                                                           |
| C-003 | DataHub improves recall from 42.9% to 100.0%, a gain of 57.1 percentage points, and recovers one dashboard plus an ML feature, model, and deployment.                                                                       | Ablation result and additional-asset URNs.                                                                                                                                          |
| C-004 | EvidenceGraph generates nine artifacts spanning SQL, dbt, a real unified diff, validation, orchestration, ML compatibility, a migration plan, and a manifest.                                                               | Flagship artifact manifest and ledger.                                                                                                                                              |
| C-005 | The verified flagship bundle passed 14 of 14 deterministic gates: one integrity/evidence-binding check, eight structured-file parser checks, and five native or integration checks.                                         | Release-candidate validation receipts.                                                                                                                                              |
| C-006 | dbt Core 1.12.0 built the generated model and passed 7 of 7 schema and data tests.                                                                                                                                          | `VAL-DBT-BUILD`, exit code 0.                                                                                                                                                       |
| C-007 | The generated Airflow DAG passed DagBag import and dependency-gate assertions in the official Airflow 3.3.0 Linux container.                                                                                                | `VAL-AIRFLOW-DAG`, official `apache/airflow:3.3.0-python3.12` image, exit code 0.                                                                                                   |
| C-008 | The SQL compatibility view executed in DuckDB and preserved the expected contract for 4 of 4 synthetic rows.                                                                                                                | `VAL-DUCKDB-PARITY`.                                                                                                                                                                |
| C-009 | The ML compatibility mapping passed parity for 4 synthetic rows at a 0.0 mismatch rate.                                                                                                                                     | `VAL-ML-PARITY`.                                                                                                                                                                    |
| C-010 | The live integration used `mcp-server-datahub@0.6.0` to collect entity, schema, dataset-lineage, and column-lineage context from DataHub Core v1.6.0.                                                                       | [Sanitized MCP observation trace](../examples/flagship/mcp-trace.sanitized.json) and [normalized live context snapshot](../examples/flagship/context-snapshot.live.sanitized.json). |
| C-011 | A controlled local run applied and read back three allowlisted DataHub metadata operations: tag addition, description append, and evidence-document save.                                                                   | Mutation receipts with `applied_verified` status.                                                                                                                                   |
| C-012 | Live write-back requires `--apply`, `EVIDENCEGRAPH_ENABLE_WRITES=true`, and MCP mutation-tool availability.                                                                                                                 | Policy implementation and negative tests.                                                                                                                                           |
| C-013 | The demonstration uses synthetic data and invented asset and team identities.                                                                                                                                               | Fixture source and provenance record.                                                                                                                                               |
| C-014 | An immediate stateless retry of the identical write-back proposal set produced 3 of 3 verified no-ops and reused the same document URN.                                                                                     | Frozen write-back retry receipts.                                                                                                                                                   |
| C-015 | The deterministic closure replay closes only from a complete graph whose observations postdate the applied patch and report zero old-field consumers; stale input is refused in tests.                                      | Before/after fixtures, closure receipt, and closure tests.                                                                                                                          |
| C-016 | In the frozen flagship scoring policy, complete evidence yields impact confidence 1.00; omitting one required lineage page caps it at 0.65.                                                                                 | Planner policy and the complete/incomplete flagship ledgers. These are deterministic policy scores, not calibrated production probabilities.                                        |
| C-017 | The EvidenceGraph review produced four focused, open, non-draft pull requests to the official DataHub Skills repository. As of August 7, 2026, their conventional-title checks pass; none is claimed as accepted or merged. | [`docs/OPEN_SOURCE_CONTRIBUTIONS.md`](OPEN_SOURCE_CONTRIBUTIONS.md) and the linked upstream pull requests.                                                                          |

## Required qualifiers

- `7 of 7` means recall against the repository's declared synthetic test
  universe, not arbitrary production catalogs.
- The public replay, if used, must be labeled as replay; the local MCP trace is
  the live DataHub integration proof.
- Generated artifacts are PR-ready inputs for human review, not automatically
  merged production changes.
- The idempotency claim is limited to an immediate retry of the identical proposal set.

## Claims that are not approved

Do not state or imply that EvidenceGraph currently:

- performs live re-ingestion from the hosted public replay;
- guarantees rollback for an interrupted multi-step metadata write;
- guarantees complete impact analysis for arbitrary catalogs;
- applies changes to production databases, repositories, dashboards, models,
  or deployments;
- exposes safe anonymous DataHub mutation; or
- uses an LLM to create verified facts.

## Immutable release references

- Frozen flagship package: `https://github.com/agentic-build-lab/evidencegraph-datahub/tree/v0.2.0/examples`
- Release commit: resolve `v0.2.0^{commit}` from the release tag
- Release tag: `v0.2.0`
- Public demo: `https://evidencegraph-datahub.liu891855.chatgpt.site`
