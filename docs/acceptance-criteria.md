# EvidenceGraph Acceptance Criteria

These criteria define the evidence required for a judge-ready release. A feature is not accepted
because it appears in the UI or README; it is accepted only when its named evidence artifact and
automated or reproducible check exist.

## Severity and status

- **P0:** required for a valid, competitive submission.
- **P1:** required for the intended 90/100 judging target.
- **P2:** bonus or resilience enhancement; it may not delay P0/P1 closure.
- **PASS:** implementation, test, and evidence artifact are present and consistent.
- **BLOCKED:** an external dependency prevents verification and the fallback is documented.
- **FAIL:** absent, contradictory, unverifiable, or misrepresented.

## Product acceptance matrix

| ID | Pri. | Acceptance criterion | Objective pass test | Required evidence |
| --- | --- | --- | --- | --- |
| AC-001 | P0 | The demo platform is a heterogeneous data estate, not a lineage-only fixture. | Seed and ingest at least one warehouse source, two dbt transformations, one Airflow DAG, one dashboard/chart, one ML feature, one model, one deployment, two owners or teams, and one active data contract. All appear as addressable DataHub entities or documented related metadata. | Seed manifest, ingestion logs, expected-entity manifest, DataHub screenshots or export, and automated entity-count assertion. |
| AC-002 | P0 | The flagship proposal is a concrete breaking change. | Removing or replacing `customer_tier` affects transformation, orchestration, dashboard, and ML paths. The proposal includes source URN, field, before/after contract, requested action, and change revision. Malformed or ambiguous proposals are rejected before graph traversal. | Versioned proposal JSON, schema validation tests, and rejected-input fixtures. |
| AC-003 | P0 | Official DataHub MCP is a real runtime boundary. | The flagship integration invokes named official MCP tools for entity/schema context and downstream lineage. Tool version, arguments digest, observation timestamp, response digest, and source URNs are recorded without secrets. A fixture adapter may support tests but cannot be presented as the live MCP path. | Sanitized MCP trace, pinned interface version, integration test, and trace-to-ledger linkage. |
| AC-004 | P0 | Downstream impact collection is complete against the declared test universe. | Traverse every page and every downstream path within the configured scope; retain direct and transitive paths; cover dbt, Airflow, dashboard/chart, feature, model, deployment, and owners. Detect cycles and duplicates. Any pagination, permission, depth, or unsupported-entity uncertainty sets completeness to unestablished and blocks a safe verdict. | Frozen ground-truth graph, traversal report, pagination/cycle tests, recall metric, and incomplete-read negative tests. |
| AC-005 | P0 | DataHub provides measurable value over repository-only analysis. | Run the identical proposal twice: once with repository evidence only and once with DataHub plus repository evidence. DataHub mode achieves 100% recall against the frozen affected-asset truth set, zero false-safe decisions, and at least a 30 percentage-point recall improvement. Repo-only must miss at least one BI dependency and one ML dependency that DataHub resolves. | `ablation/repo-only.json`, `ablation/datahub.json`, truth manifest, comparison report, exact command, and CI assertion of all thresholds. |
| AC-006 | P1 | Risk and remediation priorities are deterministic and evidence-linked. | Repeated runs over identical normalized observations yield the same affected assets, severity, task ordering, owner routing, and refusal decision, excluding explicitly non-semantic timestamps. Every score contribution links to a source observation or validator result. | Policy specification, golden output hashes, repeatability test, and score-explanation table. |
| AC-007 | P0 | The agent produces cross-system executable artifacts. | A successful planning run produces at least four artifact classes: SQL compatibility/validation code, a dbt model/schema/test change, an Airflow migration or compatibility change, and an ML feature/model compatibility or validation change. At least one artifact is a patch against a real demo repository file, not a prose snippet. | Generated migration pack, unified diff, manifest of artifact hashes, source-template tests, and examples index. |
| AC-008 | P0 | Generated artifacts are validated by their native systems. | In a disposable environment: execute SQL and validation queries in DuckDB; run `dbt compile` plus the relevant `dbt test` or `dbt build`; import/parse the Airflow DAG without error and run its deterministic unit check; run the ML feature/model contract or parity test. A failed, skipped, timed-out, or unavailable required validator prevents a safe verdict. | Per-validator JSON receipts with command, version, exit code, duration, artifact hash, sanitized output digest, and aggregate validation report. |
| AC-009 | P0 | Every factual claim has inspectable provenance. | The evidence ledger rejects a factual claim without at least one source observation or deterministic derivation. Each claim records subject URN, predicate, value, evidence IDs, confidence, observation time, derivation rule where applicable, test status, and unresolved risks. | JSON Schema, valid flagship ledger, invalid-ledger tests, and rendered human-readable ledger. |
| AC-010 | P0 | Evidence states preserve uncertainty. | `absent`, `not_queried`, `read_failed`, `incomplete`, `unsupported`, `observed`, and `derived` remain distinct through collection, policy, UI, report, and write-back. No zero-result or timeout is rendered as “no downstream impact.” | State model, serialization tests, UI snapshots, and at least one negative fixture for each uncertainty state. |
| AC-011 | P0 | Unsafe or unsupported work is refused usefully. | The system refuses write-back and safe-to-merge status when any required lineage page is unavailable, the changed field cannot be resolved, a critical owner/contract requirement is unmet, evidence conflicts, a required validator fails, or a mutation is outside the allowlist. The refusal names the failed condition, affected assets, evidence gathered, and next safe action. | Refusal matrix, automated negative tests, sample refusal ledger, and UI/CLI refusal output. |
| AC-012 | P0 | Writes are governed, bounded, and reversible at the metadata layer. | Default mode performs no mutation. Live mutation requires both `--apply` and `EVIDENCEGRAPH_ENABLE_WRITES=true`, plus MCP mutation tools enabled separately. Only allowlisted DataHub metadata types and expected URNs may change. The run reads before and after states, verifies intended state, records no-op/idempotent retry, and never overwrites human-authored documentation silently. | Policy tests, dry-run preview, mutation allowlist, before/after receipt, idempotency test, and reset instructions for demo metadata. |
| AC-013 | P1 | The result is written back as durable operational context. | When all write gates pass, create or update a stable EvidenceGraph decision/evidence document related to every in-scope affected asset and record appropriate status metadata, such as a tag, incident, assertion, or structured property where supported. A new client with no EvidenceGraph local state can retrieve the decision from DataHub. | Write-back receipt, related-entity read-back, store-less retrieval test, and second-run inheritance demonstration. |
| AC-014 | P0 | Closure requires a newer complete graph, not a stale success report. | The closure implementation accepts only a distinct complete graph whose observations postdate the applied revision, whose producer schema and contract match the approved after-state, whose required validators pass, and whose old field has zero remaining consumers. The published proof is a labeled deterministic before/after fixture replay; it is not a live re-ingestion claim. | Applied revision digest, deterministic before/after graph diff, closure receipt, and stale-graph refusal test. |
| AC-015 | P1 | The agent is robust under repetition and partial failure. | Two identical fixture runs produce semantically identical ledgers and artifact hashes. Retries do not duplicate DataHub documents or external artifacts. MCP timeouts, malformed payloads, unavailable validators, and interrupted writes produce bounded failures with no false success. | Determinism test, idempotency test, fault-injection suite, timeout configuration, and recovery notes. |
| AC-016 | P0 | The public surface is safe for anonymous judges. | Public demo requires no payment, credentials, or private membership; exposes only fixed or allowlisted synthetic scenarios; has no public mutation path; rate limits and timeouts are enforced; all fixture/replay states are labeled. No secret, token, private URL, or personal data appears in client assets, logs, examples, or history. | Public URL, threat model, gitleaks result, dependency audit, endpoint tests, and deployment configuration review. |
| AC-017 | P0 | A clean clone can reproduce judge-critical evidence. | On supported Python versions, the fixture path installs and completes without DataHub, credentials, or network after dependencies are available. The documented local DataHub path bootstraps, seeds, runs MCP, executes the flagship scenario, and verifies read-back using copy-paste commands. | Clean-room transcript, CI workflow, lockfile, version matrix, and quickstart smoke test. |
| AC-018 | P1 | Sample outputs are sufficient for judging without execution. | `examples/` includes the proposal, normalized context, impact graph, risk plan, migration pack, native validation receipts, evidence ledger, refusal case, repo-only/DataHub ablation, write-back receipt, fresh-graph closure receipt, and known limitations. All are linked from one index and pass schema/hash checks. | `examples/README.md`, example manifest, checksum verification, and stale-link test. |
| AC-019 | P0 | Public documentation is accurate and consistent. | README, architecture, demo UI, examples, Devpost copy, and video use the same asset names, counts, measured metrics, interface versions, and live-vs-replay labels. Claims are generated from or checked against committed result files where practical. | Documentation claim ledger, link checker, terminology check, and final manual review record. |
| AC-020 | P0 | The submission package satisfies the formal rules. | Public repository is Apache-2.0 and exposes source/setup; project URL remains free through judging; English Devpost description is complete; public video is under three minutes and shows functioning software; assets and music are licensed; no required form field or test instruction is missing. | Submission manifest, video duration probe, URL checks, license detection, rights checklist, and final Devpost preview. |
| AC-021 | P2 | A meaningful DataHub ecosystem contribution is published honestly. | Publish a focused Skill, test, documentation improvement, bug reproduction, RFC, connector improvement, or pull request. Its status is linked and described exactly as filed, open, accepted, or merged. Core readiness does not depend on acceptance. | Public upstream URL, reproduction or tests, contribution diff, and status check. |

