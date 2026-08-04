# Limitations

EvidenceGraph is a production-minded hackathon prototype, not a production
change-management service. The following boundaries are material to judging and
adoption.

## Declared test universe

The measured 7-of-7 result applies to the frozen synthetic commerce graph in
this repository. It proves correctness against that declared universe; it does
not establish universal recall for arbitrary DataHub deployments.

The flagship generator currently targets one deliberate breaking change:
removing `customer_tier` when an approved `segment_code` compatibility mapping
is available. Other schema, contract, orchestration, and ML changes require
additional artifact strategies before they can be considered safe.

## Metadata quality and permissions

EvidenceGraph can only reason from metadata it can retrieve. Missing or stale
lineage, field mappings, owners, contracts, permissions, or unsupported entity
relationships reduce confidence and block a safe-to-merge decision. A zero
result is not treated as proof of no impact.

MCP Server 0.6.0 does not expose every modeled relationship as a lineage node.
The demo uses a narrow DataHub Python SDK reader to enrich ML model deployment
relationships. This is disclosed in the context snapshot and architecture.

## Validation scope

The verified validation run contains fourteen passed gates, including patch application, DuckDB
execution, dbt Core 1.12.0 with 7 of 7 tests, and Airflow DagBag validation in
the official 3.3.0 Linux container. These validators exercise the generated
demo artifacts in disposable environments; they do not validate a user's full
warehouse, BI semantic layer, model registry, or deployment platform.

## Action boundary

EvidenceGraph writes generated files to an output directory and may perform
allowlisted DataHub metadata updates after explicit gates. It does not open a
pull request, merge code, alter production data, deploy a model, or edit a live
dashboard in the current release.

The public demo has no mutation path.

## Closure and retry boundary

Fresh-graph closure is implemented and covered by both positive and stale-graph refusal tests.
The published closure receipt is a deterministic synthetic replay: it proves the protocol and
policy boundary, not that the hosted public replay mutates and re-ingests a live DataHub server.

Write-back idempotence is proven for an immediate stateless retry of the identical proposal set.
It does not prove transactional rollback across a process crash, eventual-consistency windows
longer than the bounded readback period, or equivalence after a different proposal revision.

## Agent scope

The core reasoning, scoring, generation selection, validation, and policy gates
are deterministic. No external LLM key is required. This improves replayability
and evidence control, but the current release does not attempt open-ended code
generation for unknown platforms.

## Availability

The deterministic fixture mode remains useful when DataHub is unavailable. It
is labeled as replay evidence and is not presented as a fresh live query. The
local integration proof requires Docker, DataHub Core, Node.js, and the pinned
MCP server package.

## Upstream dependency constraint

The locked official DataHub agent stack currently resolves `setuptools 81.0.0`.
That version is reported by `pip-audit` and Dependabot for `PYSEC-2026-3447` /
`CVE-2026-59890` (`GHSA-h35f-9h28-mq5c`); the fixed release is 83.0.0, while
`acryl-datahub==1.6.0.6` requires `setuptools<82`. EvidenceGraph does not use
setuptools in its runtime logic or build source distributions in its supported
flow, and the public replay does not install or build untrusted distributions.
The exception remains a release risk until the official DataHub constraint
permits an upgraded setuptools.
