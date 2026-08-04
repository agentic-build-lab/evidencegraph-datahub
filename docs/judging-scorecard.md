# EvidenceGraph Judging Scorecard

This scorecard converts the official [hackathon rules](https://datahub.devpost.com/rules)
and [challenge brief](https://datahub.devpost.com/) into evidence-based release gates for
EvidenceGraph. It is a readiness instrument, not a prediction of the judges' decisions.

## Pass/fail submission gate

EvidenceGraph is not submission-ready unless every item below passes.

| Gate | Required evidence | Pass condition |
| --- | --- | --- |
| New work | `HACKATHON_PROVENANCE.md` and Git history | Project work is attributable to the July 6-August 10, 2026 submission period; any pre-existing material is disclosed. |
| Required DataHub use | Architecture, live trace, and reproducible integration test | DataHub OSS is used together with at least one required official agent interface. The official DataHub MCP Server is exercised in the flagship path. |
| Working project | Public demo plus clean-clone instructions | The behavior shown in the video is reproducible on its stated platform. |
| Public source | Public repository URL | Repository contains all required source, assets, examples, and setup instructions. |
| License | Root `LICENSE` and repository metadata | Apache License 2.0 is visible and detectable at the top of the repository page. |
| Project access | Public project URL | Judges can access the demo without payment or private coordination through the end of judging. |
| Description | Devpost copy and README | English description explains the problem, DataHub dependency, implementation, limitations, and data used. |
| Video | Public YouTube, Vimeo, or Youku URL | English demonstration is under three minutes and shows the functioning project. |
| Sample outputs | `examples/` index | Generated code, reports, validation receipts, and an evidence ledger are inspectable without running the project. |
| Rights and privacy | Dependency/license inventory and secret scan | All material is authorized for public use; no credentials, private data, or restricted third-party content is present. |

## Scoring method

The five official Stage Two criteria are equally weighted at 20 points each. The open-source
contribution is tracked separately because the rules describe it as a bonus.

Each checkpoint receives 0-4 points:

- **0 — Missing:** no implementation or evidence.
- **1 — Claimed:** described, but not demonstrated by an inspectable artifact.
- **2 — Replayed:** works on a committed fixture or deterministic replay.
- **3 — Integrated:** reproduced against the stated local services with machine-readable receipts.
- **4 — Verified:** independently reproducible, includes negative-path tests, and clearly states evidence boundaries.

Submission target: **90/100 or higher, no core criterion below 17/20, and every pass/fail gate
green**. A score may not be awarded from prose alone; every scored claim must link to a file,
test, trace, public demo state, or immutable output.

## 1. Use of DataHub — 20 points

| Checkpoint | 4-point evidence target |
| --- | --- |
| Operational context graph | The flagship run reads schemas, ownership, documentation, tags or glossary terms, contracts or assertions, multi-hop lineage, dashboard metadata, and ML metadata from DataHub. Each observation retains its DataHub URN. |
| Official agent interface | A live or local-Quickstart trace shows the official MCP Server performing entity, field, lineage, and governed mutation calls; interface versions and tool names are recorded. |
| Material graph reasoning | DataHub-derived paths change the plan, generated artifacts, safety decision, or owner routing. Removing DataHub must produce a measurably worse result, not an equivalent report. |
| Durable write-back | An explicit write-enabled run records a bounded decision/evidence artifact in DataHub, reads it back, verifies related-asset links, and proves idempotent retry behavior. |
| DataHub-vs-repo-only ablation | Against a frozen truth set, the DataHub path reaches 100% affected-asset recall with zero false-safe decisions and improves recall by at least 30 percentage points over the repo-only baseline, including at least one BI and one ML dependency the baseline misses. |

## 2. Technical Execution — 20 points

| Checkpoint | 4-point evidence target |
| --- | --- |
| End-to-end flagship path | One command or one public UI action runs proposal intake, MCP collection, impact analysis, plan generation, artifact generation, native validation, policy decision, ledger emission, and bounded write-back or write preview. |
| Graph correctness | Pagination is exhausted; cycles, duplicate paths, maximum-depth bounds, unsupported entity types, permissions, and truncation are handled explicitly. A successful read is not treated as proof of completeness. |
| Executable artifact quality | The migration pack contains PR-ready artifacts for at least SQL, dbt, orchestration, and ML or BI validation. Generated identifiers and references resolve to the seeded platform. |
| Native validation | SQL executes in the demo warehouse, dbt compiles and tests, the Airflow DAG imports or passes its native validation, and the ML contract/parity check runs. Every validator emits a structured receipt tied to an artifact hash. |
| Reliability and security | Deterministic tests, integration tests, refusal tests, idempotency checks, timeouts, bounded retries, type/lint checks, dependency audit, and secret scan pass from a clean clone. |

## 3. Originality — 20 points

| Checkpoint | 4-point evidence target |
| --- | --- |
| Beyond catalog lookup | The product operates as a change-assurance compiler: it converts graph context into executable migration work and a proof of completion, rather than restating metadata. |
| Cross-system completion contract | SQL, transformation, orchestration, dashboard, feature, model, deployment, and owner impacts participate in one consistent safety decision and evidence model. |
| Claim-level evidence | Every factual claim can be traced to a source observation or deterministic derivation; absence, failure, not-queried, incomplete, and unsupported are different states. |
| Fresh-graph closure protocol | The implementation requires a distinct, complete graph whose observations postdate the applied revision. The published proof is explicitly labeled as a deterministic before/after fixture replay; live post-migration re-ingestion is not claimed. |
| Bounded autonomy | Model-generated suggestions cannot create facts, raise confidence, authorize writes, or override failed validation. Insufficient evidence produces a useful refusal and remediation path. |

## 4. Real-World Usefulness — 20 points

| Checkpoint | 4-point evidence target |
| --- | --- |
| Realistic platform | The miniature platform contains a synthetic warehouse, dbt transformations, an Airflow job, a dashboard, an ML feature/model/deployment path, ownership, documentation, and a data contract. |
| Practitioner workflow | A pull-request or change-proposal workflow produces owner routing, risk-ranked tasks, reviewable diffs, validation commands, rollback guidance, and unresolved-risk ownership. |
| Actionable prioritization | Severity is derived from explicit signals such as field-level path strength, user-facing BI, production ML, contracts, ownership, and failed tests; the explanation links to the evidence used. |
| Safe adoption | Read-only mode is useful by itself; live writes require the operator flag, process enablement, and observed MCP mutation capability, followed by exact proposal approval, scoped target digest, and readback. Mutations are allowlisted and retries are idempotent. |
| Honest limitations | Demo, README, and ledger state what was live, replayed, inferred, unsupported, incomplete, or not independently verified. No fixture is presented as a fresh production query. |

## 5. Submission Quality — 20 points

| Checkpoint | 4-point evidence target |
| --- | --- |
| Judge-first demo | A no-login public demo loads reliably, exposes the flagship scenario in one action, shows progress and refusal states, and provides a deterministic replay if live dependencies are unavailable. |
| Under-three-minute video | A 2:30-2:50 video shows the breaking change, hidden BI/ML blast radius, generated artifacts, native tests, refusal/approval boundary, fresh-graph closure, and DataHub write-back/read-back. |
| README and setup | The first screen explains the value and why DataHub is essential. A quick locked fixture path and a documented local DataHub path are both available; commands are copy-paste tested. |
| Inspectable examples | `examples/` contains the input proposal, repo-only and DataHub runs, migration pack, validator receipts, evidence ledger, write-back receipt, closure receipt, and known-risk notes. |
| Visual and narrative coherence | Architecture, UI, video, Devpost text, and README use the same scenario, terminology, measured numbers, and safety claims. All links are checked immediately before submission. |

## Open-source contribution bonus

Track this outside the 100-point core score.

| Level | Evidence |
| --- | --- |
| 0 | No contribution beyond the submission repository. |
| 1 | Reproducible issue or documentation feedback filed upstream. |
| 2 | Focused DataHub Skill, documentation fix, connector improvement, test, or RFC published with source and validation evidence. |
| 3 | Upstream pull request opened and passing its relevant checks. |
| 4 | Contribution accepted or merged by an independent maintainer before judging. |

Never describe an issue, draft, or open pull request as accepted. Link its current public status and
keep the core submission strong enough to win without bonus credit.