## Required refusal scenarios

The release gate must exercise all scenarios below. Every scenario must end with a non-success
safety decision, no unauthorized mutation, and a machine-readable explanation.

| Scenario | Expected result |
| --- | --- |
| Lineage page times out after an earlier page succeeds | Preserve partial observations, mark completeness unestablished, refuse safe-to-merge and write-back. |
| Changed field is absent from the observed schema | Refuse generation and identify the unresolved source field. |
| Dataset-level lineage exists but column lineage is unavailable | Report weaker evidence, downgrade confidence, and refuse any artifact that requires an exact field mapping. |
| A critical dashboard or production model lacks an owner | Keep the asset in scope, create an unresolved routing task, and block final closure. |
| Data contract conflicts with the requested change | Cite both observations, generate no destructive patch, and request an explicit contract decision. |
| SQL/dbt/Airflow/ML validator fails | Retain all receipts, rank the failed remediation first, and block safe-to-merge status. |
| Model output cites an unknown URN or unsupported fact | Reject the claim at the evidence boundary; never add it to the ledger or write-back. |
| `--apply` is used without the environment write gate | Produce a refusal with zero mutation calls. |
| Environment write gate is set without `--apply` | Remain read-only and produce a mutation preview only. |
| Read-after-write does not observe intended state before timeout | Report accepted-but-unverified, not success; permit safe idempotent retry. |
| Re-ingestion is skipped or the graph observation predates the patch | Refuse closure as stale-graph evidence. |

## Flagship release proof

The release candidate passes only when a single indexed evidence package proves this sequence:

1. A `customer_tier` change is proposed against a stable source URN and revision.
2. Repo-only analysis misses at least one dashboard and one ML dependency.
3. DataHub MCP establishes the full declared blast radius across warehouse, dbt, Airflow, BI,
   feature, model, deployment, contract, and owner paths.
4. EvidenceGraph emits a risk-ranked plan and four or more executable artifact classes.
5. DuckDB, dbt, Airflow, and ML-native validators execute and emit receipts.
6. At least one planted unsafe variant is refused and leaves mutation count at zero.
7. A labeled deterministic before/after fixture exercises the newer-complete-graph closure
   protocol; the stale input is refused and zero remaining consumers closes.
8. Separately, three allowlisted metadata results are applied to DataHub and read back; a new
   stateless MCP client retries the exact proposal set as three verified no-ops.
9. The evidence ledger and ablation report reproduce every number used in the README, UI,
   Devpost description, and video.

Every replayed step is labeled at the point of evidence. The deterministic closure replay is
separate from the live local DataHub collection and metadata write-back proof.
