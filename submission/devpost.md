# EvidenceGraph

> EvidenceGraph uses DataHub's context graph to turn breaking data changes into
> complete impact maps, validated migration code, and evidence-backed go/no-go
> decisions.

## Inspiration

A column removal can look safe in a pull request while breaking an executive
dashboard and a production model that live outside the repository. Catalog
search can find metadata, but safe change automation needs more: complete path
evidence, ownership, contracts, deterministic validation, and a refusal path
when the graph is incomplete.

We built EvidenceGraph as a **data-change assurance compiler**. It makes DataHub
context executable, testable, and auditable instead of merely summarizing a
catalog page.

## What it does

EvidenceGraph accepts a proposed schema, contract, pipeline, or ML feature
change and runs a bounded workflow:

1. collect schemas, ownership, documentation, tags, contracts, dataset and
   column lineage, dashboard dependencies, and ML metadata from DataHub;
2. prove whether the requested downstream frontier is complete;
3. compute affected assets and evidence-backed risk priorities;
4. generate a cross-system migration bundle;
5. run deterministic and native validators;
6. issue a go/no-go decision with unresolved risks; and
7. optionally write an allowlisted evidence marker and document back to
   DataHub after explicit safety gates.

Every factual claim in the output links to a DataHub URN and an observation or
deterministic derivation. A missing lineage page, unresolved field, owner gap,
evidence conflict, or failed validator blocks write-back and safe-to-merge
status.

## Flagship scenario

Our miniature commerce platform models a source dataset, two dbt datasets, an
Airflow job, an executive Looker dashboard, an ML feature, a churn model, a
production model deployment, owners, documentation, and a governed contract.
The proposed removal of `customer_tier` crosses every one of those boundaries.

A repository-only scanner finds 3 of the 7 affected assets. With DataHub,
EvidenceGraph finds all 7 of 7. The additional context recovers the executive
dashboard plus the ML feature, model, and deployment: a 57.1 percentage-point
recall improvement against the frozen truth set and the difference between an
unsafe approval and an evidence-backed plan.

EvidenceGraph generates nine artifacts, including a compatibility SQL view,
a dbt model and tests, a real unified diff, validation SQL, an Airflow publication gate, an ML
feature compatibility contract, a risk-ranked migration plan, and an artifact
manifest.

The verified bundle passed 14 of 14 gates. dbt Core 1.12.0 built the generated
model and passed 7 of 7 tests. DuckDB executed the SQL compatibility plan. The
generated DAG passed DagBag import and dependency assertions inside the
official Apache Airflow 3.3.0 Linux container. The ML parity check reported a
0.0 mismatch rate across the four synthetic rows.

## Why DataHub is essential

DataHub is the operational context graph, not a decorative lookup layer.
Removing it changes the result: EvidenceGraph loses four non-repository
consumers, owner routing, governed context, and the evidence needed to authorize
action.

The official DataHub MCP Server is the runtime boundary for search, entity
context, schemas, dataset lineage, column lineage, and governed mutations. The
demo pins `mcp-server-datahub@0.6.0`. A narrow DataHub Python SDK reader enriches
relationships that MCP 0.6.0 does not expose as lineage nodes, including the
modeled ML deployment link. DataHub Core v1.6.0 stores the heterogeneous graph
and the bounded write-back.

## How we built it

EvidenceGraph is a Python application with a typed context-provider boundary,
a deterministic impact engine, risk planner, artifact generator, validation
harness, policy gate, evidence ledger, and allowlisted write-back executor.

The official MCP server provides inspectable agent tools. Pydantic models keep
observed, derived, incomplete, failed, and unsupported evidence states
distinct. DuckDB executes the synthetic warehouse plan, dbt validates the
generated transformation, and an official Airflow container validates the DAG
and its publication gate. Artifact and response hashes make the run
inspectable without storing secrets.

No external LLM key is required. The safety-critical reasoning and validation
path is deterministic so an optional model cannot invent facts or override a
failed policy gate.

## Challenges we solved

- Treating pagination exhaustion and traversal bounds as evidence, instead of
  assuming that a successful first page proves completeness.
- Normalizing heterogeneous DataHub assets while retaining their original URNs
  and observation hashes.
- Keeping BI and production ML consumers in the same change decision as SQL,
  dbt, and orchestration code.
- Validating generated work in disposable native environments without allowing
  those tools to inherit DataHub credentials.
- Separating useful read-only analysis from a tightly governed metadata
  mutation boundary.

## What we learned

The most important lesson is that zero results are not evidence of zero impact.
An operational agent needs to represent `not queried`, `read failed`,
`incomplete`, and `unsupported` separately. DataHub becomes most valuable when
its context changes the agent's plan and authority, not just its prose.

We also learned that generated code is only as credible as its receipts. A
reviewer should be able to move from a risk score to a lineage observation, from
an artifact to its evidence claims, and from a success badge to the exact tool,
version, exit code, and output digest.

## Current limitations

The measured 7-of-7 result is scoped to the declared synthetic graph. The
current artifact strategy is intentionally narrow and supports the flagship
`customer_tier` removal with an approved compatibility mapping. EvidenceGraph
does not modify production systems or merge code.

Fresh-graph closure is demonstrated as a labeled deterministic before/after replay, not as a
mutation performed by the hosted public demo. A controlled local run applied and read back the
three allowlisted DataHub metadata operations; a new MCP client retried the identical proposal
set and verified three no-ops. This does not prove transactional rollback after an interrupted
multi-step write. The anonymous public demo has no mutation path.

## What's next

Next steps include more schema-change strategies, pull-request integration, first-class BI
semantic validation, additional ML registries and orchestrators, and transactional recovery for
interrupted metadata writes.

## Data and privacy

All demonstration records, assets, teams, and business names are synthetic.
The project uses no customer data, private tenant metadata, or personal
information.

## Try it

- Public demo: `https://evidencegraph-datahub.liu891855.chatgpt.site`
- Public repository: `https://github.com/agentic-build-lab/evidencegraph-datahub`
- Sample evidence package: `https://github.com/agentic-build-lab/evidencegraph-datahub/tree/v0.1.0/examples`
- Demo video: `https://youtu.be/MFDSc8Nx1Qs`
- Release: `https://github.com/agentic-build-lab/evidencegraph-datahub/releases/tag/v0.1.0`

## Built with

DataHub Core, DataHub MCP Server, DataHub Python SDK, Model Context Protocol,
Python, Pydantic, Typer, DuckDB, dbt, Apache Airflow, Docker, SQLGlot, PyYAML,
Rich, and pytest.
